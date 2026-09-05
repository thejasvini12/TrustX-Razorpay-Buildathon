"""Production FastAPI backend for the AI-RISK Coordinated Merchant Abuse Risk Engine.

Provides:
- GET /health: Health check and engine availability verification.
- POST /risk/score: Real-time risk scoring for merchant accounts using the trained ML pipeline.
"""

import os
import uuid
import json
import base64
import urllib.request
import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

from src.risk_scorer import RiskScorer
from src.fraud_spike_detector import FraudSpikeDetector
from src.abuse_ring_sentinel import AbuseRingSentinel
from src.razorpay_webhook import get_webhook_manager
from src.account_store import get_account_store
from src.live_abuse_graph import get_live_abuse_graph_store, normalize_device_id
from src.live_fraud_telemetry import get_live_fraud_telemetry_store
from src.payment_context import extract_client_ip, get_payment_context_store, canonicalize_address
from src.features import (
    ID_COLUMN,
    DEFAULT_NUMERIC_VALUES,
    DEFAULT_CATEGORICAL_VALUES,
    AccountInputValidationError,
)

logger = logging.getLogger("ai_risk_api")
logging.basicConfig(level=logging.INFO)

# Global RiskScorer, FraudSpikeDetector, and AbuseRingSentinel singleton instances
_risk_scorer: Optional[RiskScorer] = None
_fraud_spike_detector: Optional[FraudSpikeDetector] = None
_abuse_ring_sentinel: Optional[AbuseRingSentinel] = None


def get_scorer() -> RiskScorer:
    """Retrieve or initialize the cached RiskScorer instance."""
    global _risk_scorer
    if _risk_scorer is None:
        model_path = os.path.join("models", "risk_engine_rf.joblib")
        metadata_path = os.path.join("models", "model_metadata.json")
        _risk_scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)
        logger.info("RiskScorer initialized and model loaded successfully.")
    return _risk_scorer


def get_spike_detector() -> FraudSpikeDetector:
    """Retrieve or initialize the cached FraudSpikeDetector instance."""
    global _fraud_spike_detector
    if _fraud_spike_detector is None:
        model_path = os.path.join("models", "fraud_spike_model.joblib")
        metadata_path = os.path.join("models", "fraud_spike_metadata.json")
        _fraud_spike_detector = FraudSpikeDetector(model_path=model_path, metadata_path=metadata_path)
        logger.info("FraudSpikeDetector initialized and model loaded successfully.")
    return _fraud_spike_detector


