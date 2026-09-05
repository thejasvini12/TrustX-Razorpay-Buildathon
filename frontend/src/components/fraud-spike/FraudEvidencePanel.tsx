import React from 'react';
import { FileText, TrendingUp, TrendingDown } from 'lucide-react';

interface FraudEvidencePanelProps {
  evidenceQuality: string;
  confidence: string;
  evidenceSummary: string;
  explanation: string;
  spikeFactors?: string[];
  mitigatingFactors?: string[];
}

export const FraudEvidencePanel: React.FC<FraudEvidencePanelProps> = ({
  evidenceQuality,
  confidence,
  evidenceSummary,
  explanation,
  spikeFactors = [],
  mitigatingFactors = [],
}) => {
  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileText size={16} color="var(--accent-cyan)" />
            <h3 className="card-title">Evidence Synthesis & Anomaly Explanation</h3>
          </div>
          <p className="card-description">
            Statistical grounding, sample quality indicators, and natural-language anomaly decomposition.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-cyan" style={{ fontSize: '11px' }}>
            Quality: {evidenceQuality}
          </span>
          <span className="badge badge-low" style={{ fontSize: '11px' }}>
            Confidence: {confidence}
          </span>
        </div>
      </div>

      {/* Narrative Box */}
      {(evidenceSummary || explanation) && (
        <div
          style={{
            padding: '14px 16px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            marginBottom: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          {evidenceSummary && (
            <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
              {evidenceSummary}
            </div>
          )}
          {explanation && (
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.55' }}>
              {explanation}
            </div>
          )}
        </div>
      )}

      {/* Factors & Mitigations Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '16px',
        }}
      >
        {/* Spike Factors */}
        <div
          style={{
            padding: '14px',
            backgroundColor: 'rgba(244, 63, 94, 0.05)',
            border: '1px solid var(--risk-high-border)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px', color: 'var(--risk-high)' }}>
            <TrendingUp size={15} />
            <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Elevating Velocity Signals ({spikeFactors.length})
            </span>
          </div>

          {spikeFactors.length > 0 ? (
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {spikeFactors.map((factor, idx) => (
                <li key={idx} style={{ fontSize: '12px', color: 'var(--text-primary)', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                  <span style={{ color: 'var(--risk-high)', fontWeight: 'bold' }}>•</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No critical surge factors detected.
            </div>
          )}
        </div>

        {/* Mitigating Factors */}
        <div
          style={{
            padding: '14px',
            backgroundColor: 'rgba(16, 185, 129, 0.05)',
            border: '1px solid var(--risk-low-border)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px', color: 'var(--risk-low)' }}>
            <TrendingDown size={15} />
            <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Stabilizing Traffic Signals ({mitigatingFactors.length})
            </span>
          </div>

          {mitigatingFactors.length > 0 ? (
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {mitigatingFactors.map((factor, idx) => (
                <li key={idx} style={{ fontSize: '12px', color: 'var(--text-primary)', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                  <span style={{ color: 'var(--risk-low)', fontWeight: 'bold' }}>•</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No stabilizing baseline factors present.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
