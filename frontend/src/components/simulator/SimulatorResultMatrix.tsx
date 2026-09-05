import React from 'react';
import {
  SimulatorScenarioDefinition,
  SimulatorExecutionStatus,
  EngineResultState,
} from '../../types/simulator';
import {
  RiskAssessmentResponse,
  FraudSpikeResponse,
  AbuseRingResponse,
} from '../../types/api';
import {
  Activity,
  Layers,
  UserCheck,
} from 'lucide-react';

interface SimulatorResultMatrixProps {
  scenario: SimulatorScenarioDefinition;
  status: SimulatorExecutionStatus;
  accountRiskResult?: EngineResultState<RiskAssessmentResponse>;
  fraudSpikeResult?: EngineResultState<FraudSpikeResponse>;
  abuseRingResult?: EngineResultState<AbuseRingResponse>;
  sequentialFraudResults?: FraudSpikeResponse[];
}

export const SimulatorResultMatrix: React.FC<SimulatorResultMatrixProps> = ({
  scenario,
  status,
  accountRiskResult,
  fraudSpikeResult,
  abuseRingResult,
  sequentialFraudResults,
}) => {
  const isIdle = status === 'IDLE';

  if (isIdle) {
    return (
      <div className="card" style={{ padding: '36px 20px', textAlign: 'center', backgroundColor: 'var(--bg-app)', border: '1px dashed var(--border-muted)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
          <div style={{ padding: '10px', borderRadius: '50%', backgroundColor: 'rgba(56, 189, 248, 0.08)', color: 'var(--accent-cyan)' }}>
            <Activity size={24} />
          </div>
          <h3 style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text-primary)' }}>
            Multi-Engine Result Matrix Standby
          </h3>
          <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', maxWidth: '520px', lineHeight: '1.4' }}>
            Click <strong>Run Simulation</strong> above to execute the real FastAPI defense pipelines and inspect independent engine outputs side-by-side.
          </p>
        </div>
      </div>
    );
  }

  const involvesAccount = scenario.involvedEngines.includes('ACCOUNT_RISK');
  const involvesSpike = scenario.involvedEngines.includes('FRAUD_SPIKE');
  const involvesRing = scenario.involvedEngines.includes('ABUSE_RING');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
            Multi-Engine Live Output Matrix
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Independent, unweighted evaluations returned by each active defense pipeline.
          </p>
        </div>
        <span className="badge badge-cyan" style={{ fontSize: '11px' }}>
          Authoritative Backend Telemetry
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: '16px',
          alignItems: 'stretch',
        }}
      >
        {/* ========================================================= */}
        {/* 1. ACCOUNT RISK ENGINE CARD                                */}
        {/* ========================================================= */}
        <div
          className="card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            border: involvesAccount ? '1px solid rgba(56, 189, 248, 0.3)' : '1px dashed var(--border-subtle)',
            backgroundColor: involvesAccount ? 'var(--bg-card)' : 'rgba(10, 14, 26, 0.4)',
            opacity: involvesAccount ? 1 : 0.65,
          }}
        >
          {/* Card Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ padding: '6px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(56, 189, 248, 0.12)', color: 'var(--accent-cyan)' }}>
                <UserCheck size={16} />
              </div>
              <div>
                <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--text-primary)' }}>Account Risk Engine</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>POST /risk/score</div>
              </div>
            </div>

            {involvesAccount ? (
              accountRiskResult?.loading ? (
                <span className="badge badge-cyan">In Flight...</span>
              ) : accountRiskResult?.data ? (
                <span className="badge badge-green">200 OK ({accountRiskResult.latencyMs}ms)</span>
              ) : accountRiskResult?.error ? (
                <span className="badge badge-rose">Failed</span>
              ) : null
            ) : (
              <span className="badge badge-neutral">Not Involved</span>
            )}
          </div>

          {/* Card Body */}
          {!involvesAccount ? (
            <div style={{ padding: '24px 10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              Account risk scoring was not designated for this scenario.
            </div>
          ) : accountRiskResult?.loading ? (
            <div style={{ padding: '28px 10px', textAlign: 'center', color: 'var(--accent-cyan)', fontSize: '12px' }}>
              Executing Random Forest pipeline & decision policies...
            </div>
          ) : accountRiskResult?.error ? (
            <div style={{ padding: '12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.25)', color: 'var(--risk-high)', fontSize: '12px' }}>
              {accountRiskResult.error}
            </div>
          ) : accountRiskResult?.data ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Score & Tier Header */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', backgroundColor: 'var(--bg-app)', padding: '10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Operational Risk Score</div>
                  <div style={{ fontSize: '20px', fontWeight: '800', color: accountRiskResult.data.risk_level === 'LOW' ? 'var(--risk-low)' : accountRiskResult.data.risk_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-high)', fontFamily: 'JetBrains Mono, monospace' }}>
                    {accountRiskResult.data.risk_score} <span style={{ fontSize: '12px', fontWeight: '500', color: 'var(--text-muted)' }}>/ 100</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Operational Tier</div>
                  <div style={{ fontSize: '13px', fontWeight: '700', color: accountRiskResult.data.risk_level === 'LOW' ? 'var(--risk-low)' : accountRiskResult.data.risk_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-high)', marginTop: '4px' }}>
                    {accountRiskResult.data.risk_level} ({accountRiskResult.data.risk_tier})
                  </div>
                </div>
              </div>

              {/* Raw ML vs Policy Distinction */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Raw ML Probability:</span>
                  <strong style={{ color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                    {(accountRiskResult.data.risk_probability * 100).toFixed(1)}% (Class {accountRiskResult.data.prediction})
                  </strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Recommended Action:</span>
                  <strong style={{ color: accountRiskResult.data.recommended_action === 'ALLOW' ? 'var(--risk-low)' : accountRiskResult.data.recommended_action === 'MANUAL_REVIEW' ? 'var(--risk-medium)' : 'var(--risk-high)' }}>
                    {accountRiskResult.data.recommended_action}
                  </strong>
                </div>

                {accountRiskResult.data.decision_policy && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Detected Pattern:</span>
                    <span style={{ color: 'var(--accent-cyan)', fontWeight: '600' }}>
                      {accountRiskResult.data.decision_policy.abuse_pattern}
                    </span>
                  </div>
                )}
              </div>

              {/* Nested Return Risk Sub-Engine */}
              {accountRiskResult.data.return_risk && (
                <div style={{ padding: '10px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--accent-cyan)', textTransform: 'uppercase' }}>
                      Return Risk Sub-Engine
                    </span>
                    <span style={{ fontSize: '11px', fontWeight: '700', color: accountRiskResult.data.return_risk.return_risk_level === 'LOW' ? 'var(--risk-low)' : accountRiskResult.data.return_risk.return_risk_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-high)' }}>
                      Score {accountRiskResult.data.return_risk.return_risk_score}/100 ({accountRiskResult.data.return_risk.return_risk_level})
                    </span>
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                    Action: <strong style={{ color: 'var(--text-primary)' }}>{accountRiskResult.data.return_risk.recommended_return_action}</strong>
                  </div>
                  {accountRiskResult.data.return_risk.return_risk_factors.length > 0 && (
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Trigger: {accountRiskResult.data.return_risk.return_risk_factors[0]}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* ========================================================= */}
        {/* 2. FRAUD SPIKE RADAR CARD                                  */}
        {/* ========================================================= */}
        <div
          className="card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            border: involvesSpike ? '1px solid rgba(245, 158, 11, 0.3)' : '1px dashed var(--border-subtle)',
            backgroundColor: involvesSpike ? 'var(--bg-card)' : 'rgba(10, 14, 26, 0.4)',
            opacity: involvesSpike ? 1 : 0.65,
          }}
        >
          {/* Card Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ padding: '6px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(245, 158, 11, 0.12)', color: 'var(--risk-medium)' }}>
                <Activity size={16} />
              </div>
              <div>
                <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--text-primary)' }}>Fraud Spike Radar</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>POST /risk/fraud-spike</div>
              </div>
            </div>

            {involvesSpike ? (
              fraudSpikeResult?.loading ? (
                <span className="badge badge-amber">In Flight...</span>
              ) : fraudSpikeResult?.data ? (
                <span className="badge badge-green">200 OK ({fraudSpikeResult.latencyMs}ms)</span>
              ) : fraudSpikeResult?.error ? (
                <span className="badge badge-rose">Failed</span>
              ) : null
            ) : (
              <span className="badge badge-neutral">Not Involved</span>
            )}
          </div>

          {/* Card Body */}
          {!involvesSpike ? (
            <div style={{ padding: '24px 10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              Temporal velocity radar was not designated for this scenario.
            </div>
          ) : fraudSpikeResult?.loading ? (
            <div style={{ padding: '28px 10px', textAlign: 'center', color: 'var(--risk-medium)', fontSize: '12px' }}>
              Evaluating velocity anomalies & micro-burst telemetry...
            </div>
          ) : fraudSpikeResult?.error ? (
            <div style={{ padding: '12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.25)', color: 'var(--risk-high)', fontSize: '12px' }}>
              {fraudSpikeResult.error}
            </div>
          ) : fraudSpikeResult?.data ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Sequential Multi-Window Result Grid if Persistent Incident */}
              {sequentialFraudResults && sequentialFraudResults.length > 1 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--risk-medium)', textTransform: 'uppercase' }}>
                    Sequential Multi-Window Progression ({sequentialFraudResults.length} Windows)
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: `repeat(${sequentialFraudResults.length}, 1fr)`, gap: '6px' }}>
                    {sequentialFraudResults.map((winRes, wIdx) => (
                      <div
                        key={wIdx}
                        style={{
                          padding: '8px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'var(--bg-app)',
                          border: wIdx === sequentialFraudResults.length - 1 ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '2px',
                        }}
                      >
                        <span style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)' }}>W{wIdx + 1} Result</span>
                        <span style={{ fontSize: '13px', fontWeight: '700', color: winRes.spike_level === 'HIGH' ? 'var(--risk-high)' : 'var(--risk-medium)', fontFamily: 'JetBrains Mono, monospace' }}>
                          Score {winRes.spike_score}
                        </span>
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                          {winRes.spike_level} ({winRes.consecutive_anomaly_windows} win)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                /* Standard Single Evaluation Score & Tier Header */
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', backgroundColor: 'var(--bg-app)', padding: '10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Operational Spike Score</div>
                    <div style={{ fontSize: '20px', fontWeight: '800', color: fraudSpikeResult.data.spike_level === 'LOW' ? 'var(--risk-low)' : fraudSpikeResult.data.spike_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-high)', fontFamily: 'JetBrains Mono, monospace' }}>
                      {fraudSpikeResult.data.spike_score} <span style={{ fontSize: '12px', fontWeight: '500', color: 'var(--text-muted)' }}>/ 100</span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Operational Tier</div>
                    <div style={{ fontSize: '13px', fontWeight: '700', color: fraudSpikeResult.data.spike_level === 'LOW' ? 'var(--risk-low)' : fraudSpikeResult.data.spike_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-high)', marginTop: '4px' }}>
                      {fraudSpikeResult.data.spike_level}
                    </div>
                  </div>
                </div>
              )}

              {/* Raw ML vs Guardrail Details */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Raw Model Output:</span>
                  <strong style={{ color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                    Score {fraudSpikeResult.data.raw_spike_score} ({fraudSpikeResult.data.raw_spike_probability != null ? (fraudSpikeResult.data.raw_spike_probability * 100).toFixed(1) + '%' : 'N/A'})
                  </strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Fraud Rate Shift:</span>
                  <span style={{ color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                    {(fraudSpikeResult.data.baseline_fraud_rate * 100).toFixed(1)}% → {(fraudSpikeResult.data.current_fraud_rate * 100).toFixed(1)}% (Δ{(fraudSpikeResult.data.fraud_rate_change * 100).toFixed(1)}%)
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Action Directive:</span>
                  <strong style={{ color: fraudSpikeResult.data.recommended_action === 'ALLOW_STANDARD_OPERATIONS' ? 'var(--risk-low)' : fraudSpikeResult.data.recommended_action === 'FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR' ? 'var(--risk-medium)' : 'var(--risk-high)' }}>
                    {fraudSpikeResult.data.recommended_action}
                  </strong>
                </div>

                {/* Guardrail Chips */}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
                  {fraudSpikeResult.data.guardrail_triggered && (
                    <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(245, 158, 11, 0.15)', color: 'var(--risk-medium)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                      P1 Delta Floor Active
                    </span>
                  )}
                  {fraudSpikeResult.data.five_minute_guardrail_triggered && (
                    <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(245, 158, 11, 0.15)', color: 'var(--risk-medium)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                      P5 5-Min Burst Active
                    </span>
                  )}
                  {fraudSpikeResult.data.persistence_escalation_triggered && (
                    <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(244, 63, 94, 0.15)', color: 'var(--risk-high)', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
                      P3 Persistence Escalated
                    </span>
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* ========================================================= */}
        {/* 3. ABUSE RING SENTINEL CARD                                */}
        {/* ========================================================= */}
        <div
          className="card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            border: involvesRing ? '1px solid rgba(168, 85, 247, 0.35)' : '1px dashed var(--border-subtle)',
            backgroundColor: involvesRing ? 'var(--bg-card)' : 'rgba(10, 14, 26, 0.4)',
            opacity: involvesRing ? 1 : 0.65,
          }}
        >
          {/* Card Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ padding: '6px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(168, 85, 247, 0.14)', color: 'var(--risk-critical)' }}>
                <Layers size={16} />
              </div>
              <div>
                <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--text-primary)' }}>Abuse Ring Sentinel</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>POST /risk/abuse-ring</div>
              </div>
            </div>

            {involvesRing ? (
              abuseRingResult?.loading ? (
                <span className="badge badge-purple">In Flight...</span>
              ) : abuseRingResult?.data ? (
                <span className="badge badge-green">200 OK ({abuseRingResult.latencyMs}ms)</span>
              ) : abuseRingResult?.error ? (
                <span className="badge badge-rose">Failed</span>
              ) : null
            ) : (
              <span className="badge badge-neutral">Not Involved</span>
            )}
          </div>

          {/* Card Body */}
          {!involvesRing ? (
            <div style={{ padding: '24px 10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              Bipartite graph analysis was not designated for this scenario.
            </div>
          ) : abuseRingResult?.loading ? (
            <div style={{ padding: '28px 10px', textAlign: 'center', color: 'var(--risk-critical)', fontSize: '12px' }}>
              Extracting graph topology & evaluating 15 cluster features...
            </div>
          ) : abuseRingResult?.error ? (
            <div style={{ padding: '12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.25)', color: 'var(--risk-high)', fontSize: '12px' }}>
              {abuseRingResult.error}
            </div>
          ) : abuseRingResult?.data ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Score & Verdict Header */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', backgroundColor: 'var(--bg-app)', padding: '10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Final Ring Score</div>
                  <div style={{ fontSize: '20px', fontWeight: '800', color: abuseRingResult.data.risk_level === 'LOW' ? 'var(--risk-low)' : abuseRingResult.data.risk_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-critical)', fontFamily: 'JetBrains Mono, monospace' }}>
                    {abuseRingResult.data.final_ring_score.toFixed(4)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Syndicate Verdict</div>
                  <div style={{ fontSize: '13px', fontWeight: '700', color: abuseRingResult.data.risk_level === 'LOW' ? 'var(--risk-low)' : abuseRingResult.data.risk_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-critical)', marginTop: '4px' }}>
                    {abuseRingResult.data.verdict}
                  </div>
                </div>
              </div>

              {/* Raw ML vs Evidence Adjustments */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Raw ML Probability:</span>
                  <span style={{ color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                    {abuseRingResult.data.raw_ml_probability.toFixed(4)} (Threshold: {abuseRingResult.data.model_threshold})
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Evidence Net Delta:</span>
                  <strong style={{ color: abuseRingResult.data.evidence_adjustments.net_delta > 0 ? 'var(--risk-high)' : 'var(--risk-low)', fontFamily: 'JetBrains Mono, monospace' }}>
                    {abuseRingResult.data.evidence_adjustments.net_delta >= 0 ? `+${abuseRingResult.data.evidence_adjustments.net_delta.toFixed(2)}` : abuseRingResult.data.evidence_adjustments.net_delta.toFixed(2)}
                  </strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Enforcement Action:</span>
                  <strong style={{ color: abuseRingResult.data.recommended_action === 'NO_ACTION' ? 'var(--risk-low)' : abuseRingResult.data.recommended_action === 'BLOCK_ENTIRE_RING' ? 'var(--risk-critical)' : 'var(--risk-medium)' }}>
                    {abuseRingResult.data.recommended_action}
                  </strong>
                </div>
              </div>

              {/* Attribution Summary */}
              {abuseRingResult.data.account_attribution && abuseRingResult.data.account_attribution.length > 0 && (
                <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Account Attribution ({abuseRingResult.data.account_attribution.length} Nodes)
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '100px', overflowY: 'auto' }}>
                    {abuseRingResult.data.account_attribution.map((node) => (
                      <div key={node.account_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
                        <span style={{ color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                          {node.account_id}
                        </span>
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: '600',
                            padding: '1px 6px',
                            borderRadius: 'var(--radius-sm)',
                            backgroundColor: node.attribution_role === 'CORE_MEMBER' ? 'rgba(168, 85, 247, 0.15)' : node.attribution_role === 'INCIDENTAL_BYSTANDER' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                            color: node.attribution_role === 'CORE_MEMBER' ? 'var(--risk-critical)' : node.attribution_role === 'INCIDENTAL_BYSTANDER' ? 'var(--risk-low)' : 'var(--risk-medium)',
                          }}
                        >
                          {node.attribution_role}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
