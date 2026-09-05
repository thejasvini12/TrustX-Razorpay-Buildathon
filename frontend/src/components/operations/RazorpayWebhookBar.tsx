import React from 'react';
import { RazorpayWebhookStatusResponse } from '../../types/api';
import {
  Webhook,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Radio,
  FileCheck2,
  Copy,
  Slash,
} from 'lucide-react';

interface RazorpayWebhookBarProps {
  status: RazorpayWebhookStatusResponse | null;
  loading: boolean;
  error: string | null;
  lastPolled: Date | null;
  onRefresh: () => void;
}

export const RazorpayWebhookBar: React.FC<RazorpayWebhookBarProps> = ({
  status,
  loading,
  error,
  lastPolled,
  onRefresh,
}) => {
  const isEnabled = Boolean(status?.enabled);

  return (
    <div
      className="card"
      style={{
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        backgroundColor: 'var(--bg-card)',
        border: error
          ? '1px solid var(--risk-medium-border)'
          : isEnabled
          ? '1px solid rgba(56, 189, 248, 0.25)'
          : '1px solid var(--border-subtle)',
      }}
    >
      {/* Header Row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              padding: '8px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: isEnabled ? 'rgba(56, 189, 248, 0.12)' : 'rgba(255, 255, 255, 0.05)',
              color: isEnabled ? 'var(--accent-cyan)' : 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Webhook size={18} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>
                Razorpay Webhook Telemetry
              </h3>

              {/* Status Badge */}
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  fontSize: '11px',
                  fontWeight: '600',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-pill)',
                  backgroundColor: isEnabled ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                  color: isEnabled ? 'var(--risk-low)' : 'var(--risk-high)',
                  border: isEnabled ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
                }}
              >
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: isEnabled ? 'var(--risk-low)' : 'var(--risk-high)',
                  }}
                />
                {isEnabled ? 'Active' : 'Inactive'}
              </span>

              {/* Environment Badge */}
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: '700',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-pill)',
                  backgroundColor: 'rgba(168, 85, 247, 0.14)',
                  color: 'var(--risk-critical)',
                  border: '1px solid rgba(168, 85, 247, 0.35)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                {status?.environment ? `${status.environment} Mode` : 'Test Mode'}
              </span>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Real-time payment lifecycle events feeding Fraud Spike velocity metrics.
            </p>
          </div>
        </div>

        {/* Polling Info & Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              color: 'var(--text-muted)',
            }}
          >
            <Radio size={12} color="var(--accent-cyan)" />
            <span>Polling (5s)</span>
            {lastPolled && (
              <span style={{ color: 'var(--text-secondary)' }}>
                • {lastPolled.toLocaleTimeString()}
              </span>
            )}
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={onRefresh}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 10px',
              fontSize: '12px',
            }}
            title="Refresh webhook status and events"
          >
            <RefreshCw size={12} className={loading ? 'spin' : ''} />
            <span>{loading ? 'Refreshing...' : 'Poll Now'}</span>
          </button>
        </div>
      </div>

      {/* Non-Blocking Error State */}
      {error && (
        <div
          style={{
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--risk-medium-bg)',
            border: '1px solid var(--risk-medium-border)',
            color: 'var(--risk-medium)',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertCircle size={14} />
          <span>Webhook telemetry offline: {error}. Operations dashboard is still active.</span>
        </div>
      )}

      {/* Telemetry Metrics Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '10px',
        }}
      >
        {/* Metric 1: Events Received */}
        <div
          style={{
            padding: '10px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ fontSize: '10.5px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            Received
          </div>
          <div
            className="font-mono"
            style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}
          >
            {status?.received ?? 0}
          </div>
        </div>

        {/* Metric 2: Events Accepted */}
        <div
          style={{
            padding: '10px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10.5px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            <CheckCircle2 size={11} color="var(--risk-low)" />
            <span>Accepted</span>
          </div>
          <div
            className="font-mono"
            style={{ fontSize: '18px', fontWeight: '800', color: 'var(--risk-low)', marginTop: '2px' }}
          >
            {status?.accepted ?? 0}
          </div>
        </div>

        {/* Metric 3: Events Ignored */}
        <div
          style={{
            padding: '10px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10.5px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            <Slash size={11} color="var(--text-muted)" />
            <span>Ignored</span>
          </div>
          <div
            className="font-mono"
            style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-secondary)', marginTop: '2px' }}
          >
            {status?.ignored ?? 0}
          </div>
        </div>

        {/* Metric 4: Duplicate Events */}
        <div
          style={{
            padding: '10px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10.5px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            <Copy size={11} color="var(--risk-medium)" />
            <span>Duplicates</span>
          </div>
          <div
            className="font-mono"
            style={{ fontSize: '18px', fontWeight: '800', color: 'var(--risk-medium)', marginTop: '2px' }}
          >
            {status?.duplicates ?? 0}
          </div>
        </div>

        {/* Metric 5: Recent Risk Events Count */}
        <div
          style={{
            padding: '10px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10.5px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            <FileCheck2 size={11} color="var(--accent-cyan)" />
            <span>Risk Feed Events</span>
          </div>
          <div
            className="font-mono"
            style={{ fontSize: '18px', fontWeight: '800', color: 'var(--accent-cyan)', marginTop: '2px' }}
          >
            {status?.recent_risk_events_count ?? 0}
          </div>
        </div>

        {/* Metric 6: Latest Event Type & Timestamp */}
        <div
          style={{
            padding: '10px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            gridColumn: 'span 2',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10.5px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            <Clock size={11} />
            <span>Latest Event</span>
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: '8px',
              marginTop: '4px',
              flexWrap: 'wrap',
            }}
          >
            <span
              className="font-mono"
              style={{
                fontSize: '12.5px',
                fontWeight: '700',
                color: status?.latest_event_type ? 'var(--text-primary)' : 'var(--text-muted)',
              }}
            >
              {status?.latest_event_type || 'None received yet'}
            </span>
            {status?.latest_event_timestamp && (
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                ({new Date(status.latest_event_timestamp).toLocaleTimeString()})
              </span>
            )}
            {status?.latest_merchant_id && (
              <span
                style={{
                  fontSize: '10px',
                  padding: '1px 5px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  color: 'var(--text-muted)',
                }}
              >
                {status.latest_merchant_id}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
