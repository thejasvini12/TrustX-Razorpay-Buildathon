import React from 'react';
import { RiskAssessmentResponse } from '../../types/api';
import { RiskMeter } from './RiskMeter';
import { ShieldAlert, ShieldCheck, AlertTriangle, User } from 'lucide-react';

interface RiskScoreCardProps {
  assessment: RiskAssessmentResponse;
  isStale?: boolean;
}

export const RiskScoreCard: React.FC<RiskScoreCardProps> = ({ assessment, isStale = false }) => {
  const { account_id, risk_score, risk_probability, risk_level, prediction, recommended_action } = assessment;

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
      case 'ALLOW':
        return { label: 'ALLOW (Frictionless)', icon: ShieldCheck, color: 'var(--risk-low)', bg: 'var(--risk-low-bg)' };
      case 'MANUAL_REVIEW':
        return { label: 'MANUAL REVIEW (Hold & Verify)', icon: AlertTriangle, color: 'var(--risk-medium)', bg: 'var(--risk-medium-bg)' };
      case 'CHALLENGE_OR_BLOCK':
        return { label: 'CHALLENGE OR BLOCK (Step-up Auth / Decline)', icon: ShieldAlert, color: 'var(--risk-high)', bg: 'var(--risk-high-bg)' };
      default:
        return { label: action, icon: ShieldCheck, color: 'var(--accent-cyan)', bg: 'var(--accent-cyan-bg)' };
    }
  };

  const actionInfo = getActionBadge(recommended_action);
  const ActionIcon = actionInfo.icon;

  return (
    <div
      className="card"
      style={{
        position: 'relative',
        opacity: isStale ? 0.75 : 1,
        transition: 'opacity var(--transition-fast)',
        border: `1px solid ${risk_level === 'HIGH' ? 'var(--risk-high-border)' : risk_level === 'MEDIUM' ? 'var(--risk-medium-border)' : 'var(--border-subtle)'}`,
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
          Form Modified • Re-run to Update
        </div>
      )}

      {/* Account ID & Header */}
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
            <User size={16} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Assessed Account
            </div>
            <div className="font-mono" style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>
              {account_id || 'UNSEEN_ACCOUNT'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className={`badge ${getBadgeClass(risk_level)}`} style={{ fontSize: '12px', padding: '4px 12px' }}>
            {risk_level} RISK TIER
          </span>
          <span
            style={{
              fontSize: '11px',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: prediction === 1 ? 'var(--risk-high-bg)' : 'var(--risk-low-bg)',
              color: prediction === 1 ? 'var(--risk-high)' : 'var(--risk-low)',
              fontWeight: '600',
            }}
          >
            Prediction: {prediction === 1 ? 'ABUSE' : 'NORMAL'}
          </span>
        </div>
      </div>

      {/* Score and Probability Key Indicators */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '14px',
          marginBottom: '20px',
        }}
      >
        {/* Risk Score */}
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
            Calibrated Risk Score
          </div>
          <div className="font-mono" style={{ fontSize: '36px', fontWeight: '800', color: 'var(--text-primary)', lineHeight: '1.1', margin: '4px 0' }}>
            {risk_score}
            <span style={{ fontSize: '16px', color: 'var(--text-muted)', fontWeight: '500' }}>/100</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Empirically calibrated probability index
          </div>
        </div>

        {/* Risk Probability */}
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
            Model Abuse Probability
          </div>
          <div className="font-mono" style={{ fontSize: '36px', fontWeight: '800', color: 'var(--accent-cyan)', lineHeight: '1.1', margin: '4px 0' }}>
            {(risk_probability * 100).toFixed(1)}%
          </div>
          <div className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            P(Abuse) = {risk_probability.toFixed(4)}
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
          <div style={{ fontSize: '11px', color: actionInfo.color, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ActionIcon size={14} />
            <span>Recommended Action</span>
          </div>
          <div style={{ fontSize: '15px', fontWeight: '800', color: actionInfo.color, marginTop: '6px', lineHeight: '1.3' }}>
            {actionInfo.label}
          </div>
        </div>
      </div>

      {/* Meter Bar */}
      <div style={{ marginTop: '6px' }}>
        <RiskMeter score={risk_score} level={risk_level} />
      </div>
    </div>
  );
};
