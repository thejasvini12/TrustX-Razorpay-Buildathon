import React from 'react';
import { ShieldCheck, Lock, FileCode, CheckCircle } from 'lucide-react';

const FROZEN_MODELS = [
  {
    name: 'risk_engine_rf.joblib',
    role: 'General Account Abuse Classifier',
    architecture: 'RandomForest Pipeline + Feature Selector',
    status: 'Frozen / Protected',
  },
  {
    name: 'return_risk_model.joblib',
    role: 'Return & Wardrobing Abuse Sub-Engine',
    architecture: 'Calibrated Random Forest Pipeline',
    status: 'Frozen / Protected',
  },
  {
    name: 'fraud_spike_model.joblib',
    role: 'Temporal Fraud Spike Velocity Model',
    architecture: 'Calibrated Ensemble + P1/P5 Guardrails',
    status: 'Frozen / Protected',
  },
  {
    name: 'abuse_ring_model.joblib',
    role: 'Abuse Ring Graph Topology Classifier',
    architecture: 'Bipartite Cluster Model + Evidence Layer',
    status: 'Frozen / Protected',
  },
];

export const ModelIntegrityPanel: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Lock size={16} color="var(--risk-low)" />
            <h3 className="card-title">Model Integrity & Frozen State Architecture</h3>
          </div>
          <p className="card-description">
            Verified baseline machine learning artifacts are immutable and locked against retraining or parameter drift.
          </p>
        </div>
        <span className="badge badge-low">
          <ShieldCheck size={12} />
          <span>4 Models Protected</span>
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {FROZEN_MODELS.map((model) => (
          <div
            key={model.name}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              backgroundColor: 'var(--bg-app)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              flexWrap: 'wrap',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <FileCode size={16} color="var(--accent-cyan)" />
              <div>
                <div className="font-mono" style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                  models/{model.name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  {model.role} • <span style={{ color: 'var(--text-muted)' }}>{model.architecture}</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle size={13} color="var(--risk-low)" />
              <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--risk-low)', letterSpacing: '0.02em' }}>
                {model.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
