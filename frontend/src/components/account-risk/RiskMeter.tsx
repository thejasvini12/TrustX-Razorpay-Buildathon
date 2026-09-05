import React from 'react';

interface RiskMeterProps {
  score: number;
  level: 'LOW' | 'MEDIUM' | 'HIGH' | string;
}

export const RiskMeter: React.FC<RiskMeterProps> = ({ score, level }) => {
  const clampedScore = Math.max(0, Math.min(100, score));

  const getLevelColor = () => {
    switch (level) {
      case 'LOW':
        return 'var(--risk-low)';
      case 'MEDIUM':
        return 'var(--risk-medium)';
      case 'HIGH':
        return 'var(--risk-high)';
      default:
        return 'var(--accent-cyan)';
    }
  };

  const levelColor = getLevelColor();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
      {/* Meter Bar Container */}
      <div
        style={{
          position: 'relative',
          height: '16px',
          backgroundColor: 'var(--bg-app)',
          borderRadius: 'var(--radius-pill)',
          border: '1px solid var(--border-subtle)',
          overflow: 'hidden',
          display: 'flex',
        }}
      >
        {/* Segment: LOW (0 - 29%) */}
        <div
          style={{
            width: '30%',
            height: '100%',
            backgroundColor: 'rgba(16, 185, 129, 0.25)',
            borderRight: '1px solid rgba(0, 0, 0, 0.4)',
          }}
          title="LOW Risk Tier (0 - 29)"
        />

        {/* Segment: MEDIUM (30 - 69%) */}
        <div
          style={{
            width: '40%',
            height: '100%',
            backgroundColor: 'rgba(245, 158, 11, 0.25)',
            borderRight: '1px solid rgba(0, 0, 0, 0.4)',
          }}
          title="MEDIUM Risk Tier (30 - 69)"
        />

        {/* Segment: HIGH (70 - 100%) */}
        <div
          style={{
            width: '30%',
            height: '100%',
            backgroundColor: 'rgba(244, 63, 94, 0.25)',
          }}
          title="HIGH Risk Tier (70 - 100)"
        />

        {/* Active Fill Indicator */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            bottom: 0,
            width: `${clampedScore}%`,
            background: `linear-gradient(90deg, rgba(16, 185, 129, 0.7) 0%, rgba(245, 158, 11, 0.8) 50%, rgba(244, 63, 94, 0.9) 100%)`,
            opacity: 0.85,
            transition: 'width 600ms cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        />

        {/* Needle Marker */}
        <div
          style={{
            position: 'absolute',
            top: '-2px',
            bottom: '-2px',
            left: `calc(${clampedScore}% - 2px)`,
            width: '4px',
            backgroundColor: '#ffffff',
            boxShadow: `0 0 8px ${levelColor}`,
            borderRadius: '2px',
            zIndex: 3,
            transition: 'left 600ms cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        />
      </div>

      {/* Threshold Labels */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '10px',
          fontWeight: '600',
          color: 'var(--text-muted)',
          padding: '0 2px',
        }}
      >
        <span style={{ color: 'var(--risk-low)' }}>0 LOW</span>
        <span style={{ color: 'var(--risk-medium)' }}>30 MEDIUM</span>
        <span style={{ color: 'var(--risk-high)' }}>70 HIGH</span>
        <span>100</span>
      </div>
    </div>
  );
};
