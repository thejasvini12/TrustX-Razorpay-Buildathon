import React from 'react';
import { FraudSpikeRequest } from '../../types/api';
import { CheckCircle2, TrendingUp, Zap, ShieldAlert, Sparkles, LucideIcon } from 'lucide-react';

export interface FraudPreset {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: LucideIcon;
  accentColor: string;
  data: FraudSpikeRequest;
}

export const FRAUD_PRESETS: FraudPreset[] = [
  {
    id: 'normal_merchant',
    name: 'Normal Stable Merchant',
    category: 'Synthetic Scenario: Baseline Normal',
    description: 'Steady 1% baseline fraud rate with proportional hourly volume and healthy device spread.',
    icon: CheckCircle2,
    accentColor: 'var(--risk-low)',
    data: {
      merchant_id: 'MERCH_SYNTH_NORMAL_101',
      baseline_window: 'previous_24h',
      current_window: 'latest_1h',
      baseline_tx_count: 2400,
      current_tx_count: 100,
      baseline_fraud_count: 24,
      current_fraud_count: 1,
      baseline_fraud_rate: 0.01,
      current_fraud_rate: 0.01,
      baseline_device_count: 2100,
      current_device_count: 95,
      baseline_suspicious_score: 0.03,
      current_suspicious_score: 0.03,
      five_minute_telemetry: [],
    },
  },
  {
    id: 'fraud_spike',
    name: 'Sudden Hourly Fraud Spike',
    category: 'Synthetic Scenario: Velocity Spike',
    description: '5x volume burst accompanied by a surge in fraud rate from 2% to 35% and elevated anomaly score.',
    icon: TrendingUp,
    accentColor: 'var(--risk-high)',
    data: {
      merchant_id: 'MERCH_SYNTH_SPIKE_202',
      baseline_window: 'previous_24h',
      current_window: 'latest_1h',
      baseline_tx_count: 2400,
      current_tx_count: 500,
      baseline_fraud_count: 48,
      current_fraud_count: 175,
      baseline_fraud_rate: 0.02,
      current_fraud_rate: 0.35,
      baseline_device_count: 2000,
      current_device_count: 130,
      baseline_suspicious_score: 0.05,
      current_suspicious_score: 0.85,
      five_minute_telemetry: [],
    },
  },
  {
    id: 'five_min_burst',
    name: 'Rapid 5-Min Sub-Window Burst',
    category: 'Synthetic Scenario: P5 Micro-Burst',
    description: 'Normal hourly aggregation concealing an extreme 7x velocity surge in the latest 5-minute sub-window.',
    icon: Zap,
    accentColor: 'var(--risk-medium)',
    data: {
      merchant_id: 'MERCH_SYNTH_5MIN_BURST_303',
      baseline_window: 'previous_24h',
      current_window: 'latest_1h',
      baseline_tx_count: 1200,
      current_tx_count: 70,
      baseline_fraud_count: 12,
      current_fraud_count: 15,
      baseline_fraud_rate: 0.01,
      current_fraud_rate: 0.21,
      baseline_device_count: 1000,
      current_device_count: 45,
      baseline_suspicious_score: 0.04,
      current_suspicious_score: 0.22,
      five_minute_telemetry: [
        { timestamp: '14:00', tx_count: 6, fraud_count: 0, fraud_rate: 0.0, device_count: 6 },
        { timestamp: '14:05', tx_count: 5, fraud_count: 0, fraud_rate: 0.0, device_count: 5 },
        { timestamp: '14:10', tx_count: 7, fraud_count: 0, fraud_rate: 0.0, device_count: 7 },
        { timestamp: '14:15', tx_count: 6, fraud_count: 0, fraud_rate: 0.0, device_count: 6 },
        { timestamp: '14:20', tx_count: 6, fraud_count: 1, fraud_rate: 0.16, device_count: 5 },
        { timestamp: '14:25', tx_count: 40, fraud_count: 14, fraud_rate: 0.35, device_count: 16 },
      ],
    },
  },
  {
    id: 'persistent_incident',
    name: 'Persistent Multi-Window Incident',
    category: 'Synthetic Scenario: P3 Persistence Escalation',
    description: 'Repeated medium-risk surge windows for the same merchant, triggering P3 stateful escalation to HIGH on sequential evaluations.',
    icon: ShieldAlert,
    accentColor: 'var(--risk-critical)',
    data: {
      merchant_id: 'MERCH_SYNTH_PERSISTENT_404',
      baseline_window: 'previous_24h',
      current_window: 'latest_1h',
      baseline_tx_count: 1200,
      current_tx_count: 70,
      baseline_fraud_count: 12,
      current_fraud_count: 15,
      baseline_fraud_rate: 0.01,
      current_fraud_rate: 0.21,
      baseline_device_count: 1000,
      current_device_count: 45,
      baseline_suspicious_score: 0.04,
      current_suspicious_score: 0.22,
      five_minute_telemetry: [
        { timestamp: '14:00', tx_count: 6, fraud_count: 0, fraud_rate: 0.0, device_count: 6 },
        { timestamp: '14:05', tx_count: 5, fraud_count: 0, fraud_rate: 0.0, device_count: 5 },
        { timestamp: '14:10', tx_count: 7, fraud_count: 0, fraud_rate: 0.0, device_count: 7 },
        { timestamp: '14:15', tx_count: 6, fraud_count: 0, fraud_rate: 0.0, device_count: 6 },
        { timestamp: '14:20', tx_count: 6, fraud_count: 1, fraud_rate: 0.16, device_count: 5 },
        { timestamp: '14:25', tx_count: 40, fraud_count: 14, fraud_rate: 0.35, device_count: 16 },
      ],
    },
  },
];

interface FraudScenarioPresetsProps {
  onSelect: (data: FraudSpikeRequest) => void;
  onRunSimulation?: (preset: FraudPreset) => void;
  selectedId?: string;
  disabled?: boolean;
}

export const FraudScenarioPresets: React.FC<FraudScenarioPresetsProps> = ({
  onSelect,
  onRunSimulation,
  selectedId,
  disabled = false,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={16} color="var(--accent-cyan)" />
          <h2 style={{ fontSize: '14px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
            Benchmark Temporal Scenarios
          </h2>
          <span className="badge badge-purple" style={{ fontSize: '10px' }}>
            BENCHMARK / OFFLINE
          </span>
        </div>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          Deterministic velocity & surge patterns
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '12px',
        }}
      >
        {FRAUD_PRESETS.map((preset) => {
          const Icon = preset.icon;
          const isSelected = selectedId === preset.id;

          return (
            <div
              key={preset.id}
              style={{
                padding: '14px',
                backgroundColor: isSelected ? 'var(--bg-elevated)' : 'rgba(15, 23, 42, 0.5)',
                border: `1px solid ${isSelected ? preset.accentColor : 'var(--border-color)'}`,
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '12px',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div
                    style={{
                      padding: '6px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'rgba(30, 41, 59, 0.6)',
                      color: preset.accentColor,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Icon size={16} />
                  </div>
                  <span className="badge badge-purple" style={{ fontSize: '9px', textTransform: 'uppercase' }}>
                    BENCHMARK / OFFLINE
                  </span>
                </div>

                <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  {preset.name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.45' }}>
                  {preset.description}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: 'auto' }}>
                {onRunSimulation ? (
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => onRunSimulation(preset)}
                    className="btn btn-primary"
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      fontSize: '11px',
                    }}
                  >
                    <span>Run Simulation →</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => onSelect(preset.data)}
                    className="btn btn-secondary"
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      fontSize: '11px',
                    }}
                  >
                    <span>Load Scenario →</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
