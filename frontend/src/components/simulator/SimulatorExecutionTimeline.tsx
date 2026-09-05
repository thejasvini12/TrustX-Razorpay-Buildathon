import React from 'react';
import { RuntimeStageState, SimulatorExecutionStatus, SimulatorEngine } from '../../types/simulator';
import {
  Clock,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Activity,
} from 'lucide-react';

interface SimulatorExecutionTimelineProps {
  stages: RuntimeStageState[];
  status: SimulatorExecutionStatus;
  totalLatencyMs?: number;
  isPersistentIncident?: boolean;
}

const ENGINE_BADGES: Record<SimulatorEngine, { label: string; color: string; bg: string }> = {
  ACCOUNT_RISK: { label: 'Account Risk', color: 'var(--accent-cyan)', bg: 'rgba(56, 189, 248, 0.12)' },
  FRAUD_SPIKE: { label: 'Fraud Spike', color: 'var(--risk-medium)', bg: 'rgba(245, 158, 11, 0.12)' },
  ABUSE_RING: { label: 'Abuse Ring', color: 'var(--risk-critical)', bg: 'rgba(168, 85, 247, 0.14)' },
};

export const SimulatorExecutionTimeline: React.FC<SimulatorExecutionTimelineProps> = ({
  stages,
  status,
  totalLatencyMs,
  isPersistentIncident = false,
}) => {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div className="card-header" style={{ marginBottom: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              padding: '8px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              color: 'var(--accent-cyan)',
            }}
          >
            <Activity size={18} />
          </div>
          <div>
            <h3 className="card-title" style={{ fontSize: '15px' }}>
              Multi-Engine Execution Timeline
            </h3>
            <p className="card-description" style={{ fontSize: '12px' }}>
              {isPersistentIncident
                ? 'Sequential stateful multi-window evaluation across consecutive observation windows'
                : 'Concurrent live orchestration across independent risk & defense engines'}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {isPersistentIncident && (
            <span
              style={{
                fontSize: '11px',
                fontWeight: '600',
                padding: '3px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(245, 158, 11, 0.15)',
                color: 'var(--risk-medium)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
              }}
            >
              Sequential Mode (P3 Persistence)
            </span>
          )}

          {totalLatencyMs !== undefined && status !== 'RUNNING' && status !== 'IDLE' && (
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono, monospace' }}>
              Total Latency: <strong style={{ color: 'var(--accent-cyan)' }}>{totalLatencyMs} ms</strong>
            </span>
          )}
        </div>
      </div>

      {/* Stage Flow Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${stages.length}, minmax(0, 1fr))`,
          gap: '12px',
          position: 'relative',
        }}
      >
        {stages.map((stage, index) => {
          const engineInfo = ENGINE_BADGES[stage.engine];
          const isLast = index === stages.length - 1;

          let statusIcon = <Clock size={16} color="var(--text-muted)" />;
          let statusLabel = 'Pending';
          let cardBorder = 'var(--border-subtle)';
          let cardBg = 'var(--bg-app)';

          if (stage.status === 'running') {
            statusIcon = <Loader2 size={16} className="animate-spin" color="var(--accent-cyan)" />;
            statusLabel = 'In Flight...';
            cardBorder = 'var(--accent-cyan)';
            cardBg = 'rgba(56, 189, 248, 0.04)';
          } else if (stage.status === 'completed') {
            statusIcon = <CheckCircle2 size={16} color="var(--risk-low)" />;
            statusLabel = 'Completed';
            cardBorder = 'rgba(16, 185, 129, 0.3)';
            cardBg = 'rgba(16, 185, 129, 0.03)';
          } else if (stage.status === 'failed') {
            statusIcon = <AlertCircle size={16} color="var(--risk-high)" />;
            statusLabel = 'Failed';
            cardBorder = 'rgba(244, 63, 94, 0.4)';
            cardBg = 'rgba(244, 63, 94, 0.05)';
          }

          return (
            <div
              key={stage.stageNumber}
              style={{
                display: 'flex',
                flexDirection: 'column',
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: cardBg,
                border: `1px solid ${cardBorder}`,
                gap: '8px',
                position: 'relative',
                transition: 'all var(--transition-fast)',
              }}
            >
              {/* Connector Arrow for Sequential Windows */}
              {isPersistentIncident && !isLast && (
                <div
                  style={{
                    position: 'absolute',
                    right: '-14px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    zIndex: 2,
                    color: stage.status === 'completed' ? 'var(--risk-low)' : 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  <ArrowRight size={16} />
                </div>
              )}

              {/* Stage Topline */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      color: 'var(--text-muted)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    STAGE {stage.stageNumber}
                  </span>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: '600',
                      padding: '1px 6px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: engineInfo.bg,
                      color: engineInfo.color,
                    }}
                  >
                    {engineInfo.label}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  {statusIcon}
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: '600',
                      color:
                        stage.status === 'completed'
                          ? 'var(--risk-low)'
                          : stage.status === 'running'
                          ? 'var(--accent-cyan)'
                          : stage.status === 'failed'
                          ? 'var(--risk-high)'
                          : 'var(--text-muted)',
                    }}
                  >
                    {statusLabel}
                  </span>
                </div>
              </div>

              {/* Stage Title & Description */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
                <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                  {stage.title}
                </div>
                <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', lineHeight: '1.35' }}>
                  {stage.description}
                </div>
              </div>

              {/* Footer: Latency or Error */}
              {stage.status === 'completed' && stage.latencyMs !== undefined && (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    paddingTop: '6px',
                    borderTop: '1px solid var(--border-subtle)',
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                  }}
                >
                  <span>Roundtrip Latency</span>
                  <span
                    style={{
                      fontWeight: '600',
                      color: 'var(--risk-low)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    {stage.latencyMs} ms
                  </span>
                </div>
              )}

              {stage.status === 'failed' && (
                <div
                  style={{
                    padding: '6px 8px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'rgba(244, 63, 94, 0.1)',
                    border: '1px solid rgba(244, 63, 94, 0.25)',
                    fontSize: '11px',
                    color: 'var(--risk-high)',
                    lineHeight: '1.3',
                  }}
                >
                  {stage.error || 'Engine request failed.'}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
