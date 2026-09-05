import React, { useState } from 'react';
import { EvidenceAdjustmentsResponse } from '../../types/api';
import { TrendingUp, TrendingDown, ChevronDown, ChevronUp, Zap } from 'lucide-react';

interface EvidenceAdjustmentPanelProps {
  evidenceAdjustments?: EvidenceAdjustmentsResponse;
}

export const EvidenceAdjustmentPanel: React.FC<EvidenceAdjustmentPanelProps> = ({
  evidenceAdjustments,
}) => {
  const [expanded, setExpanded] = useState<boolean>(true);

  if (!evidenceAdjustments) return null;

  const { positive_adjustments = [], mitigating_adjustments = [], total_positive_delta, total_negative_delta, net_delta } =
    evidenceAdjustments;

  const hasAdjustments = positive_adjustments.length > 0 || mitigating_adjustments.length > 0;

  return (
    <div className="card">
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap size={16} color="var(--accent-purple)" />
          <div>
            <h3 className="card-title">Deterministic Evidence Adjustments</h3>
            <p className="card-description">
              Explicit domain rules applying score bonuses or safety damping to raw ML predictions.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-purple" style={{ fontSize: '11px' }}>
            Net: {net_delta >= 0 ? `+${(net_delta * 100).toFixed(0)}` : `${(net_delta * 100).toFixed(0)}`} pts
          </span>
          {expanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {hasAdjustments ? (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '14px',
              }}
            >
              {/* Positive Risk Boosts */}
              <div
                style={{
                  padding: '12px 14px',
                  backgroundColor: 'rgba(244, 63, 94, 0.04)',
                  border: '1px solid var(--risk-high-border)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', color: 'var(--risk-high)' }}>
                  <TrendingUp size={14} />
                  <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Risk-Elevating Adjustments (+{(total_positive_delta * 100).toFixed(0)} pts)
                  </span>
                </div>

                {positive_adjustments.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {positive_adjustments.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '8px 10px',
                          backgroundColor: 'var(--bg-app)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                          <span className="font-mono" style={{ fontSize: '11px', fontWeight: '700', color: 'var(--risk-high)' }}>
                            {item.code}
                          </span>
                          <span style={{ fontSize: '11px', fontWeight: '800', color: 'var(--risk-high)' }}>
                            +{(item.delta * 100).toFixed(0)} pts
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                          {item.reason}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    No positive risk adjustments applied.
                  </div>
                )}
              </div>

              {/* Mitigating Safety Dampers */}
              <div
                style={{
                  padding: '12px 14px',
                  backgroundColor: 'rgba(16, 185, 129, 0.04)',
                  border: '1px solid var(--risk-low-border)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', color: 'var(--risk-low)' }}>
                  <TrendingDown size={14} />
                  <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Mitigating Safety Dampers (-{(total_negative_delta * 100).toFixed(0)} pts)
                  </span>
                </div>

                {mitigating_adjustments.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {mitigating_adjustments.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '8px 10px',
                          backgroundColor: 'var(--bg-app)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                          <span className="font-mono" style={{ fontSize: '11px', fontWeight: '700', color: 'var(--risk-low)' }}>
                            {item.code}
                          </span>
                          <span style={{ fontSize: '11px', fontWeight: '800', color: 'var(--risk-low)' }}>
                            -{(Math.abs(item.delta) * 100).toFixed(0)} pts
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                          {item.reason}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    No mitigating safety adjustments applied.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ padding: '12px', textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
              No deterministic adjustments triggered. Final score equals raw model probability.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
