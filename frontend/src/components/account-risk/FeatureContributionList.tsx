import React from 'react';
import { FeatureContribution } from '../../types/api';
import { BarChart3, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface FeatureContributionListProps {
  contributions?: FeatureContribution[];
}

export const FeatureContributionList: React.FC<FeatureContributionListProps> = ({ contributions = [] }) => {
  if (contributions.length === 0) return null;

  // Find max importance for scaling bars
  const maxImportance = Math.max(...contributions.map((c) => Math.abs(c.importance)), 0.01);

  const formatFeatureName = (feat: string) => {
    return feat
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const getImpactBadge = (impact: string) => {
    switch (impact) {
      case 'RISK_INCREASING':
      case 'HIGH_RISK':
      case 'ELEVATING':
        return { label: 'Elevating', color: 'var(--risk-high)', bg: 'var(--risk-high-bg)', icon: TrendingUp };
      case 'RISK_REDUCING':
      case 'PROTECTIVE':
      case 'MITIGATING':
        return { label: 'Protective', color: 'var(--risk-low)', bg: 'var(--risk-low-bg)', icon: TrendingDown };
      default:
        return { label: 'Neutral', color: 'var(--text-muted)', bg: 'var(--bg-app)', icon: Minus };
    }
  };

  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart3 size={16} color="var(--accent-cyan)" />
            <h3 className="card-title">Ranked Feature Influences</h3>
          </div>
          <p className="card-description">
            Relative predictive weight of input attributes derived from model feature importances.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {contributions.map((item, idx) => {
          const impactInfo = getImpactBadge(item.impact);
          const ImpactIcon = impactInfo.icon;
          const barWidth = Math.min(100, Math.round((Math.abs(item.importance) / maxImportance) * 100));

          return (
            <div
              key={idx}
              style={{
                padding: '10px 14px',
                backgroundColor: 'var(--bg-app)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', width: '20px' }}>
                    #{idx + 1}
                  </span>
                  <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                    {item.display_name || formatFeatureName(item.feature)}
                  </span>
                  {item.observed_value !== undefined && (
                    <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      [val: {String(item.observed_value)}]
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    Weight: {(item.importance * 100).toFixed(1)}%
                  </span>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-pill)',
                      backgroundColor: impactInfo.bg,
                      color: impactInfo.color,
                      fontSize: '11px',
                      fontWeight: '600',
                    }}
                  >
                    <ImpactIcon size={12} />
                    <span>{impactInfo.label}</span>
                  </div>
                </div>
              </div>

              {/* Relative Weight Bar */}
              <div style={{ height: '4px', backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-pill)', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${barWidth}%`,
                    height: '100%',
                    backgroundColor: impactInfo.color,
                    borderRadius: 'var(--radius-pill)',
                    transition: 'width 300ms ease',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
