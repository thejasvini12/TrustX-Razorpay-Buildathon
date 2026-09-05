import React from 'react';
import { Layers } from 'lucide-react';

interface PersistencePanelProps {
  consecutiveWindows?: number;
  escalationTriggered?: boolean;
}

export const PersistencePanel: React.FC<PersistencePanelProps> = ({
  consecutiveWindows = 0,
  escalationTriggered = false,
}) => {
  return (
    <div
      className="card"
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        border: escalationTriggered ? '1px solid var(--risk-critical-border)' : '1px solid var(--border-subtle)',
      }}
    >
      <div>
        <div className="card-header" style={{ marginBottom: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Layers size={16} color={escalationTriggered ? 'var(--risk-critical)' : 'var(--accent-cyan)'} />
              <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                P3: Multi-Window Persistence
              </h4>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Stateful rolling window tracker escalating severity when $\ge 2$ consecutive spikes occur.
            </p>
          </div>

          <span className={`badge ${escalationTriggered ? 'badge-critical' : 'badge-cyan'}`} style={{ fontSize: '10px' }}>
            {escalationTriggered ? 'P3 Escalated' : 'Standard'}
          </span>
        </div>

        <div
          style={{
            padding: '12px',
            backgroundColor: 'var(--bg-app)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '12px',
          }}
        >
          <div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Consecutive Anomaly Windows
            </span>
            <div className="font-mono" style={{ fontSize: '20px', fontWeight: '800', color: consecutiveWindows >= 2 ? 'var(--risk-critical)' : 'var(--text-primary)', marginTop: '2px' }}>
              {consecutiveWindows}
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '500' }}> Windows</span>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Escalation Status
            </span>
            <div style={{ fontSize: '11px', fontWeight: '700', color: escalationTriggered ? 'var(--risk-critical)' : 'var(--risk-low)', marginTop: '4px' }}>
              {escalationTriggered ? 'ACTIVE (P3)' : 'INACTIVE'}
            </div>
          </div>
        </div>

        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
          {consecutiveWindows >= 2 ? (
            <span style={{ color: 'var(--risk-critical)' }}>
              Repeated anomaly windows detected across sequential audits for this merchant ID.
            </span>
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>
              No persistent multi-window anomaly pattern active.
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
