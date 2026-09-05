import React from 'react';
import { FileText, TrendingUp, TrendingDown } from 'lucide-react';

interface RingFactorsPanelProps {
  evidenceQuality: string;
  confidence: string;
  evidenceSummary: string;
  decisionReasoning: string;
  ringFactors?: string[];
  mitigatingFactors?: string[];
}

export const RingFactorsPanel: React.FC<RingFactorsPanelProps> = ({
  evidenceQuality,
  confidence,
  evidenceSummary,
  decisionReasoning,
  ringFactors = [],
  mitigatingFactors = [],
}) => {
  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileText size={16} color="var(--accent-cyan)" />
            <h3 className="card-title">Evidence Synthesis & Graph Reasoning</h3>
          </div>
          <p className="card-description">
            Decomposition of structural clique density, anomaly alignment, and benign contextual indicators.
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

      {/* Narrative Summary and Reasoning */}
      {(evidenceSummary || decisionReasoning) && (
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
            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
              {evidenceSummary}
            </div>
          )}
          {decisionReasoning && (
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.55' }}>
              {decisionReasoning}
            </div>
          )}
        </div>
      )}

      {/* Factors Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '16px',
        }}
      >
        {/* Ring Elevating Factors */}
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
              Syndicate Signals ({ringFactors.length})
            </span>
          </div>

          {ringFactors.length > 0 ? (
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {ringFactors.map((factor, idx) => (
                <li key={idx} style={{ fontSize: '12px', color: 'var(--text-primary)', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                  <span style={{ color: 'var(--risk-high)', fontWeight: 'bold' }}>•</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No coordinated syndicate factors detected.
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
              Benign Contextual Factors ({mitigatingFactors.length})
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
              No benign mitigating factors observed.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
