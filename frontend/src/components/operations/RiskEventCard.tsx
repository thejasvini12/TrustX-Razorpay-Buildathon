import React from 'react';
import { RiskEvent, EventSeverity, RiskEngineType, EventSourceType, CaseStatus } from '../../types/riskFeed';
import { UserCheck, ShoppingBag, TrendingUp, Network, ArrowRight, Clock, CheckCircle2, Play, RotateCcw, Shield } from 'lucide-react';

interface RiskEventCardProps {
  event: RiskEvent;
  onInvestigate: (event: RiskEvent) => void;
  onStatusChange?: (id: string, status: CaseStatus, operatorAction?: string) => void;
}

const ENGINE_CONFIG: Record<RiskEngineType, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  ACCOUNT_RISK: {
    label: 'Account Risk',
    icon: <UserCheck size={16} />,
    color: 'var(--accent-cyan)',
    bg: 'rgba(56, 189, 248, 0.12)',
  },
  RETURN_RISK: {
    label: 'Return Risk',
    icon: <ShoppingBag size={16} />,
    color: 'var(--risk-low)',
    bg: 'rgba(16, 185, 129, 0.12)',
  },
  FRAUD_SPIKE: {
    label: 'Fraud Spike',
    icon: <TrendingUp size={16} />,
    color: 'var(--risk-medium)',
    bg: 'rgba(245, 158, 11, 0.12)',
  },
  ABUSE_RING: {
    label: 'Abuse Ring',
    icon: <Network size={16} />,
    color: 'var(--risk-critical)',
    bg: 'rgba(168, 85, 247, 0.14)',
  },
};

const SEVERITY_BADGES: Record<EventSeverity, string> = {
  LOW: 'badge-green',
  MEDIUM: 'badge-amber',
  HIGH: 'badge-rose',
  CRITICAL: 'badge-purple',
};

const SOURCE_LABELS: Record<EventSourceType, { label: string; bg: string; color: string }> = {
  LIVE_ASSESSMENT: { label: 'LIVE / API ASSESSMENT', bg: 'rgba(56, 189, 248, 0.1)', color: 'var(--accent-cyan)' },
  SIMULATION: { label: 'SIMULATION', bg: 'rgba(99, 102, 241, 0.12)', color: 'var(--accent-indigo)' },
  MANUAL_INVESTIGATION: { label: 'MANUAL INVESTIGATION', bg: 'rgba(245, 158, 11, 0.1)', color: 'var(--risk-medium)' },
};

