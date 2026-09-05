import React from 'react';
import { FraudSpikeResponse } from '../../types/api';
import { Cpu, ShieldCheck, ArrowRight } from 'lucide-react';

interface RawVsPolicyPanelProps {
  result: FraudSpikeResponse;
}

export const RawVsPolicyPanel: React.FC<RawVsPolicyPanelProps> = ({ result }) => {
  const {
    raw_spike_score,
    raw_spike_probability,
    raw_spike_level,
    spike_score,
    spike_probability,
    spike_level,
    recommended_action,
    guardrail_triggered,
    five_minute_guardrail_triggered,
    persistence_escalation_triggered,
  } = result;

  const hasPolicyAdjustment =
    (raw_spike_score !== undefined && raw_spike_score !== null && raw_spike_score !== spike_score) ||
    guardrail_triggered ||
    five_minute_guardrail_triggered ||
    persistence_escalation_triggered;

  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '16px' }}>
        <div>
          <h3 className="card-title">P4: Raw ML Output vs Operational Decision</h3>
          <p className="card-description">
            Audit transparency comparing unadjusted statistical model inference against policy-layer deterministic escalations.
          </p>
        </div>

        <span
          className={`badge ${hasPolicyAdjustment ? 'badge-medium' : 'badge-low'}`}
          style={{ fontSize: '11px', padding: '4px 10px' }}
        >
          {hasPolicyAdjustment ? 'Policy Adjustment Active' : 'No Policy Adjustment'}
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          gap: '16px',
          alignItems: 'center',
        }}
      >
        {/* Left: Raw ML Output */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-cyan)' }}>
            <Cpu size={16} />
            <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Raw ML Model Output
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginTop: '4px' }}>
            <div className="font-mono" style={{ fontSize: '28px', fontWeight: '800', color: 'var(--text-primary)' }}>
              {raw_spike_score !== undefined && raw_spike_score !== null ? raw_spike_score : spike_score}
              <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>/100</span>
            </div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: '700',
                color: (raw_spike_level || spike_level) === 'HIGH' ? 'var(--risk-high)' : (raw_spike_level || spike_level) === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)',
              }}
            >
              {(raw_spike_level || spike_level)} TIER
            </span>
          </div>

          <div className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Raw P(Spike) = {raw_spike_probability !== undefined && raw_spike_probability !== null ? raw_spike_probability.toFixed(4) : spike_probability.toFixed(4)}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Statistical Random Forest estimation prior to guardrails
          </div>
        </div>

        {/* Center Divider / Flow Arrow */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div
            style={{
              padding: '8px',
              backgroundColor: 'var(--bg-elevated)',
              border: '1px solid var(--border-muted)',
              borderRadius: 'var(--radius-pill)',
              color: 'var(--text-muted)',
            }}
          >
            <ArrowRight size={16} />
          </div>
        </div>

        {/* Right: Operational Result */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-elevated)',
            border: `1px solid ${hasPolicyAdjustment ? 'var(--risk-medium-border)' : 'var(--border-muted)'}`,
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasPolicyAdjustment ? 'var(--risk-medium)' : 'var(--risk-low)' }}>
            <ShieldCheck size={16} />
            <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Operational Defense Result
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginTop: '4px' }}>
            <div className="font-mono" style={{ fontSize: '28px', fontWeight: '800', color: 'var(--text-primary)' }}>
              {spike_score}
              <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>/100</span>
            </div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: '700',
                color: spike_level === 'HIGH' ? 'var(--risk-high)' : spike_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)',
              }}
            >
              {spike_level} TIER
            </span>
          </div>

          <div style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-primary)' }}>
            Action: {recommended_action}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Final policy-enforced output governing risk response
          </div>
        </div>
      </div>
    </div>
  );
};
