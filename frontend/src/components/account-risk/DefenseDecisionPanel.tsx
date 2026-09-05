import React from 'react';
import { DecisionPolicyResponse } from '../../types/api';
import { Shield, CheckCircle, Zap } from 'lucide-react';

interface DefenseDecisionPanelProps {
  decisionPolicy?: DecisionPolicyResponse;
}

export const DefenseDecisionPanel: React.FC<DefenseDecisionPanelProps> = ({ decisionPolicy }) => {
  if (!decisionPolicy) return null;

  const { abuse_pattern, primary_action, secondary_actions, policy_triggers, policy_reasoning, confidence } =
    decisionPolicy;

  return (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div>
        <div className="card-header" style={{ marginBottom: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Shield size={16} color="var(--accent-cyan)" />
              <h3 className="card-title">Adaptive Defense Policy</h3>
            </div>
            <p className="card-description">
              Deterministic operational rules evaluated downstream of ML risk inference.
            </p>
          </div>
          <span className="badge badge-cyan" style={{ fontSize: '11px' }}>
            Confidence: {confidence}
          </span>
        </div>

        {/* Pattern & Primary Action */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--bg-app)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <span style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Detected Pattern Archetype
            </span>
            <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--accent-cyan)', marginTop: '2px' }}>
              {abuse_pattern}
            </div>
          </div>

          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--bg-elevated)',
              border: '1px solid var(--border-muted)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <span style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Primary Defense Action
            </span>
            <div style={{ fontSize: '14px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {primary_action}
            </div>
          </div>
        </div>

        {/* Policy Reasoning */}
        {policy_reasoning && (
          <div style={{ marginBottom: '16px' }}>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)' }}>
              Policy Rationale
            </span>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.5' }}>
              {policy_reasoning}
            </p>
          </div>
        )}

        {/* Policy Triggers */}
        {policy_triggers && policy_triggers.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Zap size={12} color="var(--risk-medium)" />
              <span>Deterministic Triggers Fired</span>
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
              {policy_triggers.map((trigger, idx) => (
                <span
                  key={idx}
                  style={{
                    fontSize: '11px',
                    padding: '3px 8px',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    color: 'var(--risk-medium)',
                    border: '1px solid var(--risk-medium-border)',
                    borderRadius: 'var(--radius-sm)',
                    fontFamily: 'monospace',
                  }}
                >
                  {trigger}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Secondary Actions */}
        {secondary_actions && secondary_actions.length > 0 && (
          <div>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)' }}>
              Secondary Operational Controls
            </span>
            <ul style={{ listStyle: 'none', padding: 0, marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {secondary_actions.map((act, idx) => (
                <li
                  key={idx}
                  style={{
                    fontSize: '11px',
                    color: 'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <CheckCircle size={12} color="var(--accent-cyan)" />
                  <span>{act}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
