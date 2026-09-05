import {
  AccountRiskRequest,
  RiskAssessmentResponse,
  FraudSpikeRequest,
  FraudSpikeResponse,
  AbuseRingRequest,
  AbuseRingResponse,
} from './api';

/**
 * Supported risk engine identifiers for simulator orchestration.
 * Note: Return Risk is evaluated inside ACCOUNT_RISK via /risk/score.
 */
export type SimulatorEngine = 'ACCOUNT_RISK' | 'FRAUD_SPIKE' | 'ABUSE_RING';

/**
 * Strongly typed benchmark scenario identifiers.
 */
export type SimulatorScenarioId =
  | 'legitimate_buyer'
  | 'serial_wardrober'
  | 'promo_farm'
  | 'card_testing'
  | 'persistent_incident'
  | 'syndicate_mule'
  | 'shared_family_bystander';

/**
 * Categorization of attacks and traffic archetypes.
 */
export type AttackCategory =
  | 'BENIGN_TRAFFIC'
  | 'RETURN_ABUSE'
  | 'PROMO_ABUSE'
  | 'CARD_TESTING'
  | 'PERSISTENT_ATTACK'
  | 'COORDINATED_SYNDICATE'
  | 'BYSTANDER_PROTECTION';

/**
 * Threat severity ranking for scenario presentation.
 */
export type ScenarioSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

/**
 * Discrete stage definition within a scenario simulation workflow.
 */
export interface SimulatorStage {
  stageNumber: number;
  engine: SimulatorEngine;
  title: string;
  description: string;
  isSequential?: boolean;
  iterationCount?: number;
}

/**
 * Stage execution status.
 */
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed';

/**
 * Runtime execution state for a stage in the execution timeline.
 */
export interface RuntimeStageState extends SimulatorStage {
  status: StageStatus;
  latencyMs?: number;
  error?: string | null;
}

/**
 * Non-authoritative reference output used strictly for documentation and UI briefings.
 * NOTE: Runtime assessment outputs are always dynamically queried from live APIs.
 */
export interface NonAuthoritativeReferenceOutput {
  expectedAccountAction?: string;
  expectedReturnAction?: string;
  expectedSpikeAction?: string;
  expectedRingAction?: string;
  referenceInsight: string;
}

/**
 * Complete specification for an Attack Simulator scenario template.
 */
export interface SimulatorScenarioDefinition {
  id: SimulatorScenarioId;
  name: string;
  shortDescription: string;
  attackCategory: AttackCategory;
  severity: ScenarioSeverity;
  involvedEngines: SimulatorEngine[];
  stages: SimulatorStage[];
  accountRiskPayload?: AccountRiskRequest;
  fraudSpikePayload?: FraudSpikeRequest;
  abuseRingPayload?: AbuseRingRequest;
  demoObjective: string;
  operationalStory: string;
  keyDifferentiatorNote?: string;
  referenceOutput?: NonAuthoritativeReferenceOutput;
}

/**
 * Lifecycle states of the simulator orchestrator.
 */
export type SimulatorExecutionStatus =
  | 'IDLE'
  | 'RUNNING'
  | 'COMPLETED'
  | 'PARTIAL_FAILURE'
  | 'ERROR';

/**
 * Individual engine execution state and latency tracking.
 */
export interface EngineResultState<T> {
  data?: T;
  loading: boolean;
  error?: string | null;
  latencyMs?: number;
  executedAt?: Date;
}

/**
 * Aggregate runtime state across all involved engines in a simulation run.
 */
export interface SimulatorResultState {
  status: SimulatorExecutionStatus;
  currentStageIndex: number;
  stages: RuntimeStageState[];
  accountRiskResult?: EngineResultState<RiskAssessmentResponse>;
  fraudSpikeResult?: EngineResultState<FraudSpikeResponse>;
  abuseRingResult?: EngineResultState<AbuseRingResponse>;
  sequentialFraudResults?: FraudSpikeResponse[];
  totalLatencyMs?: number;
  overallError?: string | null;
}
