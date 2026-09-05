import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useHealth } from '../hooks/useHealth';
import { useRiskFeed } from '../context/RiskFeedContext';
import { riskApi } from '../services/api';
import { RazorpayWebhookStatusResponse } from '../types/api';
import {
  UserCheck,
  ShoppingBag,
  TrendingUp,
  Network,
  RefreshCw,
  ArrowRight,
  Flame,
  Search,
  Webhook,
  CheckCircle2,
  AlertTriangle,
  Info,
} from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const { health, loading, error, latencyMs, refresh } = useHealth(10000);
  const { events, setSelectedEvent } = useRiskFeed();
  const navigate = useNavigate();

  const [webhookStatus, setWebhookStatus] = useState<RazorpayWebhookStatusResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchWebhook = async () => {
      try {
        const res = await riskApi.getRazorpayWebhookStatus();
        if (mounted) setWebhookStatus(res);
      } catch {
        // Non-blocking fallback
      }
    };
    fetchWebhook();
    const timer = setInterval(fetchWebhook, 10000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const isOnline = health !== null && !error;

  const activeEvents = events.filter((e) => (e.status || 'OPEN') !== 'RESOLVED');
  const criticalActiveCount = activeEvents.filter((e) => e.severity === 'CRITICAL').length;
  const highActiveCount = activeEvents.filter((e) => e.severity === 'HIGH').length;
  const mediumActiveCount = activeEvents.filter((e) => e.severity === 'MEDIUM').length;

  const openCount = events.filter((e) => (e.status || 'OPEN') === 'OPEN').length;
  const investigatingCount = events.filter((e) => e.status === 'INVESTIGATING').length;
  const resolvedCount = events.filter((e) => e.status === 'RESOLVED').length;

  const spikeIncidents = events.filter((e) => e.engine === 'FRAUD_SPIKE').length;
  const ringIncidents = events.filter((e) => e.engine === 'ABUSE_RING').length;
  const accountIncidents = events.filter((e) => e.engine === 'ACCOUNT_RISK').length;
  const returnIncidents = events.filter((e) => e.engine === 'RETURN_RISK' || e.returnRisk !== undefined).length;


  // Overall Threat Posture evaluation: deterministic from ACTIVE unresolved cases
  const posture =
    criticalActiveCount > 0
      ? { label: 'CRITICAL THREAT POSTURE', color: 'var(--risk-critical)', bg: 'rgba(168, 85, 247, 0.12)', border: 'rgba(168, 85, 247, 0.35)' }
      : highActiveCount > 0
      ? { label: 'ACTIVE DEFENSE POSTURE', color: 'var(--risk-high)', bg: 'var(--risk-high-bg)', border: 'var(--risk-high-border)' }
      : mediumActiveCount > 0
      ? { label: 'ELEVATED MONITORING', color: 'var(--risk-medium)', bg: 'var(--risk-medium-bg)', border: 'var(--risk-medium-border)' }
      : { label: 'NORMAL MONITORING', color: 'var(--risk-low)', bg: 'var(--risk-low-bg)', border: 'var(--risk-low-border)' };

  // Priority Case Queue: strictly prioritizes HIGH/CRITICAL and OPEN/INVESTIGATING cases
  const priorityCases = [...events]
    .sort((a, b) => {
      // 1. Active vs Resolved
      const aActive = (a.status || 'OPEN') !== 'RESOLVED';
      const bActive = (b.status || 'OPEN') !== 'RESOLVED';
      if (aActive && !bActive) return -1;
      if (!aActive && bActive) return 1;

      // 2. Severity weight
      const severityWeight: Record<string, number> = {
        CRITICAL: 4,
        HIGH: 3,
        MEDIUM: 2,
        LOW: 1,
      };
      const aSev = severityWeight[a.severity] || 0;
      const bSev = severityWeight[b.severity] || 0;
      if (bSev !== aSev) return bSev - aSev;

      // 3. Operational score
      const aScore = typeof a.score === 'number' ? a.score : Number(a.score) || 0;
      const bScore = typeof b.score === 'number' ? b.score : Number(b.score) || 0;
      if (bScore !== aScore) return bScore - aScore;

      // 4. Recency
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    })
    .slice(0, 5);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* SECTION A: Executive Command Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <h1
              style={{
                fontSize: '24px',
                fontWeight: '800',
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em',
              }}
            >
              Executive Command Center
            </h1>

            {/* Posture Badge */}
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11px',
                fontWeight: '700',
                padding: '3px 10px',
                borderRadius: 'var(--radius-pill)',
                backgroundColor: posture.bg,
                color: posture.color,
                border: `1px solid ${posture.border}`,
                letterSpacing: '0.04em',
              }}
            >
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: posture.color }} />
              {posture.label}
            </span>
          </div>

          <p
            style={{
              fontSize: '13.5px',
              color: 'var(--text-secondary)',
              marginTop: '4px',
              maxWidth: '680px',
            }}
          >
            Real-time payment monitoring, account risk analysis, and multi-engine abuse detection.
          </p>
        </div>

        {/* Status Indicators & Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Backend Status */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-pill)',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              fontSize: '12px',
              color: 'var(--text-secondary)',
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: isOnline ? 'var(--risk-low)' : 'var(--risk-high)',
              }}
            />
            <span>{isOnline ? 'Risk Engines Online' : 'Backend Disconnected'}</span>
            {latencyMs !== null && isOnline && (
              <span style={{ color: 'var(--text-muted)' }}>• {latencyMs} ms</span>
            )}
          </div>

          {/* Webhook Ingestion Pill */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '7px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-pill)',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              fontSize: '12px',
              color: 'var(--text-secondary)',
            }}
          >
            <Webhook size={13} color={webhookStatus?.enabled ? 'var(--accent-cyan)' : 'var(--text-muted)'} />
            <span>
              {webhookStatus?.enabled ? 'Razorpay Test Mode' : 'Razorpay Standby'}
            </span>
            {webhookStatus && (
              <span style={{ color: 'var(--accent-cyan)', fontWeight: '600' }}>
                • {webhookStatus.received} tx
              </span>
            )}
          </div>

          <button
            onClick={() => refresh()}
            disabled={loading}
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
            title="Refresh system telemetry"
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* SECTION B: Three Core Operational Questions (Judge Executive Summary) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '16px',
        }}
      >
        {/* Question 1: What is happening? */}
        <div
          className="card"
          style={{
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '14px',
            borderTop: '3px solid var(--accent-cyan)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '700', color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <Info size={14} />
              <span>What is happening?</span>
            </div>
            <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '4px' }}>
              Live Risk Activity
            </h3>
            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.45' }}>
              {events.length > 0
                ? `${events.length} recent risk evaluations across payment activity, account monitoring, and simulations.`
                : 'Recent risk evaluations across payment activity, account monitoring, and simulations.'}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Open Cases</span>
              <div className="font-mono" style={{ fontSize: '16px', fontWeight: '800', color: openCount > 0 ? 'var(--risk-high)' : 'var(--risk-low)' }}>
                {openCount}
              </div>
            </div>
            <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Webhook Intake</span>
              <div className="font-mono" style={{ fontSize: '16px', fontWeight: '800', color: 'var(--accent-cyan)' }}>
                {webhookStatus?.accepted ?? 0} tx
              </div>
            </div>
          </div>
        </div>

        {/* Question 2: Why is it risky? */}
        <div
          className="card"
          style={{
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '14px',
            borderTop: '3px solid var(--risk-medium)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '700', color: 'var(--risk-medium)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <AlertTriangle size={14} />
              <span>Why is it risky?</span>
            </div>
            <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '4px' }}>
              Current Risk Signals
            </h3>
            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.45' }}>
              Fraud spikes, abuse-ring activity, and account-level risk are monitored continuously.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            <span className="badge" style={{ fontSize: '10.5px', backgroundColor: 'var(--bg-app)' }}>
              Fraud Spikes: <strong>{spikeIncidents}</strong>
            </span>
            <span className="badge" style={{ fontSize: '10.5px', backgroundColor: 'var(--bg-app)' }}>
              Abuse Rings: <strong>{ringIncidents}</strong>
            </span>
            <span className="badge" style={{ fontSize: '10.5px', backgroundColor: 'var(--bg-app)' }}>
              Account Risk: <strong>{accountIncidents}</strong>
            </span>
          </div>
        </div>

        {/* Question 3: What should the operator do? */}
        <div
          className="card"
          style={{
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '14px',
            borderTop: '3px solid var(--risk-low)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '700', color: 'var(--risk-low)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <CheckCircle2 size={14} />
              <span>What should the operator do?</span>
            </div>
            <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '4px' }}>
              Recommended Actions
            </h3>
            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.45' }}>
              {activeEvents.length > 0
                ? `${activeEvents.length} active case${activeEvents.length === 1 ? '' : 's'} receive recommended next steps, with higher-risk cases prioritized for review.`
                : 'Active cases receive recommended next steps, with higher-risk cases prioritized for review.'}
            </p>
          </div>

          <Link
            to="/risk-operations"
            className="btn btn-primary"
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12.5px',
              padding: '8px',
            }}
          >
            <span>Open Risk Operations Feed</span>
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>

      {/* SECTION C: Active Critical Cases & Quick Resolution (Top Priority Queue) */}
      <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Risk Case Queue & Recommended Actions
            </h2>
            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Active cases and recommended actions generated by the risk engines.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {openCount} Open • {investigatingCount} In Review • {resolvedCount} Resolved
            </span>
            <Link
              to="/risk-operations"
              className="btn btn-secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', padding: '5px 12px' }}
            >
              <span>View All</span>
              <ArrowRight size={12} />
            </Link>
          </div>
        </div>

        {priorityCases.length === 0 ? (
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
              gap: '12px',
            }}
          >
            <div
              style={{
                padding: '10px',
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                color: 'var(--risk-low)',
              }}
            >
              <CheckCircle2 size={24} />
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text-primary)' }}>
                No active risk events pending review
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '480px', marginTop: '4px', lineHeight: '1.4' }}>
                All transaction streams and merchant accounts are operating within standard parameters. Run an attack scenario in the Simulator to inspect live coordinated abuse.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
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
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {priorityCases.map((evt) => (
              <div
                key={evt.id}
                style={{
                  padding: '14px 16px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--bg-app)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px',
                  borderLeft: `3px solid ${
                    evt.severity === 'CRITICAL'
                      ? 'var(--risk-critical)'
                      : evt.severity === 'HIGH'
                      ? 'var(--risk-high)'
                      : evt.severity === 'MEDIUM'
                      ? 'var(--risk-medium)'
                      : 'var(--risk-low)'
                  }`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <span
                    className={`badge ${
                      evt.severity === 'CRITICAL'
                        ? 'badge-purple'
                        : evt.severity === 'HIGH'
                        ? 'badge-rose'
                        : evt.severity === 'MEDIUM'
                        ? 'badge-amber'
                        : 'badge-green'
                    }`}
                    style={{ fontSize: '10px' }}
                  >
                    {evt.severity}
                  </span>

                  <span
                    style={{
                      fontSize: '10px',
                      padding: '2px 7px',
                      borderRadius: 'var(--radius-pill)',
                      backgroundColor:
                        evt.status === 'RESOLVED'
                          ? 'rgba(16, 185, 129, 0.12)'
                          : evt.status === 'INVESTIGATING'
                          ? 'rgba(168, 85, 247, 0.14)'
                          : 'rgba(56, 189, 248, 0.12)',
                      color:
                        evt.status === 'RESOLVED'
                          ? 'var(--risk-low)'
                          : evt.status === 'INVESTIGATING'
                          ? 'var(--risk-critical)'
                          : 'var(--accent-cyan)',
                    }}
                  >
                    {evt.status || 'OPEN'}
                  </span>

                  <div>
                    <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--text-primary)' }}>
                      {evt.title}
                    </div>
                    <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono, monospace' }}>
                      Entity: {evt.entityId} • Score: <strong>{evt.score}/100</strong>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Recommended Action</div>
                    <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>
                      {evt.decision}
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setSelectedEvent(evt);
                      navigate('/risk-operations');
                    }}
                    style={{ padding: '5px 12px', fontSize: '11.5px' }}
                  >
                    Investigate
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SECTION D: Four ML Engines + Live Webhook Telemetry Matrix */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
            Integrated Risk Engines & Ingestion Pipelines
          </h2>
          <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Operational inference pipelines and verified Razorpay Test Mode ingestion contracts.
          </p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '16px',
          }}
        >
          {/* 1. Account Risk */}
          <div className="card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ padding: '7px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(56, 189, 248, 0.12)', color: 'var(--accent-cyan)' }}>
                    <UserCheck size={16} />
                  </div>
                  <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>Account Risk</h3>
                </div>
                <span
                  className={`badge ${
                    events.some((e) => e.engine === 'ACCOUNT_RISK' && (e.severity === 'HIGH' || e.severity === 'CRITICAL'))
                      ? 'badge-rose'
                      : accountIncidents > 0
                      ? 'badge-cyan'
                      : 'badge-green'
                  }`}
                  style={{ fontSize: '10px' }}
                >
                  {events.some((e) => e.engine === 'ACCOUNT_RISK' && (e.severity === 'HIGH' || e.severity === 'CRITICAL'))
                    ? `Elevated (${accountIncidents})`
                    : accountIncidents > 0
                    ? `Active (${accountIncidents})`
                    : 'Online'}
                </span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
                Real-time transaction & account scoring evaluating coordinated syndicate behavioral signals.
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/account-risk')} style={{ width: '100%', fontSize: '12px', padding: '6px' }}>
              <span>Open Module</span>
            </button>
          </div>

          {/* 2. Return Risk */}
          <div className="card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ padding: '7px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(16, 185, 129, 0.12)', color: 'var(--risk-low)' }}>
                    <ShoppingBag size={16} />
                  </div>
                  <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>Return Risk</h3>
                </div>
                <span className={`badge ${returnIncidents > 0 ? 'badge-cyan' : 'badge-green'}`} style={{ fontSize: '10px' }}>
                  {returnIncidents > 0 ? `Audited (${returnIncidents})` : 'Online'}
                </span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
                Specialized loss-prevention pipeline auditing serial wardrobing and refund manipulation.
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/account-risk')} style={{ width: '100%', fontSize: '12px', padding: '6px' }}>
              <span>Open Module</span>
            </button>
          </div>

          {/* 3. Fraud Spike */}
          <div className="card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ padding: '7px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(245, 158, 11, 0.12)', color: 'var(--risk-medium)' }}>
                    <TrendingUp size={16} />
                  </div>
                  <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>Fraud Spike</h3>
                </div>
                <span
                  className={`badge ${
                    events.some((e) => e.engine === 'FRAUD_SPIKE' && (e.severity === 'HIGH' || e.severity === 'CRITICAL'))
                      ? 'badge-rose'
                      : spikeIncidents > 0
                      ? 'badge-amber'
                      : 'badge-green'
                  }`}
                  style={{ fontSize: '10px' }}
                >
                  {events.some((e) => e.engine === 'FRAUD_SPIKE' && (e.severity === 'HIGH' || e.severity === 'CRITICAL'))
                    ? `Spike Detected (${spikeIncidents})`
                    : spikeIncidents > 0
                    ? `Active (${spikeIncidents})`
                    : 'Online'}
                </span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
                Temporal surge detector featuring 5-min micro-burst telemetry and multi-window persistence.
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/fraud-spike')} style={{ width: '100%', fontSize: '12px', padding: '6px' }}>
              <span>Open Radar</span>
            </button>
          </div>

          {/* 4. Abuse Ring */}
          <div className="card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ padding: '7px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(168, 85, 247, 0.14)', color: 'var(--risk-critical)' }}>
                    <Network size={16} />
                  </div>
                  <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>Abuse Ring</h3>
                </div>
                <span
                  className={`badge ${
                    events.some((e) => e.engine === 'ABUSE_RING' && (e.severity === 'HIGH' || e.severity === 'CRITICAL'))
                      ? 'badge-purple'
                      : ringIncidents > 0
                      ? 'badge-cyan'
                      : 'badge-green'
                  }`}
                  style={{ fontSize: '10px' }}
                >
                  {events.some((e) => e.engine === 'ABUSE_RING' && (e.severity === 'HIGH' || e.severity === 'CRITICAL'))
                    ? `Ring Flagged (${ringIncidents})`
                    : ringIncidents > 0
                    ? `Active (${ringIncidents})`
                    : 'Online'}
                </span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
                Bipartite entity network explorer isolating collusive multi-accounting syndicates.
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/abuse-ring')} style={{ width: '100%', fontSize: '12px', padding: '6px' }}>
              <span>Open Explorer</span>
            </button>
          </div>

          {/* 5. Razorpay Ingestion Pipeline */}
          <div className="card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ padding: '7px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(56, 189, 248, 0.12)', color: 'var(--accent-cyan)' }}>
                    <Webhook size={16} />
                  </div>
                  <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>Razorpay Webhook</h3>
                </div>
                <span className="badge badge-purple" style={{ fontSize: '10px' }}>
                  {webhookStatus?.enabled ? `Test Mode (${webhookStatus.accepted} tx)` : 'Standby'}
                </span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
                Verified HMAC-SHA256 ingestion with 10k bounded idempotency feeding 5-minute telemetry.
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/risk-operations')} style={{ width: '100%', fontSize: '12px', padding: '6px' }}>
              <span>View Telemetry</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewPage;
