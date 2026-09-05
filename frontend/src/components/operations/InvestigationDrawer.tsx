import React from 'react';
import { RiskEvent, CaseStatus } from '../../types/riskFeed';
import { useRiskFeed } from '../../context/RiskFeedContext';
import {
  X,
  CheckCircle2,
  Play,
  RotateCcw,
  Shield,
  Activity,
} from 'lucide-react';

interface InvestigationDrawerProps {
  event: RiskEvent | null;
  onClose: () => void;
}

function getFraudSpikeMetrics(event: RiskEvent) {
  let observationCount = event.telemetry?.observationCount ?? null;
  let evidenceQuality = event.telemetry?.evidenceQuality ?? null;
  let paymentDetails: string | null = null;

  if (Array.isArray(event.evidence)) {
    for (const line of event.evidence) {
      if (observationCount === null) {
        const match = line.match(/observation windows active:\s*(\d+)/i);
        if (match) observationCount = parseInt(match[1], 10);
      }
      if (!evidenceQuality) {
        const match = line.match(/evidence quality:\s*([A-Za-z_]+)/i);
        if (match) evidenceQuality = match[1];
      }
      if (line.toLowerCase().includes('ingested') && !paymentDetails) {
        paymentDetails = line;
      }
    }
  }

  const burstRatio = event.telemetry?.burstRatio ?? null;
  const guardrailTriggered = Boolean(
    event.telemetry?.guardrailTriggered || (burstRatio !== null && burstRatio >= 3.0)
  );
  const consecutiveWindows = event.telemetry?.consecutiveWindows ?? 0;
  const baselineFraudRate = event.telemetry?.baselineFraudRate ?? null;
  const currentFraudRate = event.telemetry?.currentFraudRate ?? null;
  const fraudRateChange = event.telemetry?.fraudRateChange ?? null;

  return {
    observationCount,
    evidenceQuality: evidenceQuality || 'SUFFICIENT',
    burstRatio,
    guardrailTriggered,
    consecutiveWindows,
    baselineFraudRate,
    currentFraudRate,
    fraudRateChange,
    paymentDetails,
  };
}

