import React from 'react';
import { ReturnRiskResponse } from '../../types/api';
import { ShoppingBag, AlertTriangle, ShieldCheck, ShieldAlert } from 'lucide-react';

interface ReturnRiskPanelProps {
  returnRisk?: ReturnRiskResponse;
}

export const ReturnRiskPanel: React.FC<ReturnRiskPanelProps> = ({ returnRisk }) => {
  if (!returnRisk) return null;

  const {
    return_risk_score,
    return_risk_level,
    return_risk_factors = [],
    return_mitigating_factors = [],
    return_explanation,
    recommended_return_action,
  } = returnRisk;

  const getReturnActionInfo = (action: string) => {
    switch (action) {
      case 'ALLOW_STANDARD_RETURNS':
        return {
          label: 'Allow Standard Frictionless Returns',
          color: 'var(--risk-low)',
          icon: ShieldCheck,
          description: 'Permit automatic instant return authorization and self-service label generation.',
        };
      case 'FLAG_FOR_RETURN_DESK_AUDIT':
        return {
          label: 'Flag for Return-Desk Physical Audit',
          color: 'var(--risk-medium)',
          icon: AlertTriangle,
          description: 'Route return claim to secondary return-desk specialist for item verification before refund.',
        };
      case 'RESTRICT_INSTANT_REFUNDS_AND_INSPECT':
        return {
          label: 'Restrict Instant Refunds & Require Inspection',
          color: 'var(--risk-high)',
          icon: ShieldAlert,
          description: 'Hold all refund disbursements pending warehouse physical item receipt and condition verification.',
        };
      default:
        return {
          label: action,
          color: 'var(--accent-cyan)',
          icon: ShieldCheck,
          description: 'Follow standard post-purchase return policy guidelines.',
        };
    }
  };

  const actionInfo = getReturnActionInfo(recommended_return_action);
  const ActionIcon = actionInfo.icon;

  return (
    <div
      className="card"
      style={{
        border: `1px solid ${
          return_risk_level === 'HIGH'
            ? 'var(--risk-high-border)'
            : return_risk_level === 'MEDIUM'
            ? 'var(--risk-medium-border)'
            : 'var(--border-subtle)'
        }`,
        display: 'flex',
        flexDirection: 'column',
        gap: '18px',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                padding: '6px',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--risk-low)',
              }}
            >
              <ShoppingBag size={18} />
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Return & Refund Risk
            </h3>
          </div>
          <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Specialized detection for serial return behavior, refund abuse and wardrobing patterns.
          </p>
        </div>

        <span
          className={`badge ${
            return_risk_level === 'HIGH'
              ? 'badge-rose'
              : return_risk_level === 'MEDIUM'
              ? 'badge-amber'
              : 'badge-green'
          }`}
          style={{ fontSize: '11px', padding: '3px 10px' }}
        >
          {return_risk_level} RETURN RISK
        </span>
      </div>

      {/* Metrics Row: Return Score & Operational Action */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '14px',
        }}
      >
        {/* Return Score */}
        <div
          style={{
            padding: '14px 16px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Return Abuse Score
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            <span style={{ fontSize: '24px', fontWeight: '800', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-primary)' }}>
              {return_risk_score}
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>/ 100</span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Evaluated independently of checkout privileges
          </span>
        </div>

        {/* Operational Directive */}
        <div
          style={{
            padding: '14px 16px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ActionIcon size={14} color={actionInfo.color} />
            <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Return Desk Directive
            </span>
          </div>
          <span style={{ fontSize: '14px', fontWeight: '700', color: actionInfo.color }}>
            {actionInfo.label}
          </span>
          <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)', lineHeight: '1.35' }}>
            {actionInfo.description}
          </span>
        </div>
      </div>

      {/* Rationale & Indicators */}
      {return_explanation && (
        <div
          style={{
            padding: '12px 14px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(56, 189, 248, 0.05)',
            border: '1px solid rgba(56, 189, 248, 0.2)',
            fontSize: '12px',
          }}
        >
          <strong style={{ color: 'var(--accent-cyan)' }}>Return Explanation: </strong>
          <span style={{ color: 'var(--text-primary)' }}>{return_explanation}</span>
        </div>
      )}

      {/* Signals List */}
      {(return_risk_factors.length > 0 || return_mitigating_factors.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
          {return_risk_factors.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--risk-high)' }}>
                Return Abuse Risk Factors:
              </span>
              <ul style={{ paddingLeft: '16px', fontSize: '12px', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {return_risk_factors.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}

          {return_mitigating_factors.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--risk-low)' }}>
                Mitigating History:
              </span>
              <ul style={{ paddingLeft: '16px', fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {return_mitigating_factors.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
