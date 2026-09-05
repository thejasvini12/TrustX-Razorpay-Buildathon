import React from 'react';
import { AbuseRingResponse } from '../../types/api';
import { Cpu, ShieldCheck, Zap } from 'lucide-react';

interface RawVsEvidencePanelProps {
  result: AbuseRingResponse;
}

export const RawVsEvidencePanel: React.FC<RawVsEvidencePanelProps> = ({ result }) => {
  const {
    raw_ml_probability,
    model_prediction,
    model_threshold,
    evidence_adjustments,
    final_ring_score,
    risk_level,
    verdict,
  } = result;

  const netDelta = evidence_adjustments?.net_delta ?? 0.0;
  const hasAdjustment = Math.abs(netDelta) > 0.001;

  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '16px' }}>
        <div>
          <h3 className="card-title">ML Probability vs Evidence-Adjusted Decision</h3>
          <p className="card-description">
            Dual-stage evaluation separating frozen Random Forest graph classification from deterministic topology evidence adjustments.
          </p>
        </div>

        <span
          className={`badge ${hasAdjustment ? 'badge-cyan' : 'badge-low'}`}
          style={{ fontSize: '11px', padding: '4px 10px' }}
        >
          {hasAdjustment ? `Evidence Adjusted (Net: ${netDelta >= 0 ? `+${netDelta.toFixed(2)}` : netDelta.toFixed(2)})` : 'No Evidence Shift'}
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px',
          alignItems: 'stretch',
        }}
      >
        {/* 1. Raw ML Classification */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '8px',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-cyan)' }}>
              <Cpu size={15} />
              <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                1. Raw ML Classifier
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginTop: '6px' }}>
              <div className="font-mono" style={{ fontSize: '26px', fontWeight: '800', color: 'var(--text-primary)' }}>
                {(raw_ml_probability * 100).toFixed(1)}%
              </div>
              <span style={{ fontSize: '11px', fontWeight: '600', color: model_prediction ? 'var(--risk-high)' : 'var(--risk-low)' }}>
                {model_prediction ? 'PREDICTED RING' : 'PREDICTED BENIGN'}
              </span>
            </div>

            <div className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              P(Ring) = {raw_ml_probability.toFixed(4)} • Threshold: {model_threshold.toFixed(2)}
            </div>
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            15-feature topological subgraph random forest
          </div>
        </div>

        {/* 2. Deterministic Evidence Layer */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '8px',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-purple)' }}>
              <Zap size={15} />
              <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                2. Evidence Layer Delta
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginTop: '6px' }}>
              <div className="font-mono" style={{ fontSize: '26px', fontWeight: '800', color: netDelta > 0 ? 'var(--risk-high)' : netDelta < 0 ? 'var(--risk-low)' : 'var(--text-primary)' }}>
                {netDelta >= 0 ? `+${(netDelta * 100).toFixed(0)}` : `${(netDelta * 100).toFixed(0)}`}
                <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}> pts</span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                Net Shift
              </span>
            </div>

            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Boosts: <strong style={{ color: 'var(--risk-high)' }}>+{(evidence_adjustments?.total_positive_delta * 100).toFixed(0)}</strong> • Mitigations: <strong style={{ color: 'var(--risk-low)' }}>-{(evidence_adjustments?.total_negative_delta * 100).toFixed(0)}</strong>
            </div>
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Domain-specific bipartite safety adjustments
          </div>
        </div>

        {/* 3. Final Operational Verdict */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-elevated)',
            border: '1px solid var(--border-muted)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '8px',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-primary)' }}>
              <ShieldCheck size={15} color="var(--accent-cyan)" />
              <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                3. Final Operational Decision
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginTop: '6px' }}>
              <div className="font-mono" style={{ fontSize: '26px', fontWeight: '800', color: 'var(--text-primary)' }}>
                {(final_ring_score * 100).toFixed(0)}
                <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>/100</span>
              </div>
              <span style={{ fontSize: '11px', fontWeight: '700', color: risk_level === 'CRITICAL' || risk_level === 'HIGH' ? 'var(--risk-critical)' : risk_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)' }}>
                {risk_level} RISK
              </span>
            </div>

            <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
              Verdict: {verdict}
            </div>
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Authoritative operational outcome
          </div>
        </div>
      </div>
    </div>
  );
};