export const InvestigationDrawer: React.FC<InvestigationDrawerProps> = ({ event, onClose }) => {
  const { updateEventStatus } = useRiskFeed();

  if (!event) return null;

  const currentStatus: CaseStatus = event.status || 'OPEN';
  const metrics = getFraudSpikeMetrics(event);

  const decisionColor =
    event.decision.includes('BLOCK') || event.decision.includes('STRICT') || event.decision.includes('CHALLENGE')
      ? 'var(--risk-high)'
      : event.decision.includes('REVIEW') || event.decision.includes('FLAG') || event.decision.includes('MONITOR')
      ? 'var(--risk-medium)'
      : 'var(--risk-low)';

  const decisionBg =
    event.decision.includes('BLOCK') || event.decision.includes('STRICT') || event.decision.includes('CHALLENGE')
      ? 'var(--risk-high-bg)'
      : event.decision.includes('REVIEW') || event.decision.includes('FLAG') || event.decision.includes('MONITOR')
      ? 'var(--risk-medium-bg)'
      : 'var(--risk-low-bg)';

  const decisionBorder =
    event.decision.includes('BLOCK') || event.decision.includes('STRICT') || event.decision.includes('CHALLENGE')
      ? 'var(--risk-high-border)'
      : event.decision.includes('REVIEW') || event.decision.includes('FLAG') || event.decision.includes('MONITOR')
      ? 'var(--risk-medium-border)'
      : 'var(--risk-low-border)';

  // Rationale resolution
  const decisionRationale =
    event.policy?.reasoning ||
    event.telemetry?.explanation ||
    (event.severity === 'HIGH' || event.severity === 'CRITICAL'
      ? 'Behavioral signals, transaction velocity, or graph sharing topology exceeded critical risk thresholds requiring defense controls.'
      : event.severity === 'MEDIUM'
      ? 'Elevated anomaly metrics detected. Recommended for manual review or step-up verification.'
      : 'Transaction features and entity graph connectivity remain within standard baseline parameters.');

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '660px',
          height: '100%',
          backgroundColor: 'var(--bg-card)',
          borderLeft: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-lg)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* TIER 1: Drawer Top Header (Risk Level & Case Status) */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            backgroundColor: 'var(--bg-elevated)',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: 'var(--accent-cyan)',
                }}
              >
                1. Case Investigation
              </span>

              {/* Severity Badge */}
              <span
                className={`badge ${
                  event.severity === 'CRITICAL'
                    ? 'badge-purple'
                    : event.severity === 'HIGH'
                    ? 'badge-rose'
                    : event.severity === 'MEDIUM'
                    ? 'badge-amber'
                    : 'badge-green'
                }`}
              >
                {event.severity} RISK
              </span>

              {/* Case Lifecycle Status */}
              <span
                style={{
                  fontSize: '10.5px',
                  fontWeight: '700',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-pill)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  backgroundColor:
                    currentStatus === 'RESOLVED'
                      ? 'rgba(16, 185, 129, 0.14)'
                      : currentStatus === 'INVESTIGATING'
                      ? 'rgba(168, 85, 247, 0.14)'
                      : 'rgba(56, 189, 248, 0.14)',
                  color:
                    currentStatus === 'RESOLVED'
                      ? 'var(--risk-low)'
                      : currentStatus === 'INVESTIGATING'
                      ? 'var(--risk-critical)'
                      : 'var(--accent-cyan)',
                  border:
                    currentStatus === 'RESOLVED'
                      ? '1px solid rgba(16, 185, 129, 0.3)'
                      : currentStatus === 'INVESTIGATING'
                      ? '1px solid rgba(168, 85, 247, 0.3)'
                      : '1px solid rgba(56, 189, 248, 0.3)',
                }}
              >
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor:
                      currentStatus === 'RESOLVED'
                        ? 'var(--risk-low)'
                        : currentStatus === 'INVESTIGATING'
                        ? 'var(--risk-critical)'
                        : 'var(--accent-cyan)',
                  }}
                />
                STATUS: {currentStatus}
              </span>

              <span className="badge badge-cyan" style={{ fontSize: '10px' }}>
                {event.source}
              </span>
            </div>

            <h2 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)' }}>
              {event.title}
            </h2>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono, monospace' }}>
              Entity: <strong style={{ color: 'var(--text-primary)' }}>{event.entityId}</strong> • Ref: {event.id}
            </span>
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            style={{ padding: '6px', borderRadius: '50%' }}
            title="Close investigation panel"
          >
            <X size={16} />
          </button>
        </div>

        {/* Operator Case Actions Bar */}
        <div
          style={{
            padding: '12px 24px',
            backgroundColor: 'rgba(0, 0, 0, 0.25)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '10px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <Activity size={13} />
            <span>Workflow Controls:</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {currentStatus === 'OPEN' && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => updateEventStatus(event.id, 'INVESTIGATING', 'Case Investigation Started')}
                style={{ padding: '4px 10px', fontSize: '11.5px', display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--risk-critical)' }}
              >
                <Play size={11} />
                <span>Mark Investigating</span>
              </button>
            )}

            {currentStatus !== 'RESOLVED' && (
              <>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => updateEventStatus(event.id, 'RESOLVED', 'Simulated Step-Up Challenge Passed')}
                  style={{ padding: '4px 10px', fontSize: '11.5px', display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--risk-low)' }}
                >
                  <CheckCircle2 size={12} />
                  <span>Resolve (Mitigated)</span>
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => updateEventStatus(event.id, 'RESOLVED', 'False Positive Dismissed')}
                  style={{ padding: '4px 10px', fontSize: '11.5px', display: 'flex', alignItems: 'center', gap: '5px' }}
                >
                  <span>Dismiss (False Positive)</span>
                </button>
              </>
            )}

            {currentStatus === 'RESOLVED' && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => updateEventStatus(event.id, 'OPEN', 'Case Reopened by Analyst')}
                style={{ padding: '4px 10px', fontSize: '11.5px', display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--text-muted)' }}
              >
                <RotateCcw size={11} />
                <span>Reopen Case</span>
              </button>
            )}
          </div>
        </div>

        {/* Operator Decision Notice if set */}
        {event.operatorAction && (
          <div
            style={{
              padding: '10px 24px',
              backgroundColor: 'rgba(99, 102, 241, 0.08)',
              borderBottom: '1px solid rgba(99, 102, 241, 0.25)',
              color: 'var(--accent-cyan)',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Shield size={14} />
            <span>
              <strong>Operator Decision — Process Local:</strong> {event.operatorAction}
              {event.updatedAt && (
                <span style={{ color: 'var(--text-muted)', marginLeft: '6px' }}>
                  ({new Date(event.updatedAt).toLocaleTimeString()})
                </span>
              )}
            </span>
          </div>
        )}

        {/* Drawer Body Content: Strict 8-Tier Hierarchy */}
        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* TIER 2: Operational Score & Evaluation Confidence */}
          <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              2. Operational Risk Score & Confidence
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
              <div style={{ padding: '10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>Calibrated Risk Score</span>
                <div className="font-mono" style={{ fontSize: '20px', fontWeight: '800', color: 'var(--accent-cyan)', marginTop: '2px' }}>
                  {event.score} <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>/ 100</span>
                </div>
              </div>

              <div style={{ padding: '10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>Risk Tier</span>
                <div className="font-mono" style={{ fontSize: '16px', fontWeight: '800', color: decisionColor, marginTop: '4px' }}>
                  {event.severity} TIER
                </div>
              </div>

              <div style={{ padding: '10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>Evidence Quality</span>
                <div className="font-mono" style={{ fontSize: '14px', fontWeight: '700', color: metrics.evidenceQuality === 'SUFFICIENT' ? 'var(--risk-low)' : 'var(--risk-medium)', marginTop: '4px' }}>
                  {metrics.evidenceQuality}
                </div>
              </div>
            </div>
          </div>

          {/* TIER 3: System Recommended Action Directive */}
          <div
            className="card"
            style={{
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              backgroundColor: decisionBg,
              border: `1px solid ${decisionBorder}`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '11px', fontWeight: '700', color: decisionColor, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                3. System Recommended Action
              </div>
              <span className="badge" style={{ backgroundColor: 'rgba(0,0,0,0.3)', color: decisionColor, fontSize: '10px' }}>
                Automated Policy Directive
              </span>
            </div>

            <div style={{ fontSize: '17px', fontWeight: '800', color: 'var(--text-primary)' }}>
              {event.decision}
            </div>

            <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Specialized automated defense directive prescribed downstream of model inference. (Does not simulate execution without operator approval).
            </p>

            {/* Nested Return Risk Directive if present */}
            {event.returnRisk && (
              <div
                style={{
                  marginTop: '8px',
                  padding: '8px 10px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(0, 0, 0, 0.25)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '11.5px',
                }}
              >
                <strong style={{ color: 'var(--risk-low)' }}>Return Desk Policy: </strong>
                <span>{event.returnRisk.action} (Score: {event.returnRisk.score}/100)</span>
              </div>
            )}
          </div>

          {/* TIER 4: Why The System Reached The Decision (Decision Rationale) */}
          <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              4. Why The System Reached This Decision
            </div>
            <div
              style={{
                padding: '12px 14px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-app)',
                border: '1px solid var(--border-subtle)',
                fontSize: '13px',
                color: 'var(--text-primary)',
                lineHeight: '1.5',
              }}
            >
              {decisionRationale}
            </div>
            {event.policy?.pattern && (
              <div style={{ fontSize: '11.5px', color: 'var(--accent-cyan)' }}>
                Matched Pattern Archetype: <strong>{event.policy.pattern}</strong>
              </div>
            )}
          </div>

          {/* TIER 5: Evidence & Signal Breakdown */}
          <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              5. Observed Evidence Signals
            </div>

            {event.evidence && event.evidence.length > 0 ? (
              <ul style={{ paddingLeft: '18px', fontSize: '12.5px', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {event.evidence.map((item, idx) => (
                  <li key={idx} style={{ lineHeight: '1.4' }}>{item}</li>
                ))}
              </ul>
            ) : (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Standard baseline traffic — no anomalous risk signals flagged.
              </div>
            )}
          </div>

          {/* TIER 6: Machine Learning Signals */}
          <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                6. Raw Machine Learning Signal
              </div>
              <span className="badge badge-purple" style={{ fontSize: '10px' }}>
                Inference Pipeline
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ padding: '10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>Model Posterior Probability</span>
                <div className="font-mono" style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
                  {event.rawMl.probability !== undefined ? `${(event.rawMl.probability * 100).toFixed(1)}%` : 'N/A'}
                </div>
              </div>

              <div style={{ padding: '10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>Evaluating Engine</span>
                <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--accent-cyan)', marginTop: '4px' }}>
                  {event.engine.replace(/_/g, ' ')}
                </div>
              </div>
            </div>
          </div>

          {/* TIER 7: Temporal & Telemetry Diagnostics */}
          <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                7. Temporal & Telemetry Diagnostics
              </div>
              <span className={`badge ${metrics.guardrailTriggered ? 'badge-medium' : 'badge-cyan'}`} style={{ fontSize: '10px' }}>
                {metrics.guardrailTriggered ? 'Guardrail Active' : 'Monitored'}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
              <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>5-Min Velocity</span>
                <div className="font-mono" style={{ fontSize: '15px', fontWeight: '800', color: (metrics.burstRatio || 0) >= 3.0 ? 'var(--risk-high)' : 'var(--text-primary)', marginTop: '2px' }}>
                  {metrics.burstRatio !== null ? `${metrics.burstRatio.toFixed(2)}x` : '1.00x'}
                </div>
              </div>

              <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Active Windows</span>
                <div className="font-mono" style={{ fontSize: '15px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
                  {metrics.observationCount !== null ? `${metrics.observationCount} windows` : '1-Hour Baseline'}
                </div>
              </div>

              <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Persistence</span>
                <div className="font-mono" style={{ fontSize: '15px', fontWeight: '800', color: metrics.consecutiveWindows > 0 ? 'var(--risk-medium)' : 'var(--text-muted)', marginTop: '2px' }}>
                  {metrics.consecutiveWindows} windows
                </div>
              </div>
            </div>

            {/* Rates Row if baseline or current rates are present */}
            {metrics.baselineFraudRate !== null && metrics.currentFraudRate !== null && (
              <div
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-app)',
                  border: '1px solid var(--border-subtle)',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: '8px',
                  fontSize: '11px',
                }}
              >
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Baseline Rate: </span>
                  <strong style={{ color: 'var(--text-primary)' }}>{(metrics.baselineFraudRate * 100).toFixed(2)}%</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Current Rate: </span>
                  <strong style={{ color: 'var(--text-primary)' }}>{(metrics.currentFraudRate * 100).toFixed(2)}%</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Delta: </span>
                  <strong style={{ color: (metrics.fraudRateChange || 0) > 0 ? 'var(--risk-high)' : 'var(--risk-low)' }}>
                    {metrics.fraudRateChange !== null ? `${(metrics.fraudRateChange * 100).toFixed(2)}%` : '--'}
                  </strong>
                </div>
              </div>
            )}
          </div>

          {/* TIER 8: Related Payment / Account / Entity Information */}
          <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              8. Entity & Ingestion Footprint
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '12px' }}>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>Entity Type: </span>
                <strong style={{ color: 'var(--text-primary)' }}>{event.entityType}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>Entity ID: </span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent-cyan)' }}>{event.entityId}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>Detection Time: </span>
                <span style={{ color: 'var(--text-primary)' }}>{event.timestamp.toLocaleString()}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>Event ID: </span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)' }}>{event.id}</span>
              </div>
            </div>

            {metrics.paymentDetails && (
              <div
                style={{
                  fontSize: '11.5px',
                  color: 'var(--accent-cyan)',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(56, 189, 248, 0.08)',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                }}
              >
                {metrics.paymentDetails}
              </div>
            )}

            {/* Syndicate Member Attribution if present */}
            {event.attribution && event.attribution.length > 0 && (
              <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Linked Syndicate Accounts ({event.attribution.length}):
                </span>
                {event.attribution.map((node) => (
                  <div
                    key={node.accountId}
                    style={{
                      padding: '6px 10px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'var(--bg-app)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '11.5px',
                    }}
                  >
                    <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{node.accountId}</span>
                    <span className="badge" style={{ fontSize: '9.5px', textTransform: 'uppercase' }}>{node.role}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvestigationDrawer;
