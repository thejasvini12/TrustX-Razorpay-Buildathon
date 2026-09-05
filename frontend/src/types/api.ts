/**
 * TypeScript definitions mirroring FastAPI backend contracts.
 */

// ==========================================
// System Health
// ==========================================
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  model_loaded: boolean;
  model_type?: string;
}

// ==========================================
// Account Risk & Return Risk
// ==========================================
export interface AccountRiskRequest {
  account_id?: string;
  order_count?: number;
  return_count?: number;
  refund_count?: number;
  total_spend?: number;
  average_order_value?: number;
  account_age_days?: number;
  device_count?: number;
  ip_count?: number;
  payment_instrument_count?: number;
  return_rate?: number | null;
  refund_rate?: number | null;
  high_value_order_count?: number;
  suspicious_activity_score?: number;
  device_type?: string;
  primary_payment_method?: string;
  live_activity?: LiveActivityData;
}

export interface LiveActivityEvent {
  event_id?: string;
  event_type: string;
  payment_id?: string;
  amount?: number | null;
  currency?: string;
  status: string;
  timestamp: string;
  association_source?: string;
}

export interface LiveActivityData {
  account_id: string;
  payment_count: number;
  failed_payment_count: number;
  payment_volume: number;
  last_payment_at: string | null;
  webhook_event_count: number;
  recent_events: LiveActivityEvent[];
  association_sources?: string[];
}

export interface DecisionPolicyResponse {
  abuse_pattern: string;
  primary_action: string;
  secondary_actions: string[];
  policy_triggers: string[];
  policy_reasoning: string;
  confidence: string;
}

export interface ReturnRiskResponse {
  return_abuse_prediction: number;
  return_risk_probability: number;
  return_risk_score: number;
  return_risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  return_risk_factors: string[];
  return_mitigating_factors: string[];
  return_explanation: string;
  recommended_return_action: string;
}

export interface FeatureContribution {
  feature: string;
  display_name?: string;
  importance: number;
  impact: string;
  observed_value?: string | number;
}

export interface RiskAssessmentResponse {
  account_id: string;
  prediction: number;
  risk_probability: number;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  risk_tier: string;
  data_quality_score: number;
  warnings: string[];
  recommended_action: 'ALLOW' | 'MANUAL_REVIEW' | 'CHALLENGE_OR_BLOCK' | string;
  explanation_summary?: string;
  decision_reasoning?: string;
  risk_increasing_signals?: string[];
  risk_reducing_signals?: string[];
  risk_factors: string[];
  mitigating_factors?: string[];
  feature_contributions?: FeatureContribution[];
  decision_policy?: DecisionPolicyResponse;
  return_risk?: ReturnRiskResponse;
}

// ==========================================
// Temporal Fraud Spike & 5-Min Telemetry
// ==========================================
export interface FiveMinuteObservation {
  timestamp?: string | null;
  tx_count: number;
  failed_count?: number | null;
  fraud_count?: number | null;
  fraud_rate?: number | null;
  device_count?: number | null;
  window_start?: number;
  window_end?: number;
}

export interface FraudSpikeRequest {
  merchant_id?: string;
  baseline_window?: string;
  current_window?: string;
  baseline_tx_count?: number;
  current_tx_count?: number;
  baseline_fraud_count?: number;
  current_fraud_count?: number;
  baseline_fraud_rate?: number | null;
  current_fraud_rate?: number | null;
  baseline_device_count?: number | null;
  current_device_count?: number | null;
  baseline_suspicious_score?: number;
  current_suspicious_score?: number;
  five_minute_telemetry?: FiveMinuteObservation[] | null;
}

export interface FraudSpikeResponse {
  merchant_id: string;
  spike_prediction: number;
  spike_probability: number;
  spike_score: number;
  spike_level: 'LOW' | 'MEDIUM' | 'HIGH';
  raw_spike_probability?: number | null;
  raw_spike_score?: number | null;
  raw_spike_level?: string | null;
  guardrail_triggered?: boolean;
  five_minute_telemetry_available?: boolean;
  five_minute_observation_count?: number;
  five_minute_current_tx_count?: number | null;
  five_minute_velocity_ratio?: number | null;
  five_minute_guardrail_triggered?: boolean;
  consecutive_anomaly_windows?: number;
  persistence_escalation_triggered?: boolean;
  baseline_window: string;
  current_window: string;
  baseline_fraud_rate: number;
  current_fraud_rate: number;
  fraud_rate_change: number;
  evidence_quality: string;
  confidence: string;
  evidence_summary: string;
  spike_factors: string[];
  mitigating_factors: string[];
  explanation: string;
  recommended_action: string;
}