def get_abuse_ring_sentinel() -> AbuseRingSentinel:
    """Retrieve or initialize the cached AbuseRingSentinel instance."""
    global _abuse_ring_sentinel
    if _abuse_ring_sentinel is None:
        model_path = os.path.join("models", "abuse_ring_model.joblib")
        _abuse_ring_sentinel = AbuseRingSentinel(model_path=model_path)
        logger.info("AbuseRingSentinel initialized and model loaded successfully.")
    return _abuse_ring_sentinel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager to pre-load all ML models on API startup."""
    try:
        get_scorer()
        get_spike_detector()
        get_abuse_ring_sentinel()
        logger.info("AI-RISK API startup complete. All ML models ready for inference.")
    except Exception as e:
        logger.error(f"Failed to pre-load ML models during startup: {e}")
    yield


app = FastAPI(
    title="AI-RISK Engine API",
    description=(
        "Production-grade REST API for Coordinated Merchant Abuse Detection. "
        "Provides real-time behavioral validation, ML risk scoring, and policy action recommendations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Schemas for Request and Response Documentation
class AccountRiskRequest(BaseModel):
    """Input payload representing merchant account attributes."""
    model_config = ConfigDict(extra="allow")

    account_id: Optional[str] = Field(
        default="UNSEEN_ACCOUNT",
        description="Unique identifier for the merchant/account (not used as a predictive feature).",
        examples=["ACC_MERCHANT_90210"],
    )
    order_count: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["order_count"],
        description="Total lifetime orders completed by the account.",
        examples=[25.0],
    )
    return_count: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["return_count"],
        description="Total count of returned orders.",
        examples=[1.0],
    )
    refund_count: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["refund_count"],
        description="Total count of refund claims filed.",
        examples=[1.0],
    )
    total_spend: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["total_spend"],
        description="Gross lifetime spend in USD.",
        examples=[1400.0],
    )
    average_order_value: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["average_order_value"],
        description="Average order value in USD.",
        examples=[56.0],
    )
    account_age_days: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["account_age_days"],
        description="Age of the account in days.",
        examples=[365.0],
    )
    device_count: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["device_count"],
        description="Number of hardware devices linked to this account.",
        examples=[1.0],
    )
    ip_count: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["ip_count"],
        description="Number of distinct IP addresses used by this account.",
        examples=[2.0],
    )
    payment_instrument_count: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["payment_instrument_count"],
        description="Number of credit cards / payment instruments linked.",
        examples=[1.0],
    )
    return_rate: Optional[float] = Field(
        default=None,
        description="Return rate [0.0 to 1.0]. Recalculated from counts if omitted.",
        examples=[0.04],
    )
    refund_rate: Optional[float] = Field(
        default=None,
        description="Refund rate [0.0 to 1.0]. Recalculated from counts if omitted.",
        examples=[0.04],
    )
    high_value_order_count: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["high_value_order_count"],
        description="Count of high-value transactions.",
        examples=[1.0],
    )
    suspicious_activity_score: Optional[float] = Field(
        default=DEFAULT_NUMERIC_VALUES["suspicious_activity_score"],
        description="External syndicate / velocity anomaly score [0.0 to 1.0].",
        examples=[0.02],
    )
    device_type: Optional[str] = Field(
        default=DEFAULT_CATEGORICAL_VALUES["device_type"],
        description="Primary device fingerprint (mobile_ios, desktop_chrome, emulator_bot, etc.).",
        examples=["mobile_ios"],
    )
    primary_payment_method: Optional[str] = Field(
        default=DEFAULT_CATEGORICAL_VALUES["primary_payment_method"],
        description="Primary payment method (credit_card, paypal, virtual_card, etc.).",
        examples=["credit_card"],
    )


class LiveActivityEvent(BaseModel):
    """Summary of a real-time Razorpay payment event."""
    model_config = ConfigDict(extra="allow")

    event_id: Optional[str] = None
    event_type: str
    payment_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "INR"
    status: str = "unknown"
    timestamp: str
    association_source: str = "notes"


class LiveActivityResponse(BaseModel):
    """Real-time in-memory live activity derived strictly from accepted Razorpay webhooks."""
    model_config = ConfigDict(extra="allow")

    account_id: str
    payment_count: int = Field(default=0, description="Count of unique captured payments.")
    failed_payment_count: int = Field(default=0, description="Count of unique failed payments.")
    payment_volume: float = Field(default=0.0, description="Monetary sum of captured payments.")
    last_payment_at: Optional[str] = Field(default=None, description="ISO timestamp of last payment.")
    webhook_event_count: int = Field(default=0, description="Total non-duplicate webhook events.")
    recent_events: List[LiveActivityEvent] = Field(default_factory=list, description="Recent webhook payment events.")
    association_sources: List[str] = Field(default_factory=list, description="Methods used to associate payments.")


class AccountProfileResponse(AccountRiskRequest):
    """Complete account profile response with immutable historical features and live_activity."""
    model_config = ConfigDict(extra="allow")

    live_activity: Optional[LiveActivityResponse] = Field(
        default=None,
        description="Real-time activity derived strictly from Razorpay webhook telemetry."
    )


class DecisionPolicyResponse(BaseModel):
    """Contextual operational defense policy recommendations generated by AdaptiveDecisionEngine."""
    abuse_pattern: str = Field(description="Identified abuse pattern archetype (e.g., SERIAL_RETURN_ABUSE, COORDINATED_SYNDICATE, etc.).")
    primary_action: str = Field(description="Contextual primary defense action (e.g., RESTRICT_RETURN_WITHOUT_RECEIPT, REQUIRE_2FA_VERIFICATION).")
    secondary_actions: List[str] = Field(default_factory=list, description="Recommended operational safeguards and secondary controls.")
    policy_triggers: List[str] = Field(default_factory=list, description="Deterministic rule triggers that matched this account profile.")
    policy_reasoning: str = Field(description="Human-readable rationale for the recommended defense policy.")
    confidence: str = Field(description="Policy rule matching confidence (HIGH, MEDIUM, LOW).")


class ReturnRiskResponse(BaseModel):
    """Dedicated specialized assessment for Return & Refund Abuse (Serial Wardrobing).
    
    OPERATIONAL DOMAIN: Post-purchase return and refund authorization only.
    Operates independently of and does NOT alter account-level checkout authorization.
    """
    return_abuse_prediction: int = Field(description="Binary classification for return abuse (0 = Normal, 1 = Return Abuser).")
    return_risk_probability: float = Field(description="Estimated return abuse posterior probability (0.0 to 1.0).")
    return_risk_score: int = Field(description="Calibrated return risk index (0 to 100).")
    return_risk_level: str = Field(description="Qualitative return risk tier: LOW, MEDIUM, or HIGH.")
    return_risk_factors: List[str] = Field(default_factory=list, description="Behavioral signals elevating return risk.")
    return_mitigating_factors: List[str] = Field(default_factory=list, description="Protective signals lowering return risk.")
    return_explanation: str = Field(description="Specific plain-language explanation of return risk.")
    recommended_return_action: str = Field(
        description=(
            "Specialized operational policy action strictly governing RETURN AND REFUND authorization: "
            "ALLOW_STANDARD_RETURNS (standard frictionless returns), "
            "FLAG_FOR_RETURN_DESK_AUDIT (secondary return-desk verification), or "
            "RESTRICT_INSTANT_REFUNDS_AND_INSPECT (hold refund pending physical receipt inspection). "
            "Does NOT restrict account-level checkout or transactional privileges."
        )
    )


class RiskAssessmentResponse(BaseModel):
    """Structured response containing prediction, calibrated risk score, and policy action.
    
    OPERATIONAL DOMAIN: Real-time account, checkout, and transactional authorization.
    """
    account_id: str = Field(description="Account identifier.")
    prediction: int = Field(description="Binary classification label (0 = Normal, 1 = Coordinated Abuse).")
    risk_probability: float = Field(description="Model abuse probability between 0.0 and 1.0.")
    risk_score: int = Field(description="Calibrated risk index between 0 and 100.")
    risk_level: str = Field(description="Qualitative risk tier: LOW, MEDIUM, or HIGH.")
    risk_tier: str = Field(description="Alias for risk_level.")
    data_quality_score: float = Field(description="Input completeness/sanity score between 0.0 and 1.0.")
    warnings: List[str] = Field(description="Data sanitization and imputation notes.")
    recommended_action: str = Field(
        description=(
            "Policy defense action governing ACCOUNT / CHECKOUT / TRANSACTIONAL authorization: "
            "ALLOW (permit frictionless transaction), "
            "MANUAL_REVIEW (hold order for verification), or "
            "CHALLENGE_OR_BLOCK (enforce step-up authentication or decline). "
            "Operates independently of specialized post-purchase return_risk authorization."
        )
    )
    explanation_summary: Optional[str] = Field(
        default="",
        description="High-level human-readable explanation of the combined model risk decision.",
    )
    decision_reasoning: Optional[str] = Field(
        default="",
        description="Detailed explanation of why the account was assigned to its qualitative risk tier.",
    )
    risk_increasing_signals: Optional[List[str]] = Field(
        default_factory=list,
        description="Prominent behavioral patterns associated with elevated risk.",
    )
    risk_reducing_signals: Optional[List[str]] = Field(
        default_factory=list,
        description="Prominent protective patterns associated with customer trustworthiness.",
    )
    risk_factors: List[str] = Field(description="Behavioral drivers contributing to the risk evaluation.")
    mitigating_factors: Optional[List[str]] = Field(
        default_factory=list,
        description="Positive protective signals that decrease risk assessment.",
    )
    feature_contributions: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Ranked model-informed feature influences based on global feature importances.",
    )
    decision_policy: Optional[DecisionPolicyResponse] = Field(
        default=None,
        description="Adaptive operational defense policy evaluated downstream of ML scoring.",
    )
    return_risk: Optional[ReturnRiskResponse] = Field(
        default=None,
        description=(
            "Dedicated Return & Refund Abuse risk assessment governing post-purchase return/refund "
            "privileges independently of account-level checkout authorization."
        ),
    )


class HealthResponse(BaseModel):
    """Health check status response."""
    status: str
    service: str
    version: str
    model_loaded: bool
    model_type: Optional[str] = None


class FiveMinuteObservation(BaseModel):
    """Input payload representing a single 5-minute sub-window telemetry observation."""
    model_config = ConfigDict(extra="allow")

    timestamp: Optional[str] = Field(default=None, description="Observation timestamp or window identifier.")
    tx_count: int = Field(default=0, ge=0, description="Completed transactions in the 5-minute interval.")
    fraud_count: Optional[int] = Field(default=0, ge=0, description="Disputed/fraudulent transactions in the 5-minute interval.")
    fraud_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Explicit 5-minute fraud rate.")
    device_count: Optional[int] = Field(default=None, ge=0, description="Distinct devices observed in the 5-minute interval.")


class FraudSpikeRequest(BaseModel):
    """Input payload representing a merchant or population cluster temporal observation window."""
    model_config = ConfigDict(extra="ignore")

    merchant_id: Optional[str] = Field(default="MERCH_UNKNOWN", description="Merchant or cluster identifier.")
    baseline_window: Optional[str] = Field(default="previous_24h", description="Baseline historical comparison window.")
    current_window: Optional[str] = Field(default="latest_1h", description="Current evaluation observation window.")
    baseline_tx_count: int = Field(default=240, ge=0, description="Total completed transactions in baseline window.")
    current_tx_count: int = Field(default=10, ge=0, description="Total transactions in current observation window.")
    baseline_fraud_count: Optional[int] = Field(default=0, ge=0, description="Disputed/fraudulent transactions in baseline.")
    current_fraud_count: Optional[int] = Field(default=0, ge=0, description="Disputed/fraudulent transactions in current window.")
    baseline_fraud_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Explicit baseline fraud rate.")
    current_fraud_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Explicit current fraud rate.")
    baseline_device_count: Optional[int] = Field(default=None, ge=0, description="Distinct hardware devices observed in baseline.")
    current_device_count: Optional[int] = Field(default=None, ge=0, description="Distinct hardware devices observed in current window.")
    baseline_suspicious_score: Optional[float] = Field(default=0.05, ge=0.0, le=1.0, description="Baseline cluster anomaly score.")
    current_suspicious_score: Optional[float] = Field(default=0.05, ge=0.0, le=1.0, description="Current cluster anomaly score.")
    five_minute_telemetry: Optional[List[FiveMinuteObservation]] = Field(
        default=None,
        description="Optional chronological sequence of 5-minute sub-window observations.",
    )


class FraudSpikeResponse(BaseModel):
    """Structured response for temporal fraud-spike detection."""
    merchant_id: str = Field(description="Merchant or population cluster identifier.")
    spike_prediction: int = Field(description="Binary classification (0 = Normal/Stable, 1 = Genuine Fraud Spike).")
    spike_probability: float = Field(description="Model posterior spike probability (0.0 to 1.0).")
    spike_score: int = Field(description="Calibrated spike risk index (0 to 100).")
    spike_level: str = Field(description="Qualitative spike tier: LOW, MEDIUM, or HIGH.")
    raw_spike_probability: Optional[float] = Field(default=None, description="Raw unadjusted model posterior probability.")
    raw_spike_score: Optional[int] = Field(default=None, description="Raw unadjusted model spike score (0 to 100).")
    raw_spike_level: Optional[str] = Field(default=None, description="Raw unadjusted model spike tier: LOW, MEDIUM, or HIGH.")
    guardrail_triggered: Optional[bool] = Field(default=False, description="Whether the deterministic fraud-rate delta floor guardrail activated.")
    five_minute_telemetry_available: Optional[bool] = Field(default=False, description="Whether 5-minute sub-window telemetry was provided and evaluated.")
    five_minute_observation_count: Optional[int] = Field(default=0, description="Number of 5-minute sub-window observations evaluated.")
    five_minute_current_tx_count: Optional[int] = Field(default=None, description="Transaction count in the latest 5-minute sub-window.")
    five_minute_velocity_ratio: Optional[float] = Field(default=None, description="Short-window transaction velocity ratio relative to recent 5-minute baseline.")
    five_minute_guardrail_triggered: Optional[bool] = Field(default=False, description="Whether short-window 5-minute burst guardrail activated.")
    consecutive_anomaly_windows: Optional[int] = Field(default=0, description="Number of consecutive evaluation windows with elevated anomaly risk.")
    persistence_escalation_triggered: Optional[bool] = Field(default=False, description="Whether operational tier was escalated to HIGH due to persistent consecutive anomaly windows.")
    baseline_window: str = Field(description="Baseline window description.")
    current_window: str = Field(description="Current evaluation window description.")
    baseline_fraud_rate: float = Field(description="Historical baseline fraud rate.")
    current_fraud_rate: float = Field(description="Current observation window fraud rate.")
    fraud_rate_change: float = Field(description="Absolute delta between current and baseline fraud rate.")
    evidence_quality: str = Field(description="Observational sample quality: SUFFICIENT, LIMITED_SAMPLE, or INSUFFICIENT_SAMPLE.")
    confidence: str = Field(description="Operational confidence level: HIGH, MEDIUM, or LOW.")
    evidence_summary: str = Field(description="Plain-language explanation of supporting observational evidence volume.")
    spike_factors: List[str] = Field(default_factory=list, description="Specific velocity, rate, or device risk drivers.")
    mitigating_factors: List[str] = Field(default_factory=list, description="Protective factors explaining non-spike traffic.")
    explanation: str = Field(description="Plain-language human-readable assessment of the temporal change.")
    recommended_action: str = Field(description="Automated defense policy action for merchant or cluster.")


class LiveFraud5MinMetrics(BaseModel):
    """Real-time 5-minute window transaction metrics."""
    tx_count: int = Field(default=0, description="Completed payments in the latest 5 minutes.")
    tx_volume: float = Field(default=0.0, description="Total monetary volume of completed payments.")
    failed_count: int = Field(default=0, description="Failed payments in the latest 5 minutes.")
    fraud_count: int = Field(default=0, description="Explicit fraud signals in the latest 5 minutes.")
    fraud_rate: float = Field(default=0.0, description="Fraud rate in the latest 5 minutes.")


class LiveFraud1HourMetrics(BaseModel):
    """Real-time 1-hour window transaction metrics."""
    tx_count: int = Field(default=0, description="Completed payments in the latest 1 hour.")
    tx_volume: float = Field(default=0.0, description="Total monetary volume of completed payments.")
    failed_count: int = Field(default=0, description="Failed payments in the latest 1 hour.")
    fraud_count: int = Field(default=0, description="Explicit fraud signals in the latest 1 hour.")
    fraud_rate: float = Field(default=0.0, description="Fraud rate in the latest 1 hour.")


class LiveFraudRecentEventItem(BaseModel):
    """Audit representation of an event ingested into live fraud telemetry."""
    event_id: str
    event_type: str
    payment_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "INR"
    status: str = "unknown"
    merchant_id: str
    lifecycle_action: str
    is_failed: bool = False
    explicit_fraud: bool = False
    device_id: Optional[str] = None
    timestamp: str
    unix_timestamp: float


class LiveFraudSpikeTelemetryResponse(BaseModel):
    """Operational live telemetry response for Fraud Spike Sentinel."""
    status: str = Field(description="Telemetry status ('ACTIVE' or 'IDLE').")
    merchant_id: str = Field(description="Target merchant identifier.")
    total_events_processed: int = Field(description="Total non-duplicate webhook events ingested.")
    last_event_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of latest event.")
    rolling_5m: LiveFraud5MinMetrics = Field(description="Rolling 5-minute metrics.")
    rolling_1h: LiveFraud1HourMetrics = Field(description="Rolling 1-hour metrics.")
    unique_devices_1h: int = Field(default=0, description="Distinct explicit devices observed in 1 hour.")
    five_minute_observations: List[FiveMinuteObservation] = Field(default_factory=list, description="Chronological 5-minute observation buckets.")
    recent_events: List[LiveFraudRecentEventItem] = Field(default_factory=list, description="Recent webhook event stream.")
    synthesized_request: Optional[Dict[str, Any]] = Field(default=None, description="Normalized FraudSpikeRequest derived from live metrics.")


class LiveFraudEvaluationRequest(BaseModel):
    """Optional evaluation parameters for live fraud spike evaluation."""
    merchant_id: Optional[str] = Field(default=None, description="Target merchant identifier.")


# Abuse-Ring Sentinel Request and Response Schemas
class AccountNodeInput(BaseModel):
    """Input payload representing an account node within a candidate cluster."""
    model_config = ConfigDict(extra="allow")

    account_id: str = Field(description="Unique account identifier.", examples=["ACC_000001"])
    created_at: Optional[str] = Field(default=None, description="ISO 8601 creation timestamp.", examples=["2026-02-15T08:30:00Z"])
    average_order_value: Optional[float] = Field(default=None, description="Average order value in USD.", examples=[125.50])
    return_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Return rate [0.0 to 1.0].", examples=[0.05])
    suspicious_activity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Upstream suspicious activity score [0.0 to 1.0].", examples=[0.02])
    order_count: Optional[int] = Field(default=None, ge=0, description="Lifetime order count.")
    total_spend: Optional[float] = Field(default=None, ge=0.0, description="Gross spend.")
    return_count: Optional[int] = Field(default=None, ge=0, description="Lifetime return count.")
    refund_count: Optional[int] = Field(default=None, ge=0, description="Lifetime refund count.")
    refund_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Refund rate.")
    high_value_order_count: Optional[int] = Field(default=None, ge=0, description="High-value order count.")
    device_type: Optional[str] = Field(default=None, description="Device fingerprint type.")
    primary_payment_method: Optional[str] = Field(default=None, description="Payment instrument category.")


class EntityEdgeInput(BaseModel):
    """Input payload representing a bipartite entity link (DEVICE, IP, PAYMENT, ADDRESS)."""
    model_config = ConfigDict(extra="allow")

    account_id: str = Field(description="Account node identifier linked to the entity token.", examples=["ACC_000001"])
    entity_type: str = Field(description="Canonical entity type: DEVICE, IP, PAYMENT, ADDRESS.", examples=["DEVICE"])
    entity_id: str = Field(description="Unique entity token identifier.", examples=["DEV_PHONE_00001"])
    edge_id: Optional[str] = Field(default=None, description="Unique edge identifier.")
    first_seen_at: Optional[str] = Field(default=None, description="First seen ISO 8601 timestamp.")
    last_seen_at: Optional[str] = Field(default=None, description="Last seen ISO 8601 timestamp.")
    interaction_count: Optional[int] = Field(default=None, ge=1, description="Number of observed interactions.")
    event_type: Optional[str] = Field(default=None, description="Interaction event type (e.g. CHECKOUT, LOGIN).")


class AbuseRingRequest(BaseModel):
    """Input payload representing a candidate connected component subgraph."""
    model_config = ConfigDict(extra="allow")

    accounts: List[AccountNodeInput] = Field(default_factory=list, description="List of account nodes in candidate cluster.")
    edges: List[EntityEdgeInput] = Field(default_factory=list, description="List of bipartite entity interaction edges.")
    cluster_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional cluster-level summary metadata.")


class EvidenceAdjustmentItem(BaseModel):
    """Individual evidence modifier signal."""
    code: str = Field(description="Unique adjustment code.")
    delta: float = Field(description="Score modifier delta.")
    reason: str = Field(description="Human-readable explanation of the adjustment.")


class EvidenceAdjustmentsResponse(BaseModel):
    """Structured breakdown of deterministic evidence adjustments."""
    positive_adjustments: List[EvidenceAdjustmentItem] = Field(default_factory=list, description="Escalating risk factors.")
    mitigating_adjustments: List[EvidenceAdjustmentItem] = Field(default_factory=list, description="Protective mitigating factors.")
    total_positive_delta: float = Field(description="Sum of positive deltas (capped at +0.15).")
    total_negative_delta: float = Field(description="Sum of negative deltas (bounded at -0.30).")
    net_delta: float = Field(description="Net score adjustment applied.")


class AccountAttributionItem(BaseModel):
    """Deterministic account-level operational attribution within candidate ring."""
    account_id: str = Field(description="Account identifier.")
    attribution_role: str = Field(description="Role classification: CORE_MEMBER, PERIPHERAL_MEMBER, or INCIDENTAL_BYSTANDER.")
    linked_ring_accounts_count: int = Field(description="Number of other cluster accounts sharing tokens with this account.")
    shared_entity_types: List[str] = Field(default_factory=list, description="Entity token types shared with other members.")
    bipartite_degree: float = Field(description="Normalized degree centrality in projected 1-mode cluster graph.")
    suspicious_activity_score: float = Field(description="Individual suspicious activity score.")
    risk_contribution: str = Field(description="Qualitative risk contribution tier: HIGH, MEDIUM, or LOW.")
    attribution_reasoning: str = Field(description="Deterministic rationale for the assigned role.")


class ModelMetadataResponse(BaseModel):
    """Metadata regarding the underlying frozen Abuse-Ring ML model."""
    model_version: str = Field(description="Model artifact version.")
    feature_schema_version: str = Field(description="Feature schema definition version.")
    calibrated: bool = Field(description="Whether the probability output is calibrated.")


class AbuseRingResponse(BaseModel):
    """Comprehensive structured response for Abuse-Ring Sentinel evaluation."""
    cluster_id: str = Field(description="Evaluated cluster identifier.")
    ring_detected: bool = Field(description="Binary flag indicating whether an abuse ring was detected.")
    raw_ml_probability: float = Field(description="Raw calibrated ML model probability [0.0 to 1.0].")
    model_prediction: bool = Field(description="Model prediction at frozen threshold (0.50).")
    model_threshold: float = Field(description="Frozen operational model threshold (0.50).")
    evidence_adjustments: EvidenceAdjustmentsResponse = Field(description="Deterministic evidence adjustments.")
    final_ring_score: float = Field(description="Operational risk score [0.0 to 1.0] after evidence adjustments.")
    risk_level: str = Field(description="Qualitative risk tier: LOW, MEDIUM, HIGH, or CRITICAL.")
    verdict: str = Field(description="Operational verdict: NO_RING, POSSIBLE_RING, LIKELY_RING, or HIGH_CONFIDENCE_RING.")
    evidence_quality: str = Field(description="Sample quality tier: SUFFICIENT, LIMITED_SAMPLE, or INSUFFICIENT_SAMPLE.")
    confidence: str = Field(description="Evidence reliability confidence: HIGH, MEDIUM, or LOW.")
    cluster_size: int = Field(description="Total member count evaluated in cluster.")
    ring_factors: List[str] = Field(default_factory=list, description="Topological and behavioral factors elevating concern.")
    mitigating_factors: List[str] = Field(default_factory=list, description="Protective benign factors reducing concern.")
    evidence_summary: str = Field(description="Concise plain-language summary of graph connectivity.")
    decision_reasoning: str = Field(description="Step-by-step reasoning linking ML probability, evidence, and actions.")
    account_attribution: List[AccountAttributionItem] = Field(default_factory=list, description="Account-level attribution breakdown.")
    recommended_action: str = Field(description="Recommended operational policy action.")
    model_metadata: ModelMetadataResponse = Field(description="Model artifact metadata.")
    diagnostics: Optional[List[str]] = Field(default_factory=list, description="Diagnostic warnings or parsing notes.")


# Live Abuse Graph Response Schemas
class LiveGraphEdgeItem(BaseModel):
    """Bipartite interaction edge in the live graph."""
    account_id: str = Field(description="Account identifier.")
    entity_type: str = Field(description="Entity type: DEVICE, IP, PAYMENT, ADDRESS.")
    entity_id: str = Field(description="Canonical entity token (hashed for ADDRESS, payment_id for PAYMENT).")
    first_seen_at: str = Field(description="ISO 8601 first observed timestamp.")
    last_seen_at: str = Field(description="ISO 8601 last observed timestamp.")
    interaction_count: int = Field(description="Number of recorded interactions on this edge.")
    payment_status: Optional[str] = Field(default=None, description="Latest payment status if entity is PAYMENT.")
    amount: Optional[float] = Field(default=None, description="Payment monetary amount.")
    currency: Optional[str] = Field(default=None, description="Currency code.")


class LiveSharedEntityItem(BaseModel):
    """Shared infrastructure token bridging multiple accounts."""
    entity_type: str = Field(description="Bridging entity type (DEVICE, IP, ADDRESS).")
    entity_id: str = Field(description="Opaque or canonical entity identifier.")
    account_count: int = Field(description="Number of accounts sharing this token.")


class LiveClusterCandidateItem(BaseModel):
    """Candidate connected component discovered in the live graph."""
    cluster_id: str = Field(description="Synthesized live cluster identifier.")
    member_count: int = Field(description="Total number of accounts in this candidate component.")
    account_ids: List[str] = Field(description="List of accounts belonging to this cluster.")
    is_multi_account: bool = Field(description="True if cluster contains >= 2 accounts sharing infrastructure.")
    shared_entities: List[LiveSharedEntityItem] = Field(default_factory=list, description="Shared infrastructure entities.")
    total_entities_count: int = Field(description="Total entity tokens associated with this cluster.")
    total_edges_count: int = Field(description="Total edges connecting accounts and entities in this cluster.")


class LiveGraphRecentEventItem(BaseModel):
    """Recent event audit record in the live graph."""
    event_id: str = Field(description="Webhook event identifier.")
    event_type: str = Field(description="Webhook event type.")
    account_id: str = Field(description="Associated account identifier.")
    payment_id: Optional[str] = Field(default=None, description="Payment identifier.")
    status: str = Field(description="Payment status.")
    association_source: str = Field(description="Association source mechanism.")
    entities_observed: List[Dict[str, str]] = Field(default_factory=list, description="Entities recorded.")
    timestamp: str = Field(description="Timestamp.")


class LiveAbuseGraphResponse(BaseModel):
    """Operational state and candidate clusters from the live abuse graph."""
    status: str = Field(description="Graph ingestion status ('active' or 'idle').")
    total_webhook_events: int = Field(description="Total accepted non-duplicate webhook events processed.")
    total_accounts: int = Field(description="Total unique accounts observed in the graph.")
    total_entities: int = Field(description="Total unique entity tokens recorded.")
    total_edges: int = Field(description="Total bipartite edges in the graph.")
    candidate_clusters_count: int = Field(description="Number of candidate connected components.")
    candidate_clusters: List[LiveClusterCandidateItem] = Field(default_factory=list, description="List of candidate clusters.")
    recent_events: List[LiveGraphRecentEventItem] = Field(default_factory=list, description="Recent webhook event stream.")
    last_activity_at: Optional[str] = Field(default=None, description="Timestamp of the latest graph event.")


class LiveGraphAnalysisRequest(BaseModel):
    """Optional filter parameters for evaluating a live candidate cluster."""
    cluster_id: Optional[str] = Field(default=None, description="Target live cluster ID to evaluate.")
    account_id: Optional[str] = Field(default=None, description="Target account ID to evaluate with its neighborhood.")


class LiveAbuseSimulationRequest(BaseModel):
    """Request payload for running a live attack simulation scenario."""
    scenario: str = Field(
        default="CLEAN_SHARED_INFRASTRUCTURE",
        description="Scenario: CLEAN_SHARED_INFRASTRUCTURE, COORDINATED_SUSPICIOUS_CLUSTER, HIGH_CONFIDENCE_ABUSE_RING, or BYSTANDER_MIXED_CLUSTER",
    )


class LiveAbuseSimulationResponse(BaseModel):
    """Response payload containing simulation topology and frozen Abuse-Ring Sentinel evaluation."""
    scenario: str
    is_synthetic_simulation: bool = True
    cluster_id: str
    account_count: int
    entity_count: int
    shared_entities: List[Dict[str, Any]] = Field(default_factory=list)
    evaluation: AbuseRingResponse
    cluster_data: Optional[Dict[str, Any]] = None


class CreatePaymentOrderRequest(BaseModel):
    """Application-owned checkout/order initiation request."""
    account_id: str = Field(description="Account identifier initiating the payment.")
    amount: int = Field(default=15000, ge=100, description="Amount in currency subunits (e.g. paise for INR).")
    currency: str = Field(default="INR", description="Three-letter currency code.")
    device_id: Optional[str] = Field(default=None, description="Optional application-observed device identifier.")
    address: Optional[str] = Field(default=None, description="Optional application-observed billing or shipping address.")
    correlation_id: Optional[str] = Field(default=None, description="Optional custom correlation key.")


class CreatePaymentOrderResponse(BaseModel):
    """Application-owned checkout/order initiation response."""
    order_id: str = Field(description="Order identifier (Razorpay order ID or deterministic test ID).")
    correlation_id: str = Field(description="Correlation identifier linking application context to webhook.")
    account_id: str = Field(description="Account identifier.")
    amount: int = Field(description="Monetary amount in subunits.")
    currency: str = Field(description="Currency code.")
    device_id: Optional[str] = Field(default=None, description="Normalized device identifier if provided.")
    ip_captured: bool = Field(description="True if a genuine client connection IP was observed.")
    address_captured: bool = Field(default=False, description="True if a valid address was observed and hashed.")



# Exception Handlers
@app.exception_handler(AccountInputValidationError)
async def handle_input_validation_error(request: Request, exc: AccountInputValidationError):
    """Handle custom validation errors with a structured 400 response."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "errors": exc.errors},
    )


