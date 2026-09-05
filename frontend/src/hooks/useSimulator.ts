import { useState, useCallback, useRef } from 'react';
import {
  SimulatorScenarioDefinition,
  SimulatorScenarioId,
  SimulatorExecutionStatus,
  SimulatorResultState,
  RuntimeStageState,
  EngineResultState,
} from '../types/simulator';
import {
  SIMULATOR_SCENARIOS,
  getSimulatorScenario,
} from '../services/simulatorScenarios';
import { riskApi, ApiError } from '../services/api';
import { useRiskFeed } from '../context/RiskFeedContext';
import {
  RiskAssessmentResponse,
  FraudSpikeResponse,
  AbuseRingResponse,
} from '../types/api';

/**
 * Creates initial stage states with 'pending' status for a scenario definition.
 */
function createInitialStages(scenario: SimulatorScenarioDefinition): RuntimeStageState[] {
  return scenario.stages.map((stage) => ({
    ...stage,
    status: 'pending',
    latencyMs: undefined,
    error: null,
  }));
}

/**
 * Creates the initial empty result state for a scenario definition.
 */
function createInitialResultState(scenario: SimulatorScenarioDefinition): SimulatorResultState {
  return {
    status: 'IDLE',
    currentStageIndex: 0,
    stages: createInitialStages(scenario),
    accountRiskResult: undefined,
    fraudSpikeResult: undefined,
    abuseRingResult: undefined,
    sequentialFraudResults: undefined,
    totalLatencyMs: undefined,
    overallError: null,
  };
}

/**
 * Normalizes an unknown error into a clean, human-readable string.
 */
function formatErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    return err.message;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return 'An unexpected error occurred during engine execution.';
}

export interface UseSimulatorReturn {
  currentScenario: SimulatorScenarioDefinition;
  availableScenarios: SimulatorScenarioDefinition[];
  selectScenario: (scenarioOrId: SimulatorScenarioId | SimulatorScenarioDefinition) => void;
  status: SimulatorExecutionStatus;
  stages: RuntimeStageState[];
  currentStageIndex: number;
  accountRiskResult?: EngineResultState<RiskAssessmentResponse>;
  fraudSpikeResult?: EngineResultState<FraudSpikeResponse>;
  abuseRingResult?: EngineResultState<AbuseRingResponse>;
  sequentialFraudResults?: FraudSpikeResponse[];
  totalLatencyMs?: number;
  overallError?: string | null;
  isStale: boolean;
  runSimulation: () => Promise<void>;
  resetSimulation: () => void;
}

/**
 * Custom hook orchestrating live Attack Simulator executions across the 3 core risk engines.
 * 
 * Guarantees:
 * - Real API invocation via riskApi (zero fake scores/mocking)
 * - Concurrent execution for independent engines via Promise.allSettled
 * - Sequential execution for P3 Multi-Window Persistence evaluations
 * - Partial failure tolerance (one engine failure does not clear other successful results)
 * - Stale-run protection (superseded asynchronous runs cannot overwrite newer state)
 * - Emits real events to the live Risk Operations session feed
 */