export interface LiveFraud5MinMetrics {
  tx_count: number;
  tx_volume: number;
  failed_count: number;
  fraud_count: number;
  fraud_rate: number;
}

export interface LiveFraud1HourMetrics {
  tx_count: number;
  tx_volume: number;
  failed_count: number;
  fraud_count: number;
  fraud_rate: number;
}

export interface LiveFraudRecentEventItem {
  event_id: string;
  event_type: string;
  payment_id?: string | null;
  amount?: number | null;
  currency?: string | null;
  status: string;
  merchant_id: string;
  lifecycle_action: string;
  is_failed: boolean;
  explicit_fraud: boolean;
  device_id?: string | null;
  timestamp: string;
  unix_timestamp: number;
}

export interface LiveFraudSpikeTelemetryResponse {
  status: 'ACTIVE' | 'IDLE' | string;
  merchant_id: string;
  total_events_processed: number;
  last_event_timestamp?: string | null;
  rolling_5m: LiveFraud5MinMetrics;
  rolling_1h: LiveFraud1HourMetrics;
  unique_devices_1h: number;
  five_minute_observations: FiveMinuteObservation[];
  recent_events: LiveFraudRecentEventItem[];
  synthesized_request?: FraudSpikeRequest | null;
}

// ==========================================
// Abuse-Ring Sentinel
// ==========================================
export interface AccountNodeInput {
  account_id: string;
  created_at?: string | null;
  average_order_value?: number | null;
  return_rate?: number | null;
  suspicious_activity_score?: number | null;
  order_count?: number | null;
  total_spend?: number | null;
  return_count?: number | null;
  refund_count?: number | null;
  refund_rate?: number | null;
  high_value_order_count?: number | null;
  device_type?: string | null;
  primary_payment_method?: string | null;
}

export interface EntityEdgeInput {
  account_id: string;
  entity_type: 'DEVICE' | 'IP' | 'PAYMENT' | 'ADDRESS' | string;
  entity_id: string;
  edge_id?: string | null;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  interaction_count?: number | null;
  event_type?: string | null;
}

export interface AbuseRingRequest {
  accounts: AccountNodeInput[];
  edges: EntityEdgeInput[];
  cluster_metadata?: Record<string, any> | null;
}

export interface LiveAbuseSimulationRequest {
  scenario: string;
}

export interface LiveAbuseSimulationResponse {
  scenario: string;
  is_synthetic_simulation: boolean;
  cluster_id: string;
  account_count: number;
  entity_count: number;
  shared_entities: Array<{
    entity_type: string;
    entity_id: string;
    account_count: number;
  }>;
  evaluation: AbuseRingResponse;
  cluster_data?: AbuseRingRequest | null;
}

export interface EvidenceAdjustmentItem {
  code: string;
  delta: number;
  reason: string;
}

export interface EvidenceAdjustmentsResponse {
  positive_adjustments: EvidenceAdjustmentItem[];
  mitigating_adjustments: EvidenceAdjustmentItem[];
  total_positive_delta: number;
  total_negative_delta: number;
  net_delta: number;
}

export interface AccountAttributionItem {
  account_id: string;
  attribution_role: 'CORE_MEMBER' | 'PERIPHERAL_MEMBER' | 'INCIDENTAL_BYSTANDER' | string;
  linked_ring_accounts_count: number;
  shared_entity_types: string[];
  bipartite_degree: number;
  suspicious_activity_score: number;
  risk_contribution: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  attribution_reasoning: string;
}

export interface ModelMetadataResponse {
  model_version: string;
  feature_schema_version: string;
  calibrated: boolean;
}

