import React from 'react';
import { AbuseRingResponse } from '../../types/api';
import { ShieldCheck, ShieldAlert, AlertTriangle, ShieldBan } from 'lucide-react';

interface RingResultCardProps {
  result: AbuseRingResponse;
  isStale?: boolean;
}

export const RingResultCard: React.FC<RingResultCardProps> = ({ result, isStale = false }) => {
  const {
    cluster_id,
    final_ring_score,
    risk_level,
    verdict,
    ring_detected,
    recommended_action,
    cluster_size,
    confidence,
    evidence_quality,
  } = result;

  const getVerdictInfo = (v: string) => {
    switch (v) {
      case 'HIGH_CONFIDENCE_RING':
        return {
          label: 'High-Confidence Abuse Ring',
          sub: 'Coordinated multi-accounting syndicate operating dense shared infrastructure.',
          color: 'var(--risk-critical)',
          badge: 'badge-critical',
          icon: ShieldAlert,
        };
      case 'LIKELY_RING':
        return {
          label: 'Likely Abuse Ring',
          sub: 'Elevated shared infrastructure and anomalous entity reuse patterns.',
          color: 'var(--risk-high)',
          badge: 'badge-high',
          icon: ShieldAlert,
        };
      case 'POSSIBLE_RING':
        return {
          label: 'Possible Coordinated Cluster',
          sub: 'Partial infrastructure overlap requiring manual review or enhanced verification.',
          color: 'var(--risk-medium)',
          badge: 'badge-medium',
          icon: AlertTriangle,
        };
      case 'NO_RING':
      default:
        return {
          label: 'No Abuse Ring Detected',
          sub: 'Benign infrastructure sharing consistent with natural household or campus usage.',
          color: 'var(--risk-low)',
          badge: 'badge-low',
          icon: ShieldCheck,
        };
    }
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'BLOCK_ENTIRE_RING':
        return {
          label: 'Block Entire Coordinated Ring',
          color: 'var(--risk-critical)',
          bg: 'var(--risk-critical-bg)',
          icon: ShieldBan,
        };
      case 'RESTRICT_SELECTED_ACCOUNT':
        return {
          label: 'Restrict High-Risk Core Members Only',
          color: 'var(--risk-high)',
          bg: 'var(--risk-high-bg)',
          icon: AlertTriangle,
        };
      case 'REVIEW_CLUSTER':
      case 'REVIEW_ACCOUNTS':
        return {
          label: 'Route Cluster to Special Investigations',
          color: 'var(--risk-medium)',
          bg: 'var(--risk-medium-bg)',
          icon: AlertTriangle,
        };
      case 'NO_ACTION':
      case 'ALLOW':
      default:
        return {
          label: 'Allow Standard Operations (No Restriction)',
          color: 'var(--risk-low)',
          bg: 'var(--risk-low-bg)',
          icon: ShieldCheck,
        };
    }
  };

  const verdictInfo = getVerdictInfo(verdict);
  const actionInfo = getActionBadge(recommended_action);
  const VerdictIcon = verdictInfo.icon;
  const ActionIcon = actionInfo.icon;

  // Normalized score 0-100
  const score100 = Math.round(final_ring_score * 100);

  return (
    <div
      className="card"
      style={{
        position: 'relative',
        opacity: isStale ? 0.75 : 1,
        border: `1px solid ${verdictInfo.color}60`,
        background: 'linear-gradient(180deg, var(--bg-card) 0%, rgba(18, 24, 38, 0.95) 100%)',
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
          Cluster Modified • Re-run Analysis
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
              color: verdictInfo.color,
            }}
          >
            <VerdictIcon size={18} />
          </div>
          <div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Candidate Connected Component
            </div>
            <div className="font-mono" style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>
              {cluster_id || 'CLUSTER_SYNTH_001'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className={`badge ${verdictInfo.badge}`} style={{ fontSize: '12px', padding: '4px 12px' }}>
            {verdict}
          </span>
          <span
            style={{
              fontSize: '11px',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: ring_detected ? 'var(--risk-high-bg)' : 'var(--risk-low-bg)',
              color: ring_detected ? 'var(--risk-high)' : 'var(--risk-low)',
              fontWeight: '600',
            }}
          >
            {ring_detected ? 'RING CONFIRMED' : 'BENIGN CLUSTER'}
          </span>
        </div>
      </div>

      {/* Primary Metrics 3-Card Strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '14px',
          marginBottom: '20px',
        }}
      >
        {/* Final Ring Score */}
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
            Final Ring Index
          </div>
          <div className="font-mono" style={{ fontSize: '36px', fontWeight: '800', color: 'var(--text-primary)', lineHeight: '1.1', margin: '4px 0' }}>
            {score100}
            <span style={{ fontSize: '16px', color: 'var(--text-muted)', fontWeight: '500' }}>/100</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Risk Tier: <strong style={{ color: verdictInfo.color }}>{risk_level}</strong>
          </div>
        </div>

        {/* Cluster Scale & Confidence */}
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
            Component Scope
          </div>
          <div className="font-mono" style={{ fontSize: '36px', fontWeight: '800', color: 'var(--accent-cyan)', lineHeight: '1.1', margin: '4px 0' }}>
            {cluster_size}
            <span style={{ fontSize: '14px', color: 'var(--text-muted)', fontWeight: '500' }}> accounts</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Confidence: <strong style={{ color: 'var(--text-primary)' }}>{confidence}</strong> • Quality: <strong style={{ color: 'var(--text-primary)' }}>{evidence_quality}</strong>
          </div>
        </div>

        {/* Operational Gated Action */}
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
          <div style={{ fontSize: '11px', color: actionInfo.color, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ActionIcon size={14} />
            <span>Operational Defense Action</span>
          </div>
          <div style={{ fontSize: '14px', fontWeight: '800', color: actionInfo.color, marginTop: '6px', lineHeight: '1.3' }}>
            {actionInfo.label}
          </div>
        </div>
      </div>
    </div>
  );
};
