import React from 'react';
import { CheckCircle2, AlertTriangle, FileCheck } from 'lucide-react';

interface DataQualityPanelProps {
  score: number;
  warnings?: string[];
}

export const DataQualityPanel: React.FC<DataQualityPanelProps> = ({ score, warnings = [] }) => {
  const percentage = Math.round(score * 100);
  const hasWarnings = warnings.length > 0;

  return (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div>
        <div className="card-header" style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileCheck size={16} color="var(--accent-cyan)" />
            <h3 className="card-title">Input Sanitization & Data Quality</h3>
          </div>
          <span className={`badge ${percentage >= 80 ? 'badge-low' : percentage >= 50 ? 'badge-medium' : 'badge-high'}`}>
            {percentage}% Quality
          </span>
        </div>

        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
          Automated input completeness and outlier normalization pass before model inference.
        </p>

        {/* Quality Bar */}
        <div style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
            <span>Completeness Score</span>
            <span className="font-mono" style={{ color: 'var(--text-primary)', fontWeight: '600' }}>{percentage}%</span>
          </div>
          <div style={{ height: '6px', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-pill)', overflow: 'hidden' }}>
            <div
              style={{
                width: `${percentage}%`,
                height: '100%',
                backgroundColor: percentage >= 80 ? 'var(--risk-low)' : percentage >= 50 ? 'var(--risk-medium)' : 'var(--risk-high)',
                borderRadius: 'var(--radius-pill)',
                transition: 'width 400ms ease',
              }}
            />
          </div>
        </div>

        {/* Warnings or Clean State */}
        <div>
          <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)' }}>
            Sanitization Log
          </span>

          {hasWarnings ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
              {warnings.map((warn, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '6px',
                    padding: '8px 10px',
                    backgroundColor: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid var(--risk-medium-border)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    color: 'var(--risk-medium)',
                  }}
                >
                  <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: '2px' }} />
                  <span>{warn}</span>
                </div>
              ))}
            </div>
          ) : (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 12px',
                backgroundColor: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid var(--risk-low-border)',
                borderRadius: 'var(--radius-sm)',
                marginTop: '6px',
                fontSize: '11px',
                color: 'var(--risk-low)',
              }}
            >
              <CheckCircle2 size={14} />
              <span>Input quality: Clean • All behavioral features within verified bounds</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
