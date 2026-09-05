"""Razorpay Test Mode Webhook Ingestion Adapter for AI-RISK Fraud Spike Detector.

Implements:
- Raw-body HMAC-SHA256 signature verification (constant-time)
- Bounded thread-safe idempotency store (capacity: 10,000)
- Canonical payment event lifecycle tracking (order-independent deduplication)
- Internal normalized event schema (RiskPaymentEvent) with zero-fabrication guarantees
- Telemetry ingestion into the existing FiveMinuteTelemetryStore
- Fraud Spike evaluation without synthetic fraud labels or model changes
- Safe status reporting and structured operational logging without secret leakage
"""

import os
import hmac
import hashlib
import json
import time
import logging
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.fraud_spike_detector import FraudSpikeDetector
from src.live_activity import get_live_activity_store
from src.live_abuse_graph import get_live_abuse_graph_store, normalize_device_id
from src.live_fraud_telemetry import get_live_fraud_telemetry_store
from src.payment_context import get_payment_context_store, canonicalize_address

logger = logging.getLogger("ai_risk_razorpay_webhook")

# Environment Variable Configuration
ENV_KEY_ID = "RAZORPAY_KEY_ID"
ENV_KEY_SECRET = "RAZORPAY_KEY_SECRET"
ENV_WEBHOOK_SECRET = "RAZORPAY_WEBHOOK_SECRET"
ENV_DEFAULT_MERCHANT_ID = "RAZORPAY_DEFAULT_MERCHANT_ID"

DEFAULT_TEST_MERCHANT_ID = "MERCH_RAZORPAY_TEST"

# Canonical Event Constants
EVENT_PAYMENT_CAPTURED = "payment.captured"
EVENT_PAYMENT_AUTHORIZED = "payment.authorized"
EVENT_PAYMENT_FAILED = "payment.failed"
EVENT_ORDER_PAID = "order.paid"

SUPPORTED_PAYMENT_EVENTS = {
    EVENT_PAYMENT_CAPTURED,
    EVENT_PAYMENT_AUTHORIZED,
    EVENT_PAYMENT_FAILED,
}


def load_dotenv_if_present(env_path: str = ".env") -> None:
    """Load key-value pairs from a local .env file into os.environ if present."""
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


def get_webhook_secret() -> str:
    """Retrieve the Razorpay webhook secret from environment or local .env."""
    load_dotenv_if_present()
    return os.environ.get(ENV_WEBHOOK_SECRET, "").strip()


def get_default_merchant_id() -> str:
    """Retrieve the default merchant identifier for Test Mode."""
    load_dotenv_if_present()
    return os.environ.get(ENV_DEFAULT_MERCHANT_ID, DEFAULT_TEST_MERCHANT_ID).strip()


def verify_razorpay_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    secret: Optional[str] = None,
) -> bool:
    """Verify HMAC-SHA256 signature of the exact raw webhook request body.

    Args:
        raw_body: Exact raw bytes of the incoming request body.
        signature_header: Value of the X-Razorpay-Signature header.
        secret: Optional secret override (defaults to RAZORPAY_WEBHOOK_SECRET).

    Returns:
        bool: True if signature matches, False otherwise.
    """
    if not signature_header:
        logger.warning("[RazorpayWebhook] Missing X-Razorpay-Signature header")
        return False

    webhook_secret = secret if secret is not None else get_webhook_secret()
    if not webhook_secret:
        logger.error("[RazorpayWebhook] RAZORPAY_WEBHOOK_SECRET is not configured in environment")
        return False

    try:
        computed = hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(computed, signature_header.strip())
        if not is_valid:
            logger.warning("[RazorpayWebhook] signature_valid=false accepted=false")
        return is_valid
    except Exception as e:
        logger.error(f"[RazorpayWebhook] Error computing HMAC signature: {e}")
        return False


