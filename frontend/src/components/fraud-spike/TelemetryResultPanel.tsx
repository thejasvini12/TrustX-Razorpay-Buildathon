import React from 'react';
import { Zap } from 'lucide-react';

interface TelemetryResultPanelProps {
  telemetryAvailable?: boolean;
  observationCount?: number;
  currentTxCount?: number | null;
  velocityRatio?: number | null;
  guardrailTriggered?: boolean;
}

export const TelemetryResultPanel: React.FC<TelemetryResultPanelProps> = ({
  telemetryAvailable = false,
  observationCount = 0,
  currentTxCount = null,
  velocityRatio = null,
  guardrailTriggered = false,
}) => {
  return (
    <div
      className="card"
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        border: guardrailTriggered ? '1px solid var(--risk-medium-border)' : '1px solid var(--border-subtle)',
      }}
    >
      <div>
        <div className="card-header" style={{ marginBottom: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Zap size={16} color={guardrailTriggered ? 'var(--risk-medium)' : 'var(--accent-cyan)'} />
              <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                P5: 5-Minute Sub-Window Telemetry
              </h4>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Short-window radar uncovering sudden intra-hour micro-bursts and bot flooding.
            </p>
          </div>

          <span className={`badge ${guardrailTriggered ? 'badge-medium' : telemetryAvailable ? 'badge-cyan' : 'badge-low'}`} style={{ fontSize: '10px' }}>
            {guardrailTriggered ? 'P5 Burst Detected' : telemetryAvailable ? 'P5 Active' : 'No Sub-Windows'}
          </span>
        </div>

        {telemetryAvailable ? (
          <div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 1fr',
                gap: '8px',
                padding: '12px',
                backgroundColor: 'var(--bg-app)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
                marginBottom: '12px',
              }}
            >
              <div>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Windows</span>
                <div className="font-mono" style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                  {observationCount}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Short-Win Tx</span>
                <div className="font-mono" style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                  {currentTxCount !== null ? currentTxCount : '--'}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Velocity Ratio</span>
                <div className="font-mono" style={{ fontSize: '14px', fontWeight: '700', color: (velocityRatio || 0) >= 3.0 ? 'var(--risk-high)' : 'var(--accent-cyan)', marginTop: '2px' }}>
                  {velocityRatio !== null ? `${velocityRatio.toFixed(2)}x` : '1.00x'}
                </div>
              </div>
            </div>

            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              {guardrailTriggered ? (
                <span style={{ color: 'var(--risk-medium)' }}>
                  Intra-hour velocity burst ratio exceeds threshold $\ge 3.0\times$, triggering P5 short-window escalation.
                </span>
              ) : (
                <span style={{ color: 'var(--text-muted)' }}>
                  Sub-window volume distribution is consistent with normal intra-hour throughput.
                </span>
              )}
            </div>
          </div>
        ) : (
          <div style={{ padding: '16px', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)', textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
            No 5-minute sub-window telemetry payload submitted for this assessment. Standard 1-hour window evaluated.
          </div>
        )}
      </div>
    </div>
  );
};
