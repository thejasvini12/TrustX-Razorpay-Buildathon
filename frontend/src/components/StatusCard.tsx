import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface StatusCardProps {
  label: string;
  value: React.ReactNode;
  subtext: string;
  status?: 'online' | 'offline' | 'verified' | 'neutral' | 'warning';
  icon: LucideIcon;
  badgeText?: string;
}

export const StatusCard: React.FC<StatusCardProps> = ({
  label,
  value,
  subtext,
  status = 'neutral',
  icon: Icon,
  badgeText,
}) => {
  const getStatusStyles = () => {
    switch (status) {
      case 'online':
      case 'verified':
        return {
          iconColor: 'var(--risk-low)',
          iconBg: 'var(--risk-low-bg)',
          borderColor: 'var(--border-subtle)',
          badgeClass: 'badge-low',
        };
      case 'offline':
        return {
          iconColor: 'var(--status-offline)',
          iconBg: 'rgba(239, 68, 68, 0.1)',
          borderColor: 'rgba(239, 68, 68, 0.3)',
          badgeClass: 'badge-high',
        };
      case 'warning':
        return {
          iconColor: 'var(--status-warning)',
          iconBg: 'var(--risk-medium-bg)',
          borderColor: 'var(--risk-medium-border)',
          badgeClass: 'badge-medium',
        };
      case 'neutral':
      default:
        return {
          iconColor: 'var(--accent-cyan)',
          iconBg: 'var(--accent-cyan-bg)',
          borderColor: 'var(--border-subtle)',
          badgeClass: 'badge-cyan',
        };
    }
  };

  const styles = getStatusStyles();

  return (
    <div
      className="card"
      style={{
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        borderColor: styles.borderColor,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {label}
        </span>
        <div
          style={{
            padding: '8px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: styles.iconBg,
            color: styles.iconColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon size={18} />
        </div>
      </div>

      <div>
        <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px', letterSpacing: '-0.02em' }}>
          {value}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {subtext}
          </span>
          {badgeText && (
            <span className={`badge ${styles.badgeClass}`} style={{ fontSize: '10px', padding: '2px 8px' }}>
              {badgeText}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
