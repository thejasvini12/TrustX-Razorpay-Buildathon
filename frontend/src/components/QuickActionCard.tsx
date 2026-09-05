import React from 'react';
import { NavLink } from 'react-router-dom';
import { LucideIcon, ArrowUpRight } from 'lucide-react';

export interface QuickActionItem {
  title: string;
  description: string;
  route: string;
  icon: LucideIcon;
  badge?: string;
  color?: string;
}

export interface QuickActionCardProps {
  actions: QuickActionItem[];
}

export const QuickActionCard: React.FC<QuickActionCardProps> = ({ actions }) => {
  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '14px' }}>
        <div>
          <h3 className="card-title">Quick Investigation Actions</h3>
          <p className="card-description">
            Jump directly into active risk assessment, anomaly investigation, or simulation workflows.
          </p>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '12px',
        }}
      >
        {actions.map((act) => {
          const Icon = act.icon;
          return (
            <NavLink
              key={act.title}
              to={act.route}
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                padding: '16px',
                backgroundColor: 'var(--bg-app)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                transition: 'all var(--transition-fast)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-muted)';
                e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
                e.currentTarget.style.backgroundColor = 'var(--bg-app)';
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div
                    style={{
                      padding: '6px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'var(--bg-card)',
                      color: act.color || 'var(--accent-cyan)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Icon size={16} />
                  </div>
                  <ArrowUpRight size={14} color="var(--text-muted)" />
                </div>
                <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  {act.title}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  {act.description}
                </div>
              </div>
            </NavLink>
          );
        })}
      </div>
    </div>
  );
};
