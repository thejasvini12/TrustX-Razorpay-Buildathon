import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useRiskFeed } from '../context/RiskFeedContext';
import { riskApi } from '../services/api';
import { RazorpayWebhookStatusResponse } from '../types/api';
import { RiskEvent } from '../types/riskFeed';
import { RiskEventCard } from '../components/operations/RiskEventCard';
import { InvestigationDrawer } from '../components/operations/InvestigationDrawer';
import { RazorpayWebhookBar } from '../components/operations/RazorpayWebhookBar';
import {
  Activity,
  Flame,
  Search,
  Trash2,
} from 'lucide-react';

export const RiskOperationsPage: React.FC = () => {
  const { events, clearFeed, selectedEvent, setSelectedEvent, mergeEvents, updateEventStatus, clearedAt } = useRiskFeed();

  const [webhookStatus, setWebhookStatus] = useState<RazorpayWebhookStatusResponse | null>(null);
  const [webhookLoading, setWebhookLoading] = useState<boolean>(false);
  const [webhookError, setWebhookError] = useState<string | null>(null);
  const [lastPolled, setLastPolled] = useState<Date | null>(null);

  // Case Filter States
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'INVESTIGATING' | 'RESOLVED'>('ALL');
  const [engineFilter, setEngineFilter] = useState<'ALL' | 'FRAUD_SPIKE' | 'ACCOUNT_RISK' | 'RETURN_RISK' | 'ABUSE_RING'>('ALL');
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'HIGH_CRITICAL' | 'MEDIUM' | 'LOW'>('ALL');

  const openCount = events.filter((e) => (e.status || 'OPEN') === 'OPEN').length;
  const investigatingCount = events.filter((e) => e.status === 'INVESTIGATING').length;
  const resolvedCount = events.filter((e) => e.status === 'RESOLVED').length;

  const filteredEvents = events.filter((e) => {
    const currentStatus = e.status || 'OPEN';
    if (statusFilter !== 'ALL' && currentStatus !== statusFilter) return false;
    if (engineFilter !== 'ALL' && e.engine !== engineFilter) return false;
    if (severityFilter === 'HIGH_CRITICAL' && e.severity !== 'HIGH' && e.severity !== 'CRITICAL') return false;
    if (severityFilter === 'MEDIUM' && e.severity !== 'MEDIUM') return false;
    if (severityFilter === 'LOW' && e.severity !== 'LOW') return false;
    return true;
  });

  const fetchWebhookData = useCallback(async () => {
    try {
      setWebhookLoading(true);
      const [statusRes, eventsRes] = await Promise.all([
        riskApi.getRazorpayWebhookStatus(),
        riskApi.getRazorpayRecentEvents(),
      ]);

      setWebhookStatus(statusRes);
      setWebhookError(null);
      setLastPolled(new Date());

      if (Array.isArray(eventsRes) && eventsRes.length > 0) {
        const mappedEvents: RiskEvent[] = eventsRes.map((item) => ({
          id: item.id,
          timestamp: new Date(item.timestamp),
          engine: (item.engine as any) || 'FRAUD_SPIKE',
          source: (item.source as any) || 'LIVE_ASSESSMENT',
          title: item.title,
          entityId: item.entityId,
          entityType: (item.entityType as any) || 'MERCHANT',
          severity: item.severity,
          score: item.score,
          decision: item.decision,
          rawMl: item.rawMl || {},
          evidence: item.evidence || [],
          telemetry: item.telemetry || {},
          policy: item.policy,
          attribution: item.attribution,
          returnRisk: item.returnRisk,
        }));
        mergeEvents(mappedEvents);
      }
    } catch (err: any) {
      setWebhookError(err?.message || 'Unable to connect to Razorpay webhook pipeline');
    } finally {
      setWebhookLoading(false);
    }
  }, [mergeEvents]);

  // Initial fetch and 5-second polling interval
  useEffect(() => {
    fetchWebhookData();
    const interval = setInterval(fetchWebhookData, 5000);
    return () => clearInterval(interval);
  }, [fetchWebhookData]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* 1. Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1
              style={{
                fontSize: '24px',
                fontWeight: '800',
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em',
              }}
            >
              Risk Operations
            </h1>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11px',
                fontWeight: '600',
                padding: '3px 9px',
                borderRadius: 'var(--radius-pill)',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                color: 'var(--risk-low)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
              }}
            >
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--risk-low)' }} />
              Risk Engine Online
            </span>
          </div>
          <p
            style={{
              fontSize: '14px',
              color: 'var(--text-secondary)',
              marginTop: '4px',
              maxWidth: '680px',
            }}
          >
            Monitor risk signals, investigate suspicious activity, and review operational decisions.
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {events.length > 0 && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={clearFeed}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px' }}
            >
              <Trash2 size={13} />
              <span>Clear Feed</span>
            </button>
          )}

          <Link
            to="/simulator"
            className="btn btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px' }}
          >
            <Flame size={14} />
            <span>Launch Simulator</span>
          </Link>
        </div>
      </div>

      {/* 2. Live Razorpay Webhook Ingestion Telemetry */}
      <RazorpayWebhookBar
        status={webhookStatus}
        loading={webhookLoading}
        error={webhookError}
        lastPolled={lastPolled}
        onRefresh={fetchWebhookData}
      />

      {/* 3. Live Risk Feed Container */}
      <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Live Risk Feed & Case Management
            </h2>
            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Real-time feed of live API assessments and simulated attack evaluations. Manage analyst workflow directly.
            </p>
          </div>

          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Showing {filteredEvents.length} of {events.length} {events.length === 1 ? 'Event' : 'Events'}
          </span>
        </div>

        {/* Case Lifecycle Filter Toolbar */}
        {events.length > 0 && (
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--bg-app)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            {/* Status Filter Chips */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginRight: '4px' }}>
                Case Status:
              </span>
              <button
                type="button"
                className={`btn ${statusFilter === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setStatusFilter('ALL')}
                style={{ padding: '4px 10px', fontSize: '11.5px', borderRadius: 'var(--radius-pill)' }}
              >
                All ({events.length})
              </button>
              <button
                type="button"
                className={`btn ${statusFilter === 'OPEN' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setStatusFilter('OPEN')}
                style={{
                  padding: '4px 10px',
                  fontSize: '11.5px',
                  borderRadius: 'var(--radius-pill)',
                  color: statusFilter === 'OPEN' ? undefined : 'var(--accent-cyan)',
                }}
              >
                Open ({openCount})
              </button>
              <button
                type="button"
                className={`btn ${statusFilter === 'INVESTIGATING' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setStatusFilter('INVESTIGATING')}
                style={{
                  padding: '4px 10px',
                  fontSize: '11.5px',
                  borderRadius: 'var(--radius-pill)',
                  color: statusFilter === 'INVESTIGATING' ? undefined : 'var(--risk-critical)',
                }}
              >
                Investigating ({investigatingCount})
              </button>
              <button
                type="button"
                className={`btn ${statusFilter === 'RESOLVED' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setStatusFilter('RESOLVED')}
                style={{
                  padding: '4px 10px',
                  fontSize: '11.5px',
                  borderRadius: 'var(--radius-pill)',
                  color: statusFilter === 'RESOLVED' ? undefined : 'var(--risk-low)',
                }}
              >
                Resolved ({resolvedCount})
              </button>
            </div>

            {/* Engine & Severity Filters */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Engine:</span>
                <select
                  value={engineFilter}
                  onChange={(e) => setEngineFilter(e.target.value as any)}
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '3px 8px',
                    fontSize: '11.5px',
                  }}
                >
                  <option value="ALL">All Engines</option>
                  <option value="FRAUD_SPIKE">Fraud Spike</option>
                  <option value="ACCOUNT_RISK">Account Risk</option>
                  <option value="RETURN_RISK">Return Risk</option>
                  <option value="ABUSE_RING">Abuse Ring</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Severity:</span>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value as any)}
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '3px 8px',
                    fontSize: '11.5px',
                  }}
                >
                  <option value="ALL">All Severities</option>
                  <option value="HIGH_CRITICAL">High & Critical</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Empty State when no events exist in session */}
        {events.length === 0 ? (
          <div
            style={{
              padding: '48px 24px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--bg-app)',
              border: '1px dashed var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              gap: '14px',
            }}
          >
            <div
              style={{
                padding: '12px',
                borderRadius: '50%',
                backgroundColor: 'rgba(56, 189, 248, 0.08)',
                color: 'var(--accent-cyan)',
              }}
            >
              <Activity size={26} />
            </div>
            <div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
                {clearedAt ? 'Feed Cleared — Monitoring Active' : 'Waiting for risk events'}
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '480px', marginTop: '4px', lineHeight: '1.45' }}>
                {clearedAt
                  ? `Feed cleared at ${new Date(clearedAt).toLocaleTimeString()}. Polling is active and listening for new live Razorpay webhook and risk engine events.`
                  : 'Run a simulator scenario or submit a live transaction to generate risk evaluation activity.'}
              </p>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
              <Link to="/simulator" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px' }}>
                <Flame size={14} />
                <span>Launch Simulator</span>
              </Link>
              <Link to="/account-risk" className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px' }}>
                <Search size={14} />
                <span>Assess Account</span>
              </Link>
            </div>
          </div>
        ) : filteredEvents.length === 0 ? (
          /* Filter Empty State */
          <div
            style={{
              padding: '36px 20px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--bg-app)',
              border: '1px dashed var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              gap: '10px',
            }}
          >
            <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-secondary)' }}>
              No risk cases match the current filter selection.
            </span>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setStatusFilter('ALL');
                setEngineFilter('ALL');
                setSeverityFilter('ALL');
              }}
              style={{ fontSize: '12px', padding: '5px 12px' }}
            >
              Reset Filters
            </button>
          </div>
        ) : (
          /* Live Events List */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {filteredEvents.map((evt) => (
              <RiskEventCard
                key={evt.id}
                event={evt}
                onInvestigate={(selected) => setSelectedEvent(selected)}
                onStatusChange={updateEventStatus}
              />
            ))}
          </div>
        )}
      </div>

      {/* 3. Detailed Investigation Drawer */}
      <InvestigationDrawer
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />
    </div>
  );
};

export default RiskOperationsPage;
