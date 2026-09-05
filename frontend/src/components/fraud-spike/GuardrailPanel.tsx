import React from 'react';
import { ShieldAlert } from 'lucide-react';

interface GuardrailPanelProps {
  guardrailTriggered?: boolean;
  fraudRateChange: number;
  baselineRate: number;
  currentRate: number;
}

export const GuardrailPanel: React.FC<GuardrailPanelProps> = ({
  guardrailTriggered = false,
  fraudRateChange,
  baselineRate,
  currentRate,
}) => {
  return (
    <div
      className="card"
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        border: guardrailTriggered ? '1px solid var(--risk-high-border)' : '1px solid var(--border-subtle)',
      }}
    >
      <div>
        <div className="card-header" style={{ marginBottom: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldAlert size={16} color={guardrailTriggered ? 'var(--risk-high)' : 'var(--risk-low)'} />
              <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                P1: Fraud-Rate Delta Guardrail
              </h4>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Deterministic floor enforcing escalation when fraud rate surge $\Delta \ge 15\%$.
            </p>
          </div>

          <span className={`badge ${guardrailTriggered ? 'badge-high' : 'badge-low'}`} style={{ fontSize: '10px' }}>
            {guardrailTriggered ? 'Guardrail Triggered' : 'Not Triggered'}
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '10px',
            padding: '12px',
            backgroundColor: 'var(--bg-app)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            marginBottom: '12px',
          }}
        >
          <div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Baseline Rate</span>
            <div className="font-mono" style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-secondary)' }}>
              {(baselineRate * 100).toFixed(1)}%
            </div>
          </div>

          <div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Current Rate</span>
            <div className="font-mono" style={{ fontSize: '14px', fontWeight: '700', color: currentRate > baselineRate ? 'var(--risk-high)' : 'var(--text-primary)' }}>
              {(currentRate * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px' }}>
          <span style={{ color: 'var(--text-secondary)' }}>Net Rate Delta ($\Delta$):</span>
          <span className="font-mono" style={{ fontWeight: '700', color: fraudRateChange > 0.15 ? 'var(--risk-high)' : fraudRateChange > 0 ? 'var(--risk-medium)' : 'var(--risk-low)' }}>
            {fraudRateChange >= 0 ? `+${(fraudRateChange * 100).toFixed(1)}%` : `${(fraudRateChange * 100).toFixed(1)}%`}
          </span>
        </div>
      </div>
    </div>
  );
};