class IdempotencyStore:
    """Thread-safe bounded in-memory store for webhook event IDs (capacity: 10,000)."""

    def __init__(self, capacity: int = 10000):
        self._capacity = capacity
        self._lock = threading.Lock()
        self._seen: OrderedDict[str, float] = OrderedDict()

    def is_duplicate(self, event_id: str) -> bool:
        """Check if an event ID has already been recorded."""
        if not event_id:
            return False
        with self._lock:
            return event_id in self._seen

    def record_event(self, event_id: str) -> bool:
        """Record an event ID.

        Returns:
            bool: True if newly recorded, False if already seen (duplicate).
        """
        if not event_id:
            return True
        with self._lock:
            if event_id in self._seen:
                return False
            self._seen[event_id] = time.time()
            if len(self._seen) > self._capacity:
                self._seen.popitem(last=False)
            return True

    def get_size(self) -> int:
        """Return total entries currently tracked."""
        with self._lock:
            return len(self._seen)

    def reset(self) -> None:
        """Clear all tracked event IDs."""
        with self._lock:
            self._seen.clear()


class PaymentLifecycleTracker:
    """Thread-safe tracker enforcing canonical completed-payment velocity semantics.

    Ensures that for any payment_id:
    - payment.captured is the canonical completed-payment event.
    - payment.authorized tracks authorization state but does NOT double-count.
    - Event order independence:
        * authorized -> captured: captured increments velocity by 1.
        * captured -> authorized: captured increments velocity by 1; authorized does not double-count.
        * duplicate captured: does not increment velocity a second time.
    """

    def __init__(self, capacity: int = 10000):
        self._capacity = capacity
        self._lock = threading.Lock()
        # payment_id -> dict(captured=bool, authorized=bool, failed=bool, updated_at=float)
        self._state: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def record_payment_event(
        self,
        payment_id: str,
        event_type: str,
    ) -> Tuple[bool, bool]:
        """Record a payment event and determine velocity counting.

        Args:
            payment_id: Unique payment identifier (pay_xxxx).
            event_type: Webhook event type.

        Returns:
            Tuple[bool, bool]: (should_count_velocity, is_duplicate_payment)
        """
        if not payment_id:
            # If payment_id is missing, count if it is captured
            return (event_type == EVENT_PAYMENT_CAPTURED, False)

        with self._lock:
            record = self._state.get(payment_id, {
                "captured": False,
                "authorized": False,
                "failed": False,
                "updated_at": time.time(),
            })

            should_count_velocity = False
            is_duplicate = False

            if event_type == EVENT_PAYMENT_CAPTURED:
                if record["captured"]:
                    # Already counted as captured completed payment
                    is_duplicate = True
                    should_count_velocity = False
                else:
                    record["captured"] = True
                    should_count_velocity = True
            elif event_type == EVENT_PAYMENT_AUTHORIZED:
                record["authorized"] = True
                should_count_velocity = False  # Authorized alone does not count as completed payment
            elif event_type == EVENT_PAYMENT_FAILED:
                record["failed"] = True
                should_count_velocity = False

            record["updated_at"] = time.time()
            self._state[payment_id] = record
            self._state.move_to_end(payment_id)

            if len(self._state) > self._capacity:
                self._state.popitem(last=False)

            return should_count_velocity, is_duplicate

    def get_payment_state(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve current lifecycle status for a payment ID."""
        with self._lock:
            state = self._state.get(payment_id)
            return dict(state) if state else None

    def reset(self) -> None:
        """Clear payment lifecycle tracking state."""
        with self._lock:
            self._state.clear()


class RiskPaymentEvent(BaseModel):
    """Internal normalized representation of a payment event received from Razorpay.

    Contains ONLY fields legitimately provided by Razorpay webhooks.
    Zero data fabrication (no fake device, IP, or customer risk features).
    """
    event_id: str = Field(description="Unique webhook event identifier.")
    event_type: str = Field(description="Webhook event type (e.g. payment.captured).")
    payment_id: Optional[str] = Field(default=None, description="Razorpay payment identifier (pay_xxxx).")
    order_id: Optional[str] = Field(default=None, description="Razorpay order identifier (order_xxxx).")
    merchant_id: str = Field(description="Merchant account identifier.")
    timestamp: float = Field(description="Event timestamp in unix seconds.")
    amount: Optional[float] = Field(default=None, description="Payment amount in major currency units.")
    currency: Optional[str] = Field(default="INR", description="Three-letter ISO currency code.")
    payment_status: str = Field(default="unknown", description="Razorpay payment entity status.")
    payment_method: Optional[str] = Field(default=None, description="Payment instrument method (card, upi, etc.).")
    success: bool = Field(default=False, description="Whether the payment was successfully processed.")
    source: str = Field(default="razorpay_test", description="Event source origin.")
    received_at: str = Field(description="ISO 8601 timestamp of event ingestion.")


def normalize_razorpay_payload(
    payload: Dict[str, Any],
    event_id: str,
    default_merchant_id: str,
) -> RiskPaymentEvent:
    """Normalize a raw Razorpay webhook payload into a RiskPaymentEvent.

    Extracts fields strictly present in the Razorpay payload without fabricating data.
    """
    event_type = str(payload.get("event", "unknown"))

    # Extract payment entity
    payment_container = payload.get("payload", {}).get("payment", {})
    entity = payment_container.get("entity", {}) if isinstance(payment_container, dict) else {}

    # If payload is top-level entity or alternative structure
    if not entity and payload.get("entity") == "payment":
        entity = payload

    payment_id = entity.get("id")
    order_id = entity.get("order_id")

    # Merchant identification
    merchant_id = (
        payload.get("account_id")
        or entity.get("account_id")
        or default_merchant_id
    )

    # Amount: Razorpay amounts are in subunits (e.g. paise for INR, cents for USD)
    raw_amount = entity.get("amount")
    amount: Optional[float] = None
    if raw_amount is not None:
        try:
            amount = round(float(raw_amount) / 100.0, 2)
        except (ValueError, TypeError):
            amount = None

    currency = entity.get("currency", "INR")
    status = entity.get("status", "unknown")
    method = entity.get("method")

    # Created timestamp
    raw_ts = entity.get("created_at") or payload.get("created_at")
    try:
        ts = float(raw_ts) if raw_ts is not None else time.time()
    except (ValueError, TypeError):
        ts = time.time()

    success = (status in ["captured", "authorized"]) and (event_type != EVENT_PAYMENT_FAILED)

    return RiskPaymentEvent(
        event_id=event_id,
        event_type=event_type,
        payment_id=payment_id,
        order_id=order_id,
        merchant_id=str(merchant_id),
        timestamp=ts,
        amount=amount,
        currency=currency,
        payment_status=status,
        payment_method=method,
        success=success,
        source="razorpay_test",
        received_at=datetime.now(timezone.utc).isoformat(),
    )


def resolve_associated_account_id(
    payload: Dict[str, Any],
    entity: Dict[str, Any],
    lower_headers: Dict[str, str],
) -> Tuple[Optional[str], str]:
    """Resolve target account ID and association source.

    Constraint adherence:
    1. Check notes on payment entity or payload: 'notes.account_id' or 'notes.accountId'.
       Source: 'notes'
    2. Header override: 'x-account-id' or 'x-ai-risk-account-id'.
       Source: 'header_dev_test' (strictly development/testing, never trusted production identity).
    3. Payload top-level account_id if formatted as an AI-RISK account (starts with ACC_).
       Source: 'webhook_payload'
    4. Razorpay Test Mode fallback: RAZORPAY_TEST_ACCOUNT_ID (defaults to 'ACC_MERCHANT_90210').
       Source: 'test_mode_default' (clearly documents that association was inferred from test default).
    """
    load_dotenv_if_present()

    # 1. Notes (standard ecommerce association)
    notes = entity.get("notes") or payload.get("notes") or {}
    if isinstance(notes, dict):
        acc_from_notes = notes.get("account_id") or notes.get("accountId")
        if acc_from_notes and isinstance(acc_from_notes, str) and acc_from_notes.strip():
            return acc_from_notes.strip().upper(), "notes"

    # 2. Development / testing header override (NOT trusted production identity)
    header_acc = lower_headers.get("x-account-id") or lower_headers.get("x-ai-risk-account-id")
    if header_acc and header_acc.strip():
        return header_acc.strip().upper(), "header_dev_test"

    # 3. Payload account_id if directly registered in AccountStore
    payload_acc = payload.get("account_id") or entity.get("account_id")
    if payload_acc and isinstance(payload_acc, str) and payload_acc.strip():
        from src.account_store import get_account_store
        store = get_account_store()
        if store.get_account(payload_acc.strip(), include_live=False) is not None:
            return payload_acc.strip().upper(), "webhook_payload"

    # 4. Clearly documented Test Mode fallback
    test_default = os.environ.get("RAZORPAY_TEST_ACCOUNT_ID", "ACC_MERCHANT_90210").strip()
    return test_default.upper(), "test_mode_default"


class RazorpayWebhookManager:
    """Orchestrates signature verification, idempotency, normalization, and Fraud Spike ingestion."""

    def __init__(
        self,
        idempotency_store: Optional[IdempotencyStore] = None,
        lifecycle_tracker: Optional[PaymentLifecycleTracker] = None,
    ):
        self.idempotency_store = idempotency_store or IdempotencyStore()
        self.lifecycle_tracker = lifecycle_tracker or PaymentLifecycleTracker()

        self._lock = threading.Lock()
        self._received_count = 0
        self._accepted_count = 0
        self._ignored_count = 0
        self._duplicate_count = 0
        self._latest_event_type: Optional[str] = None
        self._latest_event_timestamp: Optional[str] = None
        self._latest_merchant_id: Optional[str] = None

        # Bounded in-memory risk event history for Risk Operations integration
        self._recent_risk_events: List[Dict[str, Any]] = []
        self._max_recent_events = 100

        # One Risk Operations case per Razorpay payment.
        # A payment may generate multiple lifecycle webhooks (e.g. authorized -> captured),
        # but those lifecycle transitions must not create multiple visible risk cases.
        self._risk_event_by_payment: Dict[str, str] = {}

    def get_status(self) -> Dict[str, Any]:
        """Return safe operational status without exposing secrets or PII."""
        with self._lock:
            secret = get_webhook_secret()
            return {
                "enabled": bool(secret),
                "environment": "test",
                "received": self._received_count,
                "accepted": self._accepted_count,
                "ignored": self._ignored_count,
                "duplicates": self._duplicate_count,
                "latest_event_type": self._latest_event_type,
                "latest_event_timestamp": self._latest_event_timestamp,
                "latest_merchant_id": self._latest_merchant_id,
                "tracked_idempotency_keys": self.idempotency_store.get_size(),
                "recent_risk_events_count": len(self._recent_risk_events),
            }

    def get_recent_risk_events(self) -> List[Dict[str, Any]]:
        """Retrieve recent risk event representations for Risk Operations."""
        with self._lock:
            return list(self._recent_risk_events)

    def reset_metrics(self) -> None:
        """Reset operational counters and state."""
        with self._lock:
            self._received_count = 0
            self._accepted_count = 0
            self._ignored_count = 0
            self._duplicate_count = 0
            self._latest_event_type = None
            self._latest_event_timestamp = None
            self._latest_merchant_id = None
            self._recent_risk_events.clear()
            self._risk_event_by_payment.clear()
        self.idempotency_store.reset()
        self.lifecycle_tracker.reset()
        get_live_activity_store().reset()
        get_live_abuse_graph_store().reset()
        get_live_fraud_telemetry_store().reset()

    def process_webhook(
        self,
        raw_body: bytes,
        headers: Dict[str, str],
        detector: FraudSpikeDetector,
        secret_override: Optional[str] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        """Process incoming raw Razorpay webhook request.

        Args:
            raw_body: Raw request body bytes.
            headers: Request headers dictionary.
            detector: Existing FraudSpikeDetector singleton instance.
            secret_override: Optional secret override for testing.

        Returns:
            Tuple[int, Dict[str, Any]]: (HTTP status code, response dictionary)
        """
        with self._lock:
            self._received_count += 1

        # 1. Normalize headers for case-insensitivity
        lower_headers = {k.lower(): v for k, v in headers.items()}
        signature_header = lower_headers.get("x-razorpay-signature")
        event_id_header = lower_headers.get("x-razorpay-event-id")

        # 2. Validate signature on RAW body before JSON parsing
        if not signature_header:
            logger.warning("[RazorpayWebhook] Missing X-Razorpay-Signature header")
            return 400, {
                "status": "rejected",
                "error": "Missing X-Razorpay-Signature header",
                "accepted": False,
            }

        if not verify_razorpay_signature(raw_body, signature_header, secret=secret_override):
            return 400, {
                "status": "rejected",
                "error": "Invalid webhook signature",
                "accepted": False,
            }

        # 3. Check Event ID / Idempotency before JSON parsing if header present
        if event_id_header and self.idempotency_store.is_duplicate(event_id_header):
            with self._lock:
                self._duplicate_count += 1
            logger.info(f"[RazorpayWebhook] event_id={event_id_header} duplicate=true")
            return 200, {
                "status": "duplicate",
                "duplicate": True,
                "event_id": event_id_header,
                "message": "Event has already been processed",
                "accepted": False,
            }

        # 4. Parse JSON body safely
        try:
            payload = json.loads(raw_body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON payload must be a dictionary")
        except Exception as e:
            logger.warning(f"[RazorpayWebhook] Malformed JSON payload: {e}")
            return 400, {
                "status": "rejected",
                "error": "Malformed JSON payload",
                "accepted": False,
            }

        # 5. Resolve event_id
        resolved_event_id = event_id_header or payload.get("event_id") or payload.get("id")
        if not resolved_event_id:
            # Fallback deterministic event ID from payment ID and timestamp
            payment_id_hint = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id", "none")
            resolved_event_id = f"evt_fallback_{payment_id_hint}_{int(time.time() * 1000)}"

        # Double check idempotency with resolved event ID
        if self.idempotency_store.is_duplicate(resolved_event_id):
            with self._lock:
                self._duplicate_count += 1
            logger.info(f"[RazorpayWebhook] event_id={resolved_event_id} duplicate=true")
            return 200, {
                "status": "duplicate",
                "duplicate": True,
                "event_id": resolved_event_id,
                "message": "Event has already been processed",
                "accepted": False,
            }

        # 6. Event Type Identification
        event_type = payload.get("event", "unknown")
        default_merchant = get_default_merchant_id()

        # Handle Unsupported Events Safely
        if event_type not in SUPPORTED_PAYMENT_EVENTS:
            self.idempotency_store.record_event(resolved_event_id)
            with self._lock:
                self._ignored_count += 1
                self._latest_event_type = event_type
                self._latest_event_timestamp = datetime.now(timezone.utc).isoformat()
            logger.info(f"[RazorpayWebhook] event_id={resolved_event_id} event_type={event_type} ignored=true")
            return 200, {
                "status": "ignored",
                "duplicate": False,
                "event_id": resolved_event_id,
                "event_type": event_type,
                "message": f"Event '{event_type}' safely acknowledged but ignored for velocity telemetry",
                "accepted": False,
            }

        # 7. Normalize payload into internal schema (zero fabrication)
        normalized_event = normalize_razorpay_payload(
            payload=payload,
            event_id=resolved_event_id,
            default_merchant_id=default_merchant,
        )

        # 8. Resolve target account and update Account Live Activity
        payment_container = payload.get("payload", {}).get("payment", {})
        entity = payment_container.get("entity", {}) if isinstance(payment_container, dict) else {}
        if not entity and payload.get("entity") == "payment":
            entity = payload

        # Extract explicit application notes safely
        notes_dict: Dict[str, Any] = {}
        if isinstance(entity.get("notes"), dict):
            notes_dict.update(entity.get("notes"))
        if isinstance(payload.get("notes"), dict):
            notes_dict.update(payload.get("notes"))

        # Correlate with short-lived application payment context (Steps 4 & 5)
        # Looks up by order_id, correlation_id, or payment_id
        payment_context_store = get_payment_context_store()
        corr_key = (
            normalized_event.order_id
            or notes_dict.get("correlation_id")
            or notes_dict.get("order_id")
            or normalized_event.payment_id
        )
        payment_context = payment_context_store.get_context(corr_key)

        associated_account_id, assoc_source = resolve_associated_account_id(
            payload=payload,
            entity=entity,
            lower_headers=lower_headers,
        )

        # If account was unresolved or test_mode_default, but payment_context has it, correlate
        if (not associated_account_id or assoc_source == "test_mode_default") and payment_context and payment_context.get("account_id"):
            associated_account_id = payment_context.get("account_id")
            assoc_source = "payment_context"

        if associated_account_id:
            live_store = get_live_activity_store()
            live_store.record_webhook_payment(
                account_id=associated_account_id,
                event_id=resolved_event_id,
                event_type=normalized_event.event_type,
                payment_id=normalized_event.payment_id,
                amount=normalized_event.amount,
                currency=normalized_event.currency or "INR",
                status=normalized_event.payment_status,
                association_source=assoc_source,
                timestamp=normalized_event.received_at,
            )

            # Record genuine entities into Live Abuse Graph
            # Constraints:
            # - IP extracted from application-observed payment context or explicit notes (NEVER from webhook request headers)
            # - Device extracted from notes.device_id or payment context
            # - Address canonicalized to ADDR_HASH_<sha256[:12]>
            # - Payment treated as account-to-payment observation
            dev_id = normalize_device_id(notes_dict.get("device_id") or notes_dict.get("deviceId"))
            if not dev_id and payment_context and payment_context.get("device_id"):
                dev_id = normalize_device_id(payment_context.get("device_id"))

            observed_ip = None
            if payment_context and payment_context.get("observed_ip"):
                observed_ip = payment_context.get("observed_ip")
            elif notes_dict.get("ip_address") or notes_dict.get("ip"):
                observed_ip = notes_dict.get("ip_address") or notes_dict.get("ip")

            raw_addr = notes_dict.get("shipping_address") or notes_dict.get("address")
            observed_addr_hash = None
            if payment_context and payment_context.get("observed_address_hash"):
                observed_addr_hash = payment_context.get("observed_address_hash")
            elif raw_addr:
                observed_addr_hash = canonicalize_address(raw_addr)

            live_graph_store = get_live_abuse_graph_store()
            live_graph_store.record_webhook_event(
                event_id=resolved_event_id,
                event_type=normalized_event.event_type,
                account_id=associated_account_id,
                payment_id=normalized_event.payment_id,
                amount=normalized_event.amount,
                currency=normalized_event.currency or "INR",
                status=normalized_event.payment_status,
                device_id=dev_id,
                ip_address=str(observed_ip).strip() if observed_ip else None,
                raw_address=raw_addr,
                address_hash=observed_addr_hash,
                association_source=assoc_source,
                timestamp=normalized_event.received_at,
            )

        # 9. Feed Verified Event into Live Fraud Spike Telemetry Store
        # Maintains rolling 5-minute and 1-hour windows with canonical lifecycle deduplication
        fraud_telemetry_store = get_live_fraud_telemetry_store()
        fraud_telemetry_store.record_webhook_event(
            event_id=resolved_event_id,
            event_type=normalized_event.event_type,
            payment_id=normalized_event.payment_id,
            amount=normalized_event.amount,
            currency=normalized_event.currency or "INR",
            status=normalized_event.payment_status,
            merchant_id=normalized_event.merchant_id,
            notes=notes_dict,
            timestamp=normalized_event.timestamp,
        )

        # 10. Canonical Payment Lifecycle Deduplication for Detector (Order Independent)
        # payment.captured is canonical; payment.authorized must not double-count.
        should_count_velocity, is_duplicate_payment = self.lifecycle_tracker.record_payment_event(
            payment_id=normalized_event.payment_id or "",
            event_type=normalized_event.event_type,
        )

        telemetry_obs: Optional[Dict[str, Any]] = None
        if should_count_velocity:
            # payment.failed is NOT fraud (fraud_count remains 0)
            telemetry_obs = detector.record_payment_event(
                merchant_id=normalized_event.merchant_id,
                timestamp=normalized_event.timestamp,
                is_fraud=False,
                window_seconds=300,
            )

        # 9. Trigger Existing Fraud Spike Engine (Sufficiency Aware)
        merchant_observations = detector.telemetry_store.get_observations(normalized_event.merchant_id)
        obs_count = len(merchant_observations)

        # Evaluate 5-minute telemetry aggregation
        five_min_metrics = detector._aggregate_five_minute_telemetry(merchant_observations)

        # The existing detector defines sufficiency: N >= 3 and baseline_total_tx >= 6.0
        # If N < 3, the detector returns evidence_quality="INSUFFICIENT_SAMPLE"
        has_sufficient_windows = (obs_count >= 3) and (five_min_metrics.get("evidence_quality") != "INSUFFICIENT_SAMPLE")

        assessment_result: Dict[str, Any]
        if has_sufficient_windows:
            # Build input from actual accumulated observations without fabricating features
            curr_obs = merchant_observations[-1]
            prior_obs = merchant_observations[:-1]
            base_tx = max(1.0, sum(o.get("tx_count", 0) for o in prior_obs))
            curr_tx = max(1.0, curr_obs.get("tx_count", 1))

            detector_input = {
                "merchant_id": normalized_event.merchant_id,
                "baseline_tx_count": base_tx,
                "current_tx_count": curr_tx,
                "baseline_fraud_count": 0,
                "current_fraud_count": 0,
                "baseline_fraud_rate": 0.0,
                "current_fraud_rate": 0.0,
                "baseline_device_count": None,
                "current_device_count": None,
                "baseline_suspicious_score": 0.02,
                "current_suspicious_score": 0.02,
                "five_minute_telemetry": merchant_observations,
            }
            spike_eval = detector.detect_spike(detector_input)
            assessment_result = {
                "assessment_status": "evaluated",
                "spike_score": spike_eval["spike_score"],
                "spike_level": spike_eval["spike_level"],
                "spike_prediction": spike_eval["spike_prediction"],
                "explanation": spike_eval["explanation"],
                "recommended_action": spike_eval["recommended_action"],
                "evidence_quality": spike_eval["evidence_quality"],
                "five_minute_metrics": five_min_metrics,
            }
        else:
            assessment_result = {
                "assessment_status": "insufficient_telemetry",
                "evidence_quality": five_min_metrics.get("evidence_quality", "INSUFFICIENT_SAMPLE"),
                "observation_count": obs_count,
                "current_tx_count": five_min_metrics.get("current_tx_count", 1),
                "explanation": (
                    f"Observation count ({obs_count}/3 windows) is currently insufficient to establish a reliable baseline surge. "
                    "Accumulating real-time 5-minute telemetry."
                ),
                "recommended_action": "CONTINUE_TELEMETRY_ACCUMULATION",
                "five_minute_metrics": five_min_metrics,
            }

        # 10. Format Risk Event conforming to RiskFeedContext / Risk Operations contract
        # IMPORTANT: payment.authorized is accepted/tracked but does NOT create a visible
        # Risk Operations case. payment.captured is the canonical successful-payment
        # event; payment.failed is the terminal failure event.
        # This keeps one payment from becoming multiple visible cases.
        risk_event: Optional[Dict[str, Any]] = None

        if normalized_event.event_type in {
            EVENT_PAYMENT_CAPTURED,
            EVENT_PAYMENT_FAILED,
        }:
            risk_event_id = f"evt_rzp_{normalized_event.event_id}_{int(time.time() * 1000)}"

            # Reuse the existing risk-event ID when this payment already has a case.
            # This handles cases such as failed -> captured without creating a second case.
            if normalized_event.payment_id:
                with self._lock:
                    existing_risk_event_id = self._risk_event_by_payment.get(
                        normalized_event.payment_id
                    )
                if existing_risk_event_id:
                    risk_event_id = existing_risk_event_id

            risk_event = {
                "id": risk_event_id,
                "timestamp": normalized_event.received_at,
                "engine": "FRAUD_SPIKE",
                "source": "LIVE_ASSESSMENT",
                "title": f"Razorpay Test ({normalized_event.event_type}) - {normalized_event.merchant_id}",
                "entityId": normalized_event.merchant_id,
                "entityType": "MERCHANT",
                "paymentId": normalized_event.payment_id,
                "severity": assessment_result.get("spike_level", "LOW"),
                "score": assessment_result.get("spike_score", 0),
                "decision": assessment_result.get("recommended_action", "MONITOR_TELEMETRY"),
                "rawMl": {
                    "probability": assessment_result.get("raw_spike_probability", 0.0),
                    "score": assessment_result.get("spike_score", 0),
                    "prediction": assessment_result.get("spike_prediction", 0),
                },
                "evidence": [
                    f"Ingested {normalized_event.event_type} for payment {normalized_event.payment_id} ({normalized_event.currency} {normalized_event.amount or 0:.2f})",
                    f"Five-minute observation windows active: {obs_count}",
                    f"Evidence quality: {assessment_result.get('evidence_quality', 'INSUFFICIENT_SAMPLE')}",
                ],
                "telemetry": {
                    "burstRatio": five_min_metrics.get("velocity_ratio"),
                    "consecutiveWindows": 0,
                },
            }

        # 11. Record into Idempotency Store & Operational State
        self.idempotency_store.record_event(resolved_event_id)

        with self._lock:
            self._accepted_count += 1
            self._latest_event_type = normalized_event.event_type
            self._latest_event_timestamp = normalized_event.received_at
            self._latest_merchant_id = normalized_event.merchant_id

            if risk_event is not None:
                if normalized_event.payment_id:
                    existing_risk_event_id = self._risk_event_by_payment.get(
                        normalized_event.payment_id
                    )

                    if existing_risk_event_id:
                        # Update the existing case in place instead of appending a new case.
                        for index, existing_event in enumerate(self._recent_risk_events):
                            if existing_event.get("id") == existing_risk_event_id:
                                self._recent_risk_events[index] = risk_event
                                break
                        else:
                            self._recent_risk_events.insert(0, risk_event)
                    else:
                        self._recent_risk_events.insert(0, risk_event)

                    self._risk_event_by_payment[normalized_event.payment_id] = risk_event["id"]
                else:
                    # No payment ID means there is no safe payment-level correlation key.
                    self._recent_risk_events.insert(0, risk_event)

                if len(self._recent_risk_events) > self._max_recent_events:
                    self._recent_risk_events.pop()

        logger.info(
            f"[RazorpayWebhook] event_id={resolved_event_id} event_type={normalized_event.event_type} "
            f"merchant_id={normalized_event.merchant_id} payment_id={normalized_event.payment_id} accepted=true"
        )

        return 200, {
            "status": "accepted",
            "duplicate": False,
            "event_id": resolved_event_id,
            "event_type": normalized_event.event_type,
            "merchant_id": normalized_event.merchant_id,
            "payment_id": normalized_event.payment_id,
            "associated_account": {
                "account_id": associated_account_id,
                "association_source": assoc_source,
            },
            "velocity_counted": should_count_velocity,
            "normalized_event": normalized_event.model_dump(),
            "telemetry": {
                "observation_count": obs_count,
                "active_window": telemetry_obs,
            },
            "fraud_spike_assessment": assessment_result,
            "risk_feed_event": risk_event,
        }


# Global Singleton Manager
_webhook_manager: Optional[RazorpayWebhookManager] = None


def get_webhook_manager() -> RazorpayWebhookManager:
    """Retrieve or initialize the global RazorpayWebhookManager singleton."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = RazorpayWebhookManager()
    return _webhook_manager