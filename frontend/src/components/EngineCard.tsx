import React from 'react';
import { NavLink } from 'react-router-dom';
import { LucideIcon, ArrowRight, CheckCircle2 } from 'lucide-react';

export interface EngineCardProps {
  name: string;
  subtitle: string;
  description: string;
  icon: LucideIcon;
  tags: string[];
  route: string;
  accentColor?: string;
  accentBg?: string;
  badgeText?: string;
  badgeType?: 'low' | 'medium' | 'high' | 'critical' | 'cyan';
  operationalNote?: string;
}

export const EngineCard: React.FC<EngineCardProps> = ({
  name,
  subtitle,
  description,
  icon: Icon,
  tags,
  route,
  accentColor = 'var(--accent-cyan)',
  accentBg = 'var(--accent-cyan-bg)',
  badgeText = 'Available',
  badgeType = 'low',
  operationalNote = 'ML Pipeline Verified',
}) => {
  return (
    <div
      className="card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '100%',
      }}
    >
      <div>
        {/* Header with Icon, Name and Status */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                padding: '10px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: accentBg,
                color: accentColor,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Icon size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                {name}
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '500' }}>
                {subtitle}
              </span>
            </div>
          </div>
          <span className={`badge badge-${badgeType}`}>{badgeText}</span>
        </div>

        {/* Description */}
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.55', marginBottom: '16px' }}>
          {description}
        </p>

        {/* Capability Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '18px' }}>
          {tags.map((tag) => (
            <span
              key={tag}
              style={{
                fontSize: '11px',
                padding: '3px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-input)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Footer / Action */}
      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: 'var(--risk-low)' }}>
          <CheckCircle2 size={13} />
          <span>{operationalNote}</span>
        </div>

        <NavLink
          to={route}
          className="btn btn-secondary"
          style={{
            fontSize: '12px',
            padding: '6px 14px',
            gap: '6px',
          }}
        >
          <span>Open Module</span>
          <ArrowRight size={13} />
        </NavLink>
      </div>
    </div>
  );
};
