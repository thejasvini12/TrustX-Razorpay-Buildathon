import React from 'react';
import { useHealth } from '../hooks/useHealth';
import { RefreshCw, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  title?: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({
  title = 'Operations Center',
  subtitle = 'Coordinated Merchant Abuse & Defense Intelligence',
}) => {
  const { health, loading, error, lastChecked, refresh } = useHealth(10000);

  const isOnline = health !== null && !error;

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '16px 32px',
      backgroundColor: 'var(--bg-header)',
      borderBottom: '1px solid var(--border-subtle)',
      minHeight: '70px',
    }}>
      <div>
        <h1 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
          {title}
        </h1>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
          {subtitle}
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Backend Health Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '6px 14px',
          backgroundColor: isOnline ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
          border: `1px solid ${isOnline ? 'var(--risk-low-border)' : 'rgba(239, 68, 68, 0.3)'}`,
          borderRadius: 'var(--radius-pill)',
        }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: isOnline ? 'var(--status-online)' : 'var(--status-offline)',
            boxShadow: isOnline ? '0 0 8px var(--status-online)' : '0 0 8px var(--status-offline)',
          }} />
          
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '11px', fontWeight: '600', color: isOnline ? 'var(--risk-low)' : 'var(--status-offline)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {loading && !health ? 'Connecting...' : isOnline ? 'Risk Engines Online' : 'Risk Engines Offline'}
            </span>
            {isOnline && health && (
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                v{health.version} • Operational
              </span>
            )}
          </div>

          <button
            onClick={() => refresh()}
            disabled={loading}
            title={lastChecked ? `Last checked: ${lastChecked.toLocaleTimeString()}` : 'Check connection'}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
              padding: '4px',
              marginLeft: '4px',
              cursor: 'pointer',
              opacity: loading ? 0.5 : 1,
            }}
          >
            <RefreshCw size={12} className={loading ? 'spin' : ''} />
          </button>
        </div>

        {/* Defense Mode Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          backgroundColor: 'var(--bg-elevated)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-pill)',
          fontSize: '11px',
          color: 'var(--text-secondary)',
          fontWeight: '500',
        }}>
          <ShieldCheck size={14} color="var(--accent-cyan)" />
          <span>Defense-Only Active</span>
        </div>
      </div>
    </header>
  );
};