export interface AbuseRingResponse {
  cluster_id: string;
  ring_detected: boolean;
  raw_ml_probability: number;
  model_prediction: boolean;
  model_threshold: number;
  evidence_adjustments: EvidenceAdjustmentsResponse;
  final_ring_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  verdict: 'NO_RING' | 'POSSIBLE_RING' | 'LIKELY_RING' | 'HIGH_CONFIDENCE_RING' | string;
  evidence_quality: string;
  confidence: string;
  cluster_size: number;
  ring_factors: string[];
  mitigating_factors: string[];
  evidence_summary: string;
  decision_reasoning: string;
  account_attribution: AccountAttributionItem[];
  recommended_action: string;
  model_metadata: ModelMetadataResponse;
  diagnostics?: string[];
}

// ==========================================
// Razorpay Webhook Ingestion Telemetry
// ==========================================
export interface RazorpayWebhookStatusResponse {
  enabled: boolean;
  environment: string;
  received: number;
  accepted: number;
  ignored: number;
  duplicates: number;
  latest_event_type: string | null;
  latest_event_timestamp: string | null;
  latest_merchant_id: string | null;
  tracked_idempotency_keys: number;
  recent_risk_events_count: number;
}

export interface RazorpayWebhookRiskEventResponse {
  id: string;
  timestamp: string;
  engine: 'FRAUD_SPIKE' | string;
  source: 'LIVE_ASSESSMENT' | string;
  title: string;
  entityId: string;
  entityType: 'ACCOUNT' | 'MERCHANT' | 'CLUSTER' | string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  score: number | string;
  decision: string;
  rawMl: {
    probability?: number;
    score?: number;
    prediction?: number;
  };
  evidence: string[];
  telemetry?: {
    burstRatio?: number | null;
    consecutiveWindows?: number | null;
    observationCount?: number | null;
    currentTxCount?: number | null;
    baselineFraudRate?: number | null;
    currentFraudRate?: number | null;
    fraudRateChange?: number | null;
    evidenceQuality?: string | null;
    guardrailTriggered?: boolean;
    spikeFactors?: string[];
    mitigatingFactors?: string[];
    explanation?: string;
    [key: string]: any;
  };
  policy?: {
    pattern?: string;
    primaryAction?: string;
    triggers?: string[];
    reasoning?: string;
  };
  attribution?: Array<{
    accountId: string;
    role: string;
    reasoning?: string;
  }>;
  returnRisk?: {
    score: number;
    level: string;
    action: string;
    factors: string[];
  };
}

// ==========================================
// Live Abuse Graph (Real-Time Razorpay Webhooks)
// ==========================================
export interface LiveGraphEdgeItem {
  account_id: string;
  entity_type: 'DEVICE' | 'IP' | 'PAYMENT' | 'ADDRESS' | string;
  entity_id: string;
  first_seen_at: string;
  last_seen_at: string;
  interaction_count: number;
  payment_status?: string | null;
  amount?: number | null;
  currency?: string | null;
}

export interface LiveSharedEntityItem {
  entity_type: 'DEVICE' | 'IP' | 'ADDRESS' | string;
  entity_id: string;
  account_count: number;
}

export interface LiveClusterCandidateItem {
  cluster_id: string;
  member_count: number;
  account_ids: string[];
  is_multi_account: boolean;
  shared_entities: LiveSharedEntityItem[];
  total_entities_count: number;
  total_edges_count: number;
}

export interface LiveGraphRecentEventItem {
  event_id: string;
  event_type: string;
  account_id: string;
  payment_id?: string | null;
  status: string;
  association_source: string;
  entities_observed: Array<{ entity_type: string; entity_id: string }>;
  timestamp: string;
}

export interface LiveAbuseGraphResponse {
  status: 'active' | 'idle' | string;
  total_webhook_events: number;
  total_accounts: number;
  total_entities: number;
  total_edges: number;
  candidate_clusters_count: number;
  candidate_clusters: LiveClusterCandidateItem[];
  recent_events: LiveGraphRecentEventItem[];
  last_activity_at?: string | null;
}

export interface LiveGraphAnalysisRequest {
  cluster_id?: string;
  account_id?: string;
}