@app.exception_handler(TypeError)
async def handle_type_error(request: Request, exc: TypeError):
    """Handle type errors with a 400 response."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# API Endpoints
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Check API health and verify that the risk scoring ML engine is loaded and available."""
    scorer = get_scorer()
    model_loaded = scorer.pipeline is not None
    model_type = scorer.metadata.get("model_type", "RandomForestClassifier Pipeline")

    return HealthResponse(
        status="healthy",
        service="AI-RISK Abuse Detection Engine",
        version="1.0.0",
        model_loaded=model_loaded,
        model_type=model_type,
    )


@app.get(
    "/risk/account/{account_id}",
    response_model=AccountProfileResponse,
    status_code=status.HTTP_200_OK,
    tags=["Account Risk"],
    summary="Retrieve authentic merchant account profile by identifier",
)
def get_account_profile(account_id: str) -> Dict[str, Any]:
    """Retrieve indexed account behavioral profile for risk investigation.

    Looks up authentic records from synthetic accounts registry and canonical benchmarks.
    Returns calculated metrics (return_rate, refund_rate, AOV) without fabrication.
    Includes separate live_activity section derived strictly from Razorpay webhooks.
    """
    store = get_account_store()
    account = store.get_account(account_id, include_live=True)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found in registry.",
        )
    return account


