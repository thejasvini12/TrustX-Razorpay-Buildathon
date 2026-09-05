export type RiskEngineType = 'ACCOUNT_RISK' | 'RETURN_RISK' | 'FRAUD_SPIKE' | 'ABUSE_RING';

export type EventSourceType = 'LIVE_ASSESSMENT' | 'SIMULATION' | 'MANUAL_INVESTIGATION';

export type EventSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type CaseStatus = 'OPEN' | 'INVESTIGATING' | 'RESOLVED';

export interface RiskEvent {
  id: string;
  timestamp: Date;
  status?: CaseStatus;
  operatorAction?: string;
  operatorNotes?: string;
  updatedAt?: string;
  engine: RiskEngineType;
  source: EventSourceType;
  title: string;
  entityId: string;
  entityType: 'ACCOUNT' | 'MERCHANT' | 'CLUSTER';
  severity: EventSeverity;
  score: number | string;
  decision: string;
  rawMl: {
    probability?: number;
    score?: number;
    prediction?: number;
  };
  evidence: string[];
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
    environment?: string;
    eventType?: string;
    paymentId?: string;
    amount?: number;
    currency?: string;
    [key: string]: any;
  };
}
