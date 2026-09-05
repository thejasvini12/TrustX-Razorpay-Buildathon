import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  ShieldAlert,
  LayoutDashboard,
  Activity,
  UserCheck,
  TrendingUp,
  Network,
  Zap,
  Cpu,
} from 'lucide-react';

const NAV_ITEMS = [
  {
    path: '/',
    label: 'Overview',
    icon: LayoutDashboard,
    badge: 'Hub',
  },
  {
    path: '/risk-operations',
    label: 'Risk Operations',
    icon: Activity,
    badge: 'Live Feed',
  },
  {
    path: '/account-risk',
    label: 'Account Risk',
    icon: UserCheck,
    badge: 'RF + Policy',
  },
  {
    path: '/fraud-spike',
    label: 'Fraud Spike',
    icon: TrendingUp,
    badge: 'P5 5-Min',
  },
  {
    path: '/abuse-ring',
    label: 'Abuse Ring',
    icon: Network,
    badge: 'Sentinel',
  },
  {
    path: '/simulator',
    label: 'Attack Simulator',
    icon: Zap,
    badge: 'Studio',
  },
];

export const Sidebar: React.FC = () => {
  return (
    <aside style={{
      width: '260px',
      height: '100vh',
      backgroundColor: 'var(--bg-sidebar)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
    }}>
      {/* Brand Header */}
      <div style={{
        padding: '24px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
      }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--accent-cyan-bg)',
          border: '1px solid var(--accent-cyan-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--accent-cyan)',
        }}>
          <ShieldAlert size={20} />
        </div>
        <div>
          <div style={{ fontSize: '15px', fontWeight: '800', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            TrustX
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '500' }}>
            Risk & Abuse Defense
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav style={{ flex: 1, padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{
          fontSize: '10px',
          fontWeight: '700',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--text-muted)',
          padding: '8px 12px 4px 12px',
        }}>
          Operations
        </div>

        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 12px',
                borderRadius: 'var(--radius-md)',
                textDecoration: 'none',
                fontSize: '13px',
                fontWeight: isActive ? '600' : '500',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--accent-cyan-bg)' : 'transparent',
                border: isActive ? '1px solid var(--accent-cyan-border)' : '1px solid transparent',
                transition: 'all var(--transition-fast)',
              })}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Icon size={16} />
                <span>{item.label}</span>
              </div>
              <span style={{
                fontSize: '10px',
                padding: '1px 6px',
                borderRadius: 'var(--radius-pill)',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                color: 'var(--text-muted)',
                fontWeight: '600',
              }}>
                {item.badge}
              </span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer System Status */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid var(--border-subtle)',
        backgroundColor: 'rgba(0, 0, 0, 0.2)',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
      }}>
        <Cpu size={16} color="var(--accent-cyan)" />
        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
          <div><strong style={{ color: 'var(--text-primary)' }}>4 Risk Engines</strong></div>
          <div style={{ color: 'var(--text-muted)' }}>v1.0.0 • Operational</div>
        </div>
      </div>
    </aside>
  );
};