export function useSimulator(
  initialScenarioId: SimulatorScenarioId = 'legitimate_buyer'
): UseSimulatorReturn {
  const initialScenario = getSimulatorScenario(initialScenarioId) || SIMULATOR_SCENARIOS[0];

  const [currentScenario, setCurrentScenario] = useState<SimulatorScenarioDefinition>(initialScenario);
  const [resultState, setResultState] = useState<SimulatorResultState>(() =>
    createInitialResultState(initialScenario)
  );
  const [isStale, setIsStale] = useState<boolean>(false);

  const { addEvent } = useRiskFeed();

  // Monotonically increasing run ID to ignore stale asynchronous executions
  const runIdRef = useRef<number>(0);

  /**
   * Select a new attack template or benchmark scenario.
   * Immediately clears stale execution outputs and resets stage progress.
   */
  const selectScenario = useCallback(
    (scenarioOrId: SimulatorScenarioId | SimulatorScenarioDefinition) => {
      const target =
        typeof scenarioOrId === 'string' ? getSimulatorScenario(scenarioOrId) : scenarioOrId;

      if (!target) return;

      runIdRef.current += 1; // Invalidate any running simulation
      setCurrentScenario(target);
      setResultState(createInitialResultState(target));
      setIsStale(false);
    },
    []
  );

  /**
   * Reset current scenario simulation state to default initial conditions.
   */
  const resetSimulation = useCallback(() => {
    runIdRef.current += 1; // Invalidate any in-flight simulation
    setResultState(createInitialResultState(currentScenario));
    setIsStale(false);
  }, [currentScenario]);

  /**
   * Run the active scenario against live backend APIs.
   */
  const runSimulation = useCallback(async () => {
    const runId = ++runIdRef.current;
    const startTime = performance.now();

    setIsStale(false);

    // Set all initial stages to running / pending
    const runningStages: RuntimeStageState[] = currentScenario.stages.map((stage, idx) => ({
      ...stage,
      status: idx === 0 ? 'running' : 'pending',
      latencyMs: undefined,
      error: null,
    }));

    setResultState({
      status: 'RUNNING',
      currentStageIndex: 0,
      stages: runningStages,
      accountRiskResult: currentScenario.involvedEngines.includes('ACCOUNT_RISK')
        ? { loading: true }
        : undefined,
      fraudSpikeResult: currentScenario.involvedEngines.includes('FRAUD_SPIKE')
        ? { loading: true }
        : undefined,
      abuseRingResult: currentScenario.involvedEngines.includes('ABUSE_RING')
        ? { loading: true }
        : undefined,
      sequentialFraudResults: undefined,
      totalLatencyMs: undefined,
      overallError: null,
    });

    // =========================================================================
    // CASE A: Sequential Execution (P3 Persistent Incident multi-window runs)
    // =========================================================================
    if (currentScenario.id === 'persistent_incident') {
      const sequentialResults: FraudSpikeResponse[] = [];
      const updatedStages = [...runningStages];
      let hasError = false;
      let lastErrorMessage: string | null = null;

      // Unique merchant ID per simulation run to ensure state isolation across demo executions
      const runUniqueMerchantId = `MERCH_SIM_PERSIST_${Date.now().toString().slice(-6)}`;
      const basePayload = currentScenario.fraudSpikePayload || {
        baseline_tx_count: 1200,
        current_tx_count: 70,
        baseline_fraud_rate: 0.01,
        current_fraud_rate: 0.21,
      };

      for (let i = 0; i < currentScenario.stages.length; i++) {
        if (runIdRef.current !== runId) return; // Stale run guard

        // Mark current stage running
        updatedStages[i] = { ...updatedStages[i], status: 'running' };
        setResultState((prev) => ({
          ...prev,
          currentStageIndex: i,
          stages: [...updatedStages],
        }));

        const stageStart = performance.now();
        try {
          // Sequential real API invocation
          const res = await riskApi.detectFraudSpike({
            ...basePayload,
            merchant_id: runUniqueMerchantId,
          });

          if (runIdRef.current !== runId) return;

          const stageLatency = Math.round(performance.now() - stageStart);
          sequentialResults.push(res);
          updatedStages[i] = {
            ...updatedStages[i],
            status: 'completed',
            latencyMs: stageLatency,
            error: null,
          };
        } catch (err: unknown) {
          if (runIdRef.current !== runId) return;

          const stageLatency = Math.round(performance.now() - stageStart);
          const errorMsg = formatErrorMessage(err);
          hasError = true;
          lastErrorMessage = errorMsg;
          updatedStages[i] = {
            ...updatedStages[i],
            status: 'failed',
            latencyMs: stageLatency,
            error: errorMsg,
          };
          break; // Stop sequential chain on error
        }
      }

      if (runIdRef.current !== runId) return;

      const totalTime = Math.round(performance.now() - startTime);
      const finalFraudResult = sequentialResults[sequentialResults.length - 1];

      // Emit to Risk Operations feed
      if (finalFraudResult) {
        addEvent({
          engine: 'FRAUD_SPIKE',
          source: 'SIMULATION',
          title: `Simulated Persistent Incident (${runUniqueMerchantId})`,
          entityId: runUniqueMerchantId,
          entityType: 'MERCHANT',
          severity: finalFraudResult.spike_level,
          score: finalFraudResult.spike_score,
          decision: finalFraudResult.recommended_action,
          rawMl: {
            probability: finalFraudResult.raw_spike_probability !== null ? finalFraudResult.raw_spike_probability : undefined,
            score: finalFraudResult.raw_spike_score !== null ? finalFraudResult.raw_spike_score : undefined,
          },
          evidence: finalFraudResult.spike_factors,
          telemetry: {
            burstRatio: finalFraudResult.five_minute_velocity_ratio !== null ? finalFraudResult.five_minute_velocity_ratio : undefined,
            consecutiveWindows: finalFraudResult.consecutive_anomaly_windows,
          },
        });
      }

      setResultState({
        status: hasError
          ? sequentialResults.length > 0
            ? 'PARTIAL_FAILURE'
            : 'ERROR'
          : 'COMPLETED',
        currentStageIndex: currentScenario.stages.length - 1,
        stages: updatedStages,
        fraudSpikeResult: finalFraudResult
          ? {
              data: finalFraudResult,
              loading: false,
              latencyMs: updatedStages.reduce((acc, s) => acc + (s.latencyMs || 0), 0),
              executedAt: new Date(),
            }
          : {
              loading: false,
              error: lastErrorMessage,
            },
        sequentialFraudResults: sequentialResults,
        totalLatencyMs: totalTime,
        overallError: hasError ? lastErrorMessage : null,
      });

      return;
    }

    // =========================================================================
    // CASE B: Concurrent Execution for Independent Engines
    // =========================================================================
    const finalStages = [...runningStages];
    let accountResult: EngineResultState<RiskAssessmentResponse> | undefined;
    let fraudResult: EngineResultState<FraudSpikeResponse> | undefined;
    let ringResult: EngineResultState<AbuseRingResponse> | undefined;

    const taskPromises: Promise<void>[] = [];

    // 1. Account Risk Execution
    if (currentScenario.involvedEngines.includes('ACCOUNT_RISK') && currentScenario.accountRiskPayload) {
      const stageIdx = currentScenario.stages.findIndex((s) => s.engine === 'ACCOUNT_RISK');
      const payload = currentScenario.accountRiskPayload;

      taskPromises.push(
        (async () => {
          const t0 = performance.now();
          try {
            const data = await riskApi.scoreAccount(payload);
            const latency = Math.round(performance.now() - t0);
            accountResult = { data, loading: false, latencyMs: latency, executedAt: new Date() };
            if (stageIdx >= 0) {
              finalStages[stageIdx] = {
                ...finalStages[stageIdx],
                status: 'completed',
                latencyMs: latency,
              };
            }

            // Emit to feed
            addEvent({
              engine: 'ACCOUNT_RISK',
              source: 'SIMULATION',
              title: `Simulated Account Risk (${data.account_id})`,
              entityId: data.account_id,
              entityType: 'ACCOUNT',
              severity: data.risk_level,
              score: data.risk_score,
              decision: data.recommended_action,
              rawMl: {
                probability: data.risk_probability,
                prediction: data.prediction,
              },
              evidence: data.risk_increasing_signals || data.risk_factors,
              policy: data.decision_policy
                ? {
                    pattern: data.decision_policy.abuse_pattern,
                    primaryAction: data.decision_policy.primary_action,
                    reasoning: data.decision_policy.policy_reasoning,
                  }
                : undefined,
              returnRisk: data.return_risk
                ? {
                    score: data.return_risk.return_risk_score,
                    level: data.return_risk.return_risk_level,
                    action: data.return_risk.recommended_return_action,
                    factors: data.return_risk.return_risk_factors,
                  }
                : undefined,
            });
          } catch (err: unknown) {
            const latency = Math.round(performance.now() - t0);
            const msg = formatErrorMessage(err);
            accountResult = { loading: false, error: msg, latencyMs: latency };
            if (stageIdx >= 0) {
              finalStages[stageIdx] = {
                ...finalStages[stageIdx],
                status: 'failed',
                latencyMs: latency,
                error: msg,
              };
            }
          }
        })()
      );
    }

    // 2. Fraud Spike Execution
    if (currentScenario.involvedEngines.includes('FRAUD_SPIKE') && currentScenario.fraudSpikePayload) {
      const stageIdx = currentScenario.stages.findIndex((s) => s.engine === 'FRAUD_SPIKE');
      const payload = currentScenario.fraudSpikePayload;

      taskPromises.push(
        (async () => {
          const t0 = performance.now();
          try {
            const data = await riskApi.detectFraudSpike(payload);
            const latency = Math.round(performance.now() - t0);
            fraudResult = { data, loading: false, latencyMs: latency, executedAt: new Date() };
            if (stageIdx >= 0) {
              finalStages[stageIdx] = {
                ...finalStages[stageIdx],
                status: 'completed',
                latencyMs: latency,
              };
            }

            // Emit to feed
            addEvent({
              engine: 'FRAUD_SPIKE',
              source: 'SIMULATION',
              title: `Simulated Velocity Radar (${payload.merchant_id || 'MERCHANT'})`,
              entityId: payload.merchant_id || 'MERCH_SIM',
              entityType: 'MERCHANT',
              severity: data.spike_level,
              score: data.spike_score,
              decision: data.recommended_action,
              rawMl: {
                probability: data.raw_spike_probability !== null ? data.raw_spike_probability : undefined,
                score: data.raw_spike_score !== null ? data.raw_spike_score : undefined,
              },
              evidence: data.spike_factors,
              telemetry: {
                burstRatio: data.five_minute_velocity_ratio !== null ? data.five_minute_velocity_ratio : undefined,
                consecutiveWindows: data.consecutive_anomaly_windows,
                fiveMinuteVelocityRatio: data.five_minute_velocity_ratio ?? undefined,
                fiveMinuteObservationCount: data.five_minute_observation_count ?? undefined,
                fiveMinuteCurrentTxCount: data.five_minute_current_tx_count ?? undefined,
                fiveMinuteGuardrailTriggered: data.five_minute_guardrail_triggered ?? undefined,
                fiveMinuteTelemetryAvailable: data.five_minute_telemetry_available ?? undefined,
                persistenceEscalationTriggered: data.persistence_escalation_triggered ?? undefined,
                guardrailTriggered: data.guardrail_triggered ?? undefined,
                fraudRateChange: data.fraud_rate_change ?? undefined,
                baselineFraudRate: data.baseline_fraud_rate ?? undefined,
                currentFraudRate: data.current_fraud_rate ?? undefined,
              },
            });
          } catch (err: unknown) {
            const latency = Math.round(performance.now() - t0);
            const msg = formatErrorMessage(err);
            fraudResult = { loading: false, error: msg, latencyMs: latency };
            if (stageIdx >= 0) {
              finalStages[stageIdx] = {
                ...finalStages[stageIdx],
                status: 'failed',
                latencyMs: latency,
                error: msg,
              };
            }
          }
        })()
      );
    }

    // 3. Abuse Ring Execution
    if (currentScenario.involvedEngines.includes('ABUSE_RING') && currentScenario.abuseRingPayload) {
      const stageIdx = currentScenario.stages.findIndex((s) => s.engine === 'ABUSE_RING');
      const payload = currentScenario.abuseRingPayload;

      taskPromises.push(
        (async () => {
          const t0 = performance.now();
          try {
            const data = await riskApi.detectAbuseRing(payload);
            const latency = Math.round(performance.now() - t0);
            ringResult = { data, loading: false, latencyMs: latency, executedAt: new Date() };
            if (stageIdx >= 0) {
              finalStages[stageIdx] = {
                ...finalStages[stageIdx],
                status: 'completed',
                latencyMs: latency,
              };
            }

            // Emit to feed
            addEvent({
              engine: 'ABUSE_RING',
              source: 'SIMULATION',
              title: `Simulated Abuse Ring (${data.verdict})`,
              entityId: payload.cluster_metadata?.cluster_id || 'CLUSTER_SIM',
              entityType: 'CLUSTER',
              severity: data.risk_level,
              score: Math.round(data.final_ring_score * 100),
              decision: data.recommended_action,
              rawMl: {
                probability: data.raw_ml_probability,
                score: Math.round(data.raw_ml_probability * 100),
              },
              evidence: data.ring_factors,
              attribution: data.account_attribution?.map((a) => ({
                accountId: a.account_id,
                role: a.attribution_role,
                reasoning: a.attribution_reasoning,
              })),
            });
          } catch (err: unknown) {
            const latency = Math.round(performance.now() - t0);
            const msg = formatErrorMessage(err);
            ringResult = { loading: false, error: msg, latencyMs: latency };
            if (stageIdx >= 0) {
              finalStages[stageIdx] = {
                ...finalStages[stageIdx],
                status: 'failed',
                latencyMs: latency,
                error: msg,
              };
            }
          }
        })()
      );
    }

    // Await all tasks concurrently with Promise.allSettled protection
    await Promise.allSettled(taskPromises);

    if (runIdRef.current !== runId) return; // Stale run guard

    const totalTime = Math.round(performance.now() - startTime);

    // Compute aggregate success / failure status
    const engineResults = [accountResult, fraudResult, ringResult].filter(Boolean);
    const successCount = engineResults.filter((r) => r?.data !== undefined).length;
    const errorCount = engineResults.filter((r) => r?.error !== undefined && r?.error !== null).length;

    let overallStatus: SimulatorExecutionStatus = 'COMPLETED';
    let aggregateError: string | null = null;

    if (errorCount > 0) {
      if (successCount > 0) {
        overallStatus = 'PARTIAL_FAILURE';
        aggregateError = 'One or more defense engines encountered an error.';
      } else {
        overallStatus = 'ERROR';
        aggregateError = 'All involved defense engines failed to execute.';
      }
    }

    setResultState({
      status: overallStatus,
      currentStageIndex: currentScenario.stages.length - 1,
      stages: finalStages,
      accountRiskResult: accountResult,
      fraudSpikeResult: fraudResult,
      abuseRingResult: ringResult,
      totalLatencyMs: totalTime,
      overallError: aggregateError,
    });
  }, [currentScenario, addEvent]);

  return {
    currentScenario,
    availableScenarios: SIMULATOR_SCENARIOS,
    selectScenario,
    status: resultState.status,
    stages: resultState.stages,
    currentStageIndex: resultState.currentStageIndex,
    accountRiskResult: resultState.accountRiskResult,
    fraudSpikeResult: resultState.fraudSpikeResult,
    abuseRingResult: resultState.abuseRingResult,
    sequentialFraudResults: resultState.sequentialFraudResults,
    totalLatencyMs: resultState.totalLatencyMs,
    overallError: resultState.overallError,
    isStale,
    runSimulation,
    resetSimulation,
  };
}
