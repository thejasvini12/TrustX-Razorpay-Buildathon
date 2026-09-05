import React from 'react';
import { FraudSpikeResponse } from '../../types/api';
import { ShieldCheck, AlertTriangle, ShieldAlert, Store } from 'lucide-react';

interface SpikeResultCardProps {
  result: FraudSpikeResponse;
  isStale?: boolean;
}

export const SpikeResultCard: React.FC<SpikeResultCardProps> = ({ result, isStale = false }) => {
  const { merchant_id, spike_score, spike_probability, spike_level, spike_prediction, recommended_action } = result;

  const getBadgeClass = (level: string) => {
    switch (level) {
      case 'LOW':
        return 'badge-low';
      case 'MEDIUM':
        return 'badge-medium';
      case 'HIGH':
        return 'badge-high';
      default:
        return 'badge-cyan';
    }
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'ALLOW_STANDARD_OPERATIONS':
        return {
          label: 'Allow Standard Operations',
          sub: 'Velocity and fraud-rate changes within normal baseline bounds.',
          icon: ShieldCheck,
          color: 'var(--risk-low)',
          bg: 'var(--risk-low-bg)',
        };
      case 'FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR':
        return {
          label: 'Flag for Velocity Audit & Monitor',
          sub: 'Elevated rate delta or short-window surge requires enhanced telemetry monitoring.',
          icon: AlertTriangle,
          color: 'var(--risk-medium)',
          bg: 'var(--risk-medium-bg)',
        };
      case 'ENABLE_STRICT_RATE_LIMITS_AND_2FA':
        return {
          label: 'Enable Strict Rate Limits & 2FA',
          sub: 'High-severity velocity surge; enforce step-up challenge and throttle checkout volume.',
          icon: ShieldAlert,
          color: 'var(--risk-high)',
          bg: 'var(--risk-high-bg)',
        };
      default:
        return {
          label: action,
          sub: 'Operational defense action.',
          icon: ShieldCheck,
          color: 'var(--accent-cyan)',
          bg: 'var(--accent-cyan-bg)',
        };
    }
  };

  const actionInfo = getActionBadge(recommended_action);
  const ActionIcon = actionInfo.icon;
  const clampedScore = Math.max(0, Math.min(100, spike_score));

  return (
    <div
      className="card"
      style={{
        position: 'relative',
        opacity: isStale ? 0.75 : 1,
        border: `1px solid ${spike_level === 'HIGH' ? 'var(--risk-high-border)' : spike_level === 'MEDIUM' ? 'var(--risk-medium-border)' : 'var(--border-subtle)'}`,
      }}
    >
      {isStale && (
        <div
          style={{
            position: 'absolute',
            top: '12px',
            right: '16px',
            padding: '2px 8px',
            backgroundColor: 'rgba(245, 158, 11, 0.2)',
            color: 'var(--risk-medium)',
            border: '1px solid var(--risk-medium-border)',
            borderRadius: 'var(--radius-pill)',
            fontSize: '10px',
            fontWeight: '600',
          }}
        >
          Parameters Modified • Re-run Assessment
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              padding: '6px',
              backgroundColor: 'var(--bg-app)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-secondary)',
            }}
          >
            <Store size={16} />
          </div>
          <div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Assessed Merchant Identifier
            </div>
            <div className="font-mono" style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>
              {merchant_id || 'MERCH_UNKNOWN'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className={`badge ${getBadgeClass(spike_level)}`} style={{ fontSize: '12px', padding: '4px 12px' }}>
            {spike_level} SPIKE SEVERITY
          </span>
          <span
            style={{
              fontSize: '11px',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: spike_prediction === 1 ? 'var(--risk-high-bg)' : 'var(--risk-low-bg)',
              color: spike_prediction === 1 ? 'var(--risk-high)' : 'var(--risk-low)',
              fontWeight: '600',
            }}
          >
            Prediction: {spike_prediction === 1 ? 'SPIKE DETECTED' : 'NORMAL TRAFFIC'}
          </span>
        </div>
      </div>

      {/* Primary 3-Metric Summary Strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '14px',
          marginBottom: '20px',
        }}
      >
        {/* Spike Score */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Fraud Spike Score
          </div>
          <div className="font-mono" style={{ fontSize: '36px', fontWeight: '800', color: 'var(--text-primary)', lineHeight: '1.1', margin: '4px 0' }}>
            {spike_score}
            <span style={{ fontSize: '16px', color: 'var(--text-muted)', fontWeight: '500' }}>/100</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Policy-calibrated temporal risk index
          </div>
        </div>

        {/* Spike Probability */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Posterior Probability
          </div>
          <div className="font-mono" style={{ fontSize: '36px', fontWeight: '800', color: 'var(--accent-cyan)', lineHeight: '1.1', margin: '4px 0' }}>
            {(spike_probability * 100).toFixed(1)}%
          </div>
          <div className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            P(Spike) = {spike_probability.toFixed(4)}
          </div>
        </div>

        {/* Recommended Defense Action */}
        <div
          style={{
            padding: '16px',
            backgroundColor: actionInfo.bg,
            border: `1px solid ${actionInfo.color}40`,
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '10.5px', color: actionInfo.color, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ActionIcon size={14} />
            <span>System Recommended Action</span>
          </div>
          <div style={{ fontSize: '15px', fontWeight: '800', color: actionInfo.color, marginTop: '6px', lineHeight: '1.3' }}>
            {actionInfo.label}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {actionInfo.sub}
          </div>
        </div>
      </div>

      {/* Severity Progress Bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div
          style={{
            position: 'relative',
            height: '14px',
            backgroundColor: 'var(--bg-app)',
            borderRadius: 'var(--radius-pill)',
            border: '1px solid var(--border-subtle)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              bottom: 0,
              width: `${clampedScore}%`,
              background: 'linear-gradient(90deg, rgba(16, 185, 129, 0.7) 0%, rgba(245, 158, 11, 0.8) 50%, rgba(244, 63, 94, 0.9) 100%)',
              transition: 'width 600ms ease',
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-muted)' }}>
          <span style={{ color: 'var(--risk-low)' }}>0 LOW (Stable)</span>
          <span style={{ color: 'var(--risk-medium)' }}>30 MEDIUM (Elevated)</span>
          <span style={{ color: 'var(--risk-high)' }}>70 HIGH (Severe Surge)</span>
          <span>100</span>
        </div>
      </div>
    </div>
  );
};
