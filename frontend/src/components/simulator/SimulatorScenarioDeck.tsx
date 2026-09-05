import React from 'react';
import {
  SimulatorScenarioDefinition,
  SimulatorScenarioId,
  ScenarioSeverity,
  SimulatorEngine,
} from '../../types/simulator';
import { UserCheck, RefreshCw, Bot, CreditCard, Activity, Users, ShieldCheck } from 'lucide-react';

interface SimulatorScenarioDeckProps {
  scenarios: SimulatorScenarioDefinition[];
  selectedScenarioId: SimulatorScenarioId;
  onSelectScenario: (scenario: SimulatorScenarioDefinition) => void;
  disabled?: boolean;
}

const SEVERITY_CONFIG: Record<ScenarioSeverity, { label: string; badgeClass: string }> = {
  LOW: { label: 'Low Severity', badgeClass: 'badge-green' },
  MEDIUM: { label: 'Medium Severity', badgeClass: 'badge-amber' },
  HIGH: { label: 'High Severity', badgeClass: 'badge-rose' },
  CRITICAL: { label: 'Critical Severity', badgeClass: 'badge-purple' },
};

const ENGINE_LABELS: Record<SimulatorEngine, { label: string; bg: string; color: string; border: string }> = {
  ACCOUNT_RISK: {
    label: 'Account Risk',
    bg: 'rgba(56, 189, 248, 0.12)',
    color: 'var(--accent-cyan)',
    border: 'rgba(56, 189, 248, 0.25)',
  },
  FRAUD_SPIKE: {
    label: 'Fraud Spike',
    bg: 'rgba(245, 158, 11, 0.12)',
    color: 'var(--risk-medium)',
    border: 'rgba(245, 158, 11, 0.25)',
  },
  ABUSE_RING: {
    label: 'Abuse Ring',
    bg: 'rgba(168, 85, 247, 0.14)',
    color: 'var(--risk-critical)',
    border: 'rgba(168, 85, 247, 0.3)',
  },
};

const SCENARIO_ICONS: Record<SimulatorScenarioId, React.ReactNode> = {
  legitimate_buyer: <UserCheck size={18} color="var(--risk-low)" />,
  serial_wardrober: <RefreshCw size={18} color="var(--risk-medium)" />,
  promo_farm: <Bot size={18} color="var(--risk-critical)" />,
  card_testing: <CreditCard size={18} color="var(--risk-high)" />,
  persistent_incident: <Activity size={18} color="var(--risk-high)" />,
  syndicate_mule: <Users size={18} color="var(--risk-critical)" />,
  shared_family_bystander: <ShieldCheck size={18} color="var(--risk-low)" />,
};

export const SimulatorScenarioDeck: React.FC<SimulatorScenarioDeckProps> = ({
  scenarios,
  selectedScenarioId,
  onSelectScenario,
  disabled = false,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text-primary)' }}>
            Attack Scenario Templates & Benchmarks
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Select an attack pattern or baseline scenario to orchestrate against live defense engines.
          </p>
        </div>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {scenarios.length} Templates Available
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))',
          gap: '12px',
        }}
        role="radiogroup"
        aria-label="Simulation scenario selection"
      >
        {scenarios.map((scenario) => {
          const isSelected = scenario.id === selectedScenarioId;
          const severityInfo = SEVERITY_CONFIG[scenario.severity];

          return (
            <button
              key={scenario.id}
              type="button"
              role="radio"
              aria-checked={isSelected}
              disabled={disabled}
              onClick={() => onSelectScenario(scenario)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                padding: '14px',
                textAlign: 'left',
                backgroundColor: isSelected ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                border: isSelected
                  ? '1.5px solid var(--accent-cyan)'
                  : '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                cursor: disabled ? 'not-allowed' : 'pointer',
                transition: 'all var(--transition-fast)',
                boxShadow: isSelected ? 'var(--shadow-glow-cyan)' : 'var(--shadow-sm)',
                opacity: disabled && !isSelected ? 0.6 : 1,
                position: 'relative',
                minHeight: '160px',
                gap: '10px',
              }}
            >
              {/* Header: Icon + Category + Severity Badge */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div
                    style={{
                      padding: '6px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'var(--bg-elevated)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {SCENARIO_ICONS[scenario.id]}
                  </div>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: '700',
                      letterSpacing: '0.05em',
                      textTransform: 'uppercase',
                      color: 'var(--text-muted)',
                    }}
                  >
                    {scenario.attackCategory.replace(/_/g, ' ')}
                  </span>
                </div>
                <span className={`badge ${severityInfo.badgeClass}`} style={{ fontSize: '10px', padding: '2px 7px' }}>
                  {severityInfo.label}
                </span>
              </div>

              {/* Title & Description */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div
                  style={{
                    fontSize: '13.5px',
                    fontWeight: '600',
                    color: isSelected ? 'var(--accent-cyan)' : 'var(--text-primary)',
                    lineHeight: '1.3',
                  }}
                >
                  {scenario.name}
                </div>
                <div
                  style={{
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    lineHeight: '1.4',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {scenario.shortDescription}
                </div>
              </div>

              {/* Footer: Involved Engine Chips & Stage Count */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  paddingTop: '8px',
                  borderTop: '1px solid var(--border-subtle)',
                  width: '100%',
                }}
              >
                <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                  {scenario.involvedEngines.map((engine) => {
                    const cfg = ENGINE_LABELS[engine];
                    return (
                      <span
                        key={engine}
                        style={{
                          fontSize: '10px',
                          fontWeight: '600',
                          padding: '2px 6px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: cfg.bg,
                          color: cfg.color,
                          border: `1px solid ${cfg.border}`,
                        }}
                      >
                        {cfg.label}
                      </span>
                    );
                  })}
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                  {scenario.stages.length} {scenario.stages.length === 1 ? 'Stage' : 'Stages'}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
