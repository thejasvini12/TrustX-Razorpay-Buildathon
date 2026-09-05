import React from 'react';
import { HelpCircle, TrendingUp, TrendingDown, BookOpen } from 'lucide-react';

interface ExplainabilityPanelProps {
  explanationSummary?: string;
  decisionReasoning?: string;
  increasingSignals?: string[];
  reducingSignals?: string[];
}

export const ExplainabilityPanel: React.FC<ExplainabilityPanelProps> = ({
  explanationSummary,
  decisionReasoning,
  increasingSignals = [],
  reducingSignals = [],
}) => {
  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <HelpCircle size={16} color="var(--accent-cyan)" />
            <h3 className="card-title">Why did TrustX make this decision?</h3>
          </div>
          <p className="card-description">
            Dual-layer explainability articulating statistical features, tier reasoning, and prominent behavioral signals.
          </p>
        </div>
      </div>

      {/* Summary Narrative */}
      {explanationSummary && (
        <div
          style={{
            padding: '14px 16px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            marginBottom: '16px',
            fontSize: '13px',
            color: 'var(--text-primary)',
            lineHeight: '1.6',
          }}
        >
          {explanationSummary}
        </div>
      )}

      {/* Decision Tier Reasoning */}
      {decisionReasoning && (
        <div style={{ marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <BookOpen size={14} color="var(--text-muted)" />
            <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Tier Assignment Rationale
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.55' }}>
            {decisionReasoning}
          </p>
        </div>
      )}

      {/* Dual Signals Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '16px',
        }}
      >
        {/* Risk Increasing Signals */}
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
              Risk Increasing Signals ({increasingSignals.length})
            </span>
          </div>

          {increasingSignals.length > 0 ? (
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {increasingSignals.map((sig, idx) => (
                <li
                  key={idx}
                  style={{
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '6px',
                  }}
                >
                  <span style={{ color: 'var(--risk-high)', fontWeight: 'bold' }}>•</span>
                  <span>{sig}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No prominent risk-elevating signals detected.
            </div>
          )}
        </div>

        {/* Risk Reducing Signals */}
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
              Risk Mitigating Signals ({reducingSignals.length})
            </span>
          </div>

          {reducingSignals.length > 0 ? (
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {reducingSignals.map((sig, idx) => (
                <li
                  key={idx}
                  style={{
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '6px',
                  }}
                >
                  <span style={{ color: 'var(--risk-low)', fontWeight: 'bold' }}>•</span>
                  <span>{sig}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No prominent mitigating signals present.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
