import React from 'react';
import { Layers } from 'lucide-react';

export const SpikeArchitectureFlow: React.FC = () => {
  const steps = [
    { label: '1. Baseline Window', sub: '24h Historical Benchmarks' },
    { label: '2. Current Window', sub: '1h Target Metrics' },
    { label: '3. ML Inference', sub: 'RandomForest Prob P4' },
    { label: '4. P1 Delta Guardrail', sub: 'Deterministic Rate Floor' },
    { label: '5. P3 Persistence', sub: 'Multi-Window Escalation' },
    { label: '6. P5 Sub-Window', sub: '5-Min Telemetry Radar' },
    { label: '7. Operational Action', sub: 'Gated Defense Response' },
  ];

  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} color="var(--accent-cyan)" />
            <h3 className="card-title">Layered Fraud-Spike Pipeline Architecture</h3>
          </div>
          <p className="card-description">
            Transparent deterministic policy evaluation wrapping the frozen Random Forest velocity estimator.
          </p>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '8px',
          alignItems: 'center',
        }}
      >
        {steps.map((step, idx) => (
          <div
            key={idx}
            style={{
              padding: '10px',
              backgroundColor: 'var(--bg-app)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--accent-cyan)' }}>
              {step.label}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
              {step.sub}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