export const RiskEventCard: React.FC<RiskEventCardProps> = ({ event, onInvestigate, onStatusChange }) => {
  const engineInfo = ENGINE_CONFIG[event.engine];
  const severityBadge = SEVERITY_BADGES[event.severity];
  const sourceInfo = SOURCE_LABELS[event.source];
  const currentStatus: CaseStatus = event.status || 'OPEN';

  const decisionColor =
    event.decision.includes('BLOCK') || event.decision.includes('STRICT') || event.decision.includes('CHALLENGE')
      ? 'var(--risk-high)'
      : event.decision.includes('REVIEW') || event.decision.includes('FLAG') || event.decision.includes('MONITOR')
      ? 'var(--risk-medium)'
      : 'var(--risk-low)';

  const handleStartInvestigating = (e: React.MouseEvent) => {
    e.stopPropagation();
    onStatusChange?.(event.id, 'INVESTIGATING', 'Case Investigation Commenced');
  };

  const handleResolve = (e: React.MouseEvent) => {
    e.stopPropagation();
    onStatusChange?.(event.id, 'RESOLVED', 'Risk Mitigated / Reviewed by Operator');
  };

  const handleReopen = (e: React.MouseEvent) => {
    e.stopPropagation();
    onStatusChange?.(event.id, 'OPEN', 'Case Reopened for Review');
  };

  return (
    <div
      className="card"
      style={{
        padding: '16px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        borderLeft: `3px solid ${
          event.severity === 'CRITICAL'
            ? 'var(--risk-critical)'
            : event.severity === 'HIGH'
            ? 'var(--risk-high)'
            : event.severity === 'MEDIUM'
            ? 'var(--risk-medium)'
            : 'var(--risk-low)'
        }`,
      }}
    >
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <div
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: engineInfo.bg,
              color: engineInfo.color,
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {engineInfo.icon}
          </div>
          <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
            {engineInfo.label}
          </span>
          <span
            style={{
              fontSize: '10px',
              fontWeight: '700',
              padding: '2px 6px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: sourceInfo.bg,
              color: sourceInfo.color,
            }}
          >
            {sourceInfo.label}
          </span>

          {/* Case Status Badge */}
          <span
            style={{
              fontSize: '10px',
              fontWeight: '700',
              padding: '2px 7px',
              borderRadius: 'var(--radius-pill)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              backgroundColor:
                currentStatus === 'RESOLVED'
                  ? 'rgba(16, 185, 129, 0.12)'
                  : currentStatus === 'INVESTIGATING'
                  ? 'rgba(168, 85, 247, 0.14)'
                  : 'rgba(56, 189, 248, 0.12)',
              color:
                currentStatus === 'RESOLVED'
                  ? 'var(--risk-low)'
                  : currentStatus === 'INVESTIGATING'
                  ? 'var(--risk-critical)'
                  : 'var(--accent-cyan)',
              border:
                currentStatus === 'RESOLVED'
                  ? '1px solid rgba(16, 185, 129, 0.3)'
                  : currentStatus === 'INVESTIGATING'
                  ? '1px solid rgba(168, 85, 247, 0.3)'
                  : '1px solid rgba(56, 189, 248, 0.3)',
            }}
          >
            <span
              style={{
                width: '5px',
                height: '5px',
                borderRadius: '50%',
                backgroundColor:
                  currentStatus === 'RESOLVED'
                    ? 'var(--risk-low)'
                    : currentStatus === 'INVESTIGATING'
                    ? 'var(--risk-critical)'
                    : 'var(--accent-cyan)',
              }}
            />
            {currentStatus}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className={`badge ${severityBadge}`} style={{ fontSize: '10.5px' }}>
            {event.severity}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11.5px', color: 'var(--text-muted)' }}>
            <Clock size={12} />
            <span>{event.timestamp.toLocaleTimeString()}</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Title & Entity + Score & System Recommended Action */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto auto',
          alignItems: 'center',
          gap: '16px',
          backgroundColor: 'var(--bg-app)',
          padding: '12px 14px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
          <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>
            {event.title}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono, monospace' }}>
            Entity: <strong style={{ color: 'var(--accent-cyan)' }}>{event.entityId}</strong>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
          <span style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Risk Score
          </span>
          <span style={{ fontSize: '18px', fontWeight: '800', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-primary)' }}>
            {event.score} <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>/ 100</span>
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
          <span style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            System Recommended Action
          </span>
          <span style={{ fontSize: '12px', fontWeight: '700', color: decisionColor }}>
            {event.decision}
          </span>
        </div>
      </div>

      {/* Operator Decision Tag if present */}
      {event.operatorAction && (
        <div
          style={{
            fontSize: '11.5px',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(99, 102, 241, 0.08)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            color: 'var(--accent-cyan)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <Shield size={13} />
          <span>
            <strong>Operator Decision — Process Local:</strong> {event.operatorAction}
          </span>
        </div>
      )}

      {/* Footer: Evidence snippets & Status Action Controls + Investigate Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', paddingTop: '4px' }}>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          {event.evidence && event.evidence.length > 0 ? (
            <span>Key Signal: <em>{event.evidence[0]}</em></span>
          ) : (
            <span>Standard baseline observation</span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Quick Case Transition Action */}
          {onStatusChange && (
            <>
              {currentStatus === 'OPEN' && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleStartInvestigating}
                  style={{
                    padding: '4px 9px',
                    fontSize: '11.5px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    color: 'var(--risk-critical)',
                  }}
                  title="Mark case as actively under investigation"
                >
                  <Play size={11} />
                  <span>Start Investigation</span>
                </button>
              )}

              {currentStatus === 'INVESTIGATING' && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleResolve}
                  style={{
                    padding: '4px 9px',
                    fontSize: '11.5px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    color: 'var(--risk-low)',
                  }}
                  title="Resolve case"
                >
                  <CheckCircle2 size={12} />
                  <span>Resolve Case</span>
                </button>
              )}

              {currentStatus === 'RESOLVED' && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleReopen}
                  style={{
                    padding: '4px 9px',
                    fontSize: '11.5px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    color: 'var(--text-muted)',
                  }}
                  title="Reopen case"
                >
                  <RotateCcw size={11} />
                  <span>Reopen</span>
                </button>
              )}
            </>
          )}

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onInvestigate(event)}
            style={{
              padding: '5px 12px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>Investigate</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>
    </div>
  );
};