@app.get(
    "/risk/account/{account_id}/live",
    response_model=LiveActivityResponse,
    status_code=status.HTTP_200_OK,
    tags=["Account Risk"],
    summary="Retrieve real-time live activity for an account",
)
def get_account_live_activity(account_id: str) -> Dict[str, Any]:
    """Retrieve isolated live activity metrics derived from real-time Razorpay webhooks.

    Enables calm targeted polling of live transaction activity without refetching historical profiles.
    """
    store = get_account_store()
    account = store.get_account(account_id, include_live=True)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found in registry.",
        )
    return account.get("live_activity", {})


@app.get(
    "/risk/accounts/samples",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    tags=["Account Risk"],
    summary="List sample account identifiers for investigation suggestions",
)
def list_sample_accounts(limit: int = 10) -> List[str]:
    """Return realistic account identifiers for analyst lookups."""
    store = get_account_store()
    return store.list_sample_ids(limit=limit)


@app.post(
    "/risk/score",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    tags=["Risk Scoring"],
)
def score_account_risk(payload: AccountRiskRequest) -> Dict[str, Any]:
    """Score merchant account risk for coordinated abuse.

    Validates and sanitizes input features through the existing validation layer,
    evaluates behavioral metrics with the trained ML pipeline, and returns
    calibrated 0-100 risk score, risk tier, and policy actions.
    """
    try:
        # 1. Convert request model to dictionary
        input_data = payload.model_dump()

        # 2. Score with the existing RiskScorer engine
        scorer = get_scorer()
        result = scorer.predict_account(input_data)
        return result

    except AccountInputValidationError as e:
        logger.warning(f"Validation error on /risk/score: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TypeError as e:
        logger.warning(f"Type error on /risk/score: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected internal error during risk scoring: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the risk assessment.",
        )


@app.post(
    "/risk/fraud-spike",
    response_model=FraudSpikeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Fraud-Spike Detection"],
)
def detect_fraud_spike(payload: FraudSpikeRequest) -> Dict[str, Any]:
    """Detect temporal fraud spikes, velocity surges, and cluster attacks across merchant traffic.

    Compares baseline window metrics against current window activity to determine
    whether a sudden, statistically significant surge in fraudulent activity has occurred.
    """
    try:
        input_data = payload.model_dump()
        detector = get_spike_detector()
        result = detector.detect_spike(input_data)
        return result
    except Exception as e:
        logger.error(f"Error during fraud-spike detection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing fraud-spike detection.",
        )


@app.get(
    "/risk/fraud-spike/live",
    response_model=LiveFraudSpikeTelemetryResponse,
    status_code=status.HTTP_200_OK,
    tags=["Fraud-Spike Detection"],
    summary="Get real-time live telemetry and rolling window metrics for Fraud Spike Radar",
)
def get_live_fraud_spike_telemetry(merchant_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve operational rolling 5m and 1h telemetry derived continuously from verified Razorpay webhooks.

    Does not trigger model inference. Lightweight operational telemetry endpoint for 15s calm polling.
    """
    store = get_live_fraud_telemetry_store()
    return store.get_telemetry_state(merchant_id=merchant_id)


@app.post(
    "/risk/fraud-spike/live/evaluate",
    response_model=FraudSpikeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Fraud-Spike Detection"],
    summary="Evaluate current live telemetry using the existing frozen FraudSpikeDetector",
)
def evaluate_live_fraud_spike(payload: Optional[LiveFraudEvaluationRequest] = None) -> Dict[str, Any]:
    """Evaluate live rolling telemetry with the frozen FraudSpikeDetector.

    Flow:
    1. Read live telemetry metrics from LiveFraudSpikeTelemetryStore.
    2. Normalize into valid FraudSpikeRequest via export_fraud_spike_request().
    3. Evaluate via frozen FraudSpikeDetector.detect_spike().
    Maintains identical FraudSpikeResponse contract. Zero model or formula alterations.
    """
    store = get_live_fraud_telemetry_store()
    mid = payload.merchant_id if payload else None
    spike_req_dict = store.export_fraud_spike_request(merchant_id=mid)

    try:
        detector = get_spike_detector()
        result = detector.detect_spike(spike_req_dict)
        return result
    except Exception as e:
        logger.error(f"Error evaluating live fraud spike: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while evaluating live fraud spike telemetry.",
        )


@app.post(
    "/risk/abuse-ring",
    response_model=AbuseRingResponse,
    status_code=status.HTTP_200_OK,
    tags=["Abuse-Ring Sentinel"],
)
def detect_abuse_ring(payload: AbuseRingRequest) -> Dict[str, Any]:
    """Detect coordinated merchant abuse rings and syndicate multi-accounting topologies.

    Evaluates candidate connected component subgraphs using graph topology,
    multi-entity token sharing, behavioral synchronization, and temporal coordination.
    """
    try:
        accounts_data = [a.model_dump() for a in payload.accounts]
        edges_data = [e.model_dump() for e in payload.edges]
        cluster_meta = payload.cluster_metadata

        sentinel = get_abuse_ring_sentinel()
        result = sentinel.detect(
            accounts=accounts_data,
            edges=edges_data,
            cluster_metadata=cluster_meta,
        )
        return result
    except (ValueError, TypeError) as e:
        logger.warning(f"Bad request error on /risk/abuse-ring: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during abuse-ring detection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing abuse-ring detection.",
        )


@app.get(
    "/risk/abuse-ring/live",
    response_model=LiveAbuseGraphResponse,
    status_code=status.HTTP_200_OK,
    tags=["Abuse-Ring Sentinel"],
    summary="Get real-time Live Abuse Graph state and candidate clusters",
)
def get_live_abuse_graph() -> Dict[str, Any]:
    """Retrieve operational state, candidate clusters, and recent linkages from the live graph."""
    store = get_live_abuse_graph_store()
    return store.get_live_graph_state()


@app.get(
    "/risk/abuse-ring/live/{account_id}",
    status_code=status.HTTP_200_OK,
    tags=["Abuse-Ring Sentinel"],
    summary="Get live graph subgraph and candidate cluster for a specific account",
)
def get_live_abuse_graph_for_account(account_id: str) -> Dict[str, Any]:
    """Retrieve direct edges and matching cluster candidate for a specific account."""
    store = get_live_abuse_graph_store()
    subgraph = store.get_account_subgraph(account_id)
    if subgraph is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' has no recorded live webhook activity in the graph.",
        )
    return subgraph


@app.post(
    "/risk/abuse-ring/live/analyze",
    response_model=AbuseRingResponse,
    status_code=status.HTTP_200_OK,
    tags=["Abuse-Ring Sentinel"],
    summary="Evaluate a candidate cluster from the live graph using the frozen Abuse-Ring Sentinel",
)
def analyze_live_abuse_cluster(payload: Optional[LiveGraphAnalysisRequest] = None) -> Dict[str, Any]:
    """Export candidate cluster from the live graph into canonical AbuseRingRequest and evaluate.

    Adheres strictly to the single-source-of-truth requirement:
    - Does NOT introduce a second scoring model or secondary scoring rules.
    - Evaluates via the frozen, calibrated AbuseRingSentinel.
    """
    store = get_live_abuse_graph_store()
    c_id = payload.cluster_id if payload else None
    acc_id = payload.account_id if payload else None

    ring_request_data = store.export_cluster_to_abuse_ring_request(cluster_id=c_id, account_id=acc_id)
    if not ring_request_data.get("accounts"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No accounts found in the live abuse graph to evaluate. Ingest webhooks first.",
        )

    try:
        sentinel = get_abuse_ring_sentinel()
        return sentinel.detect(
            accounts=ring_request_data["accounts"],
            edges=ring_request_data["edges"],
            cluster_metadata=ring_request_data.get("cluster_metadata"),
        )
    except Exception as e:
        logger.error(f"Error evaluating live abuse cluster: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while evaluating the live abuse cluster.",
        )


@app.post(
    "/risk/abuse-ring/live/reset",
    status_code=status.HTTP_200_OK,
    tags=["Abuse-Ring Sentinel"],
    summary="Reset the live abuse graph state (development/testing)",
)
def reset_live_abuse_graph() -> Dict[str, Any]:
    """Reset the Live Abuse Graph in-memory store."""
    store = get_live_abuse_graph_store()
    store.reset()
    return {"status": "ok", "message": "Live abuse graph store has been reset."}


@app.post(
    "/risk/abuse-ring/live/simulate",
    response_model=LiveAbuseSimulationResponse,
    status_code=status.HTTP_200_OK,
    tags=["Abuse-Ring Sentinel"],
    summary="Execute a deterministic live attack simulation scenario and evaluate with frozen AbuseRingSentinel",
)
def simulate_live_abuse_ring(
    payload: LiveAbuseSimulationRequest,
    request: Request,
) -> Dict[str, Any]:
    """Execute a deterministic live attack simulation scenario.

    Strict single-source-of-truth:
    - Feeds authentic application correlation and webhook events into the Live Abuse Graph.
    - Evaluates via the existing frozen AbuseRingSentinel.
    - Zero model alterations, no hard-coded risk tiers, and complete bystander protection.
    """
    from src.live_simulation import execute_simulation_scenario
    client_ip = extract_client_ip(
        client_host=request.client.host if request.client else None,
        headers=dict(request.headers),
    )
    try:
        result = execute_simulation_scenario(payload.scenario, client_ip=client_ip)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing live abuse simulation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation error: {str(e)}",
        )


@app.post(
    "/payments/create-order",
    response_model=CreatePaymentOrderResponse,
    status_code=status.HTTP_200_OK,
    tags=["Payments"],
    summary="Initiate application-owned checkout/order and capture genuine client connection IP",
)
def create_payment_order(payload: CreatePaymentOrderRequest, request: Request) -> Dict[str, Any]:
    """Initiate an application-controlled payment order and capture real client IP.

    Observes client connection IP from server connection metadata (or configured trusted proxy).
    Creates short-lived payment context correlation mapping for verified webhook processing.
    Does NOT expose raw customer IP in the public response.
    """
    client_ip = extract_client_ip(
        client_host=request.client.host if request.client else None,
        headers=dict(request.headers),
    )

    corr_id = payload.correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
    clean_dev = normalize_device_id(payload.device_id)

    # Check if Razorpay API keys are configured to create a real Razorpay Order
    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    order_id = f"order_{corr_id}"

    if key_id and key_secret:
        try:
            auth_str = f"{key_id}:{key_secret}"
            auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            order_payload = {
                "amount": payload.amount,
                "currency": payload.currency,
                "receipt": f"rcpt_{corr_id[:16]}",
                "notes": {
                    "account_id": payload.account_id,
                    "device_id": clean_dev or "",
                    "correlation_id": corr_id,
                },
            }
            req = urllib.request.Request(
                "https://api.razorpay.com/v1/orders",
                data=json.dumps(order_payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {auth_b64}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("id"):
                    order_id = data["id"]
        except Exception as e:
            logger.warning(f"[PaymentOrder] Real Razorpay order creation failed, using fallback order_id: {e}")

    # Clean and hash address if supplied (NEVER store raw address)
    addr_hash = canonicalize_address(payload.address) if payload.address else None

    # Record context in PaymentContextStore
    ctx_store = get_payment_context_store()
    ctx_store.record_context(
        correlation_id=corr_id,
        account_id=payload.account_id,
        observed_ip=client_ip,
        device_id=clean_dev,
        observed_address_hash=addr_hash,
        order_id=order_id,
    )

    return {
        "order_id": order_id,
        "correlation_id": corr_id,
        "account_id": payload.account_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "device_id": clean_dev,
        "ip_captured": bool(client_ip),
        "address_captured": bool(addr_hash),
    }


@app.post(
    "/payments/context/reset",
    status_code=status.HTTP_200_OK,
    tags=["Payments"],
    summary="Reset payment context store (development/testing)",
)
def reset_payment_context() -> Dict[str, Any]:
    """Reset the PaymentContextStore in-memory cache."""
    ctx_store = get_payment_context_store()
    ctx_store.reset()
    return {"status": "ok", "message": "Payment context store has been reset."}



@app.post(
    "/webhooks/razorpay",
    status_code=status.HTTP_200_OK,
    tags=["Webhooks"],
    summary="Ingest real-time Razorpay Test Mode webhook events",
)
async def razorpay_webhook(request: Request) -> JSONResponse:
    """Ingest, verify, normalize, and feed real-time Razorpay Test Mode events into Fraud Spike.

    Validates HMAC-SHA256 signature against the exact raw request body.
    Enforces x-razorpay-event-id idempotency (10,000 bounded capacity).
    Tracks canonical payment lifecycle (payment.captured canonical, payment.authorized safe, payment.failed != fraud).
    Ingests transaction velocity into FiveMinuteTelemetryStore with zero-fabrication guarantees.
    """
    raw_body = await request.body()
    headers = dict(request.headers)
    manager = get_webhook_manager()
    detector = get_spike_detector()

    status_code, result = manager.process_webhook(
        raw_body=raw_body,
        headers=headers,
        detector=detector,
    )
    return JSONResponse(status_code=status_code, content=result)


@app.get(
    "/webhooks/razorpay/status",
    status_code=status.HTTP_200_OK,
    tags=["Webhooks"],
    summary="Get operational status of Razorpay webhook ingestion",
)
def get_razorpay_webhook_status() -> Dict[str, Any]:
    """Retrieve operational telemetry and health metrics for the Razorpay Test Mode webhook pipeline.

    Does not expose secrets, credentials, or customer PII.
    """
    manager = get_webhook_manager()
    return manager.get_status()


@app.get(
    "/webhooks/razorpay/events",
    status_code=status.HTTP_200_OK,
    tags=["Webhooks"],
    summary="Get recent risk events from Razorpay Test Mode ingestion",
)
def get_razorpay_recent_events() -> List[Dict[str, Any]]:
    """Retrieve recent risk event representations formatted for Risk Operations integration."""
    manager = get_webhook_manager()
    return manager.get_recent_risk_events()


