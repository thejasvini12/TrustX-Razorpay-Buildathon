import React from 'react';
import { AccountRiskRequest } from '../../types/api';
import { UserCheck, ShoppingBag, Bot, ShieldAlert, Sparkles, LucideIcon } from 'lucide-react';

export interface PresetScenario {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: LucideIcon;
  accentColor: string;
  data: AccountRiskRequest;
}

export const PRESET_SCENARIOS: PresetScenario[] = [
  {
    id: 'legitimate_buyer',
    name: 'Legitimate Seasoned Buyer',
    category: 'Synthetic Scenario: Normal',
    description: 'Established account with high transaction volume, low return rate, single device, and standard payment card.',
    icon: UserCheck,
    accentColor: 'var(--risk-low)',
    data: {
      account_id: 'ACC_SYNTH_LEGIT_8821',
      order_count: 26,
      return_count: 1,
      refund_count: 0,
      total_spend: 1580.0,
      average_order_value: 60.77,
      account_age_days: 340,
      device_count: 1,
      ip_count: 2,
      payment_instrument_count: 1,
      high_value_order_count: 2,
      suspicious_activity_score: 0.02,
      device_type: 'desktop_chrome',
      primary_payment_method: 'credit_card',
    },
  },
  {
    id: 'serial_wardrober',
    name: 'Serial Wardrobing Abuser',
    category: 'Synthetic Scenario: Return Abuse',
    description: 'Elevated returns and refund claims with concentrated high-value basket items and short retention cycle.',
    icon: ShoppingBag,
    accentColor: 'var(--risk-medium)',
    data: {
      account_id: 'ACC_SYNTH_WARDROBE_4410',
      order_count: 18,
      return_count: 14,
      refund_count: 12,
      total_spend: 2900.0,
      average_order_value: 161.11,
      account_age_days: 85,
      device_count: 2,
      ip_count: 3,
      payment_instrument_count: 2,
      high_value_order_count: 6,
      suspicious_activity_score: 0.38,
      device_type: 'mobile_ios',
      primary_payment_method: 'paypal',
    },
  },
  {
    id: 'promo_bot',
    name: 'Promo Exploitation Bot',
    category: 'Synthetic Scenario: Sybil / Multi-Accounting',
    description: 'Fresh account utilizing virtual cards, emulator fingerprint, and high device/IP hopping for voucher draining.',
    icon: Bot,
    accentColor: 'var(--risk-high)',
    data: {
      account_id: 'ACC_SYNTH_PROMO_BOT_9104',
      order_count: 3,
      return_count: 0,
      refund_count: 0,
      total_spend: 42.0,
      average_order_value: 14.0,
      account_age_days: 2,
      device_count: 6,
      ip_count: 9,
      payment_instrument_count: 4,
      high_value_order_count: 0,
      suspicious_activity_score: 0.86,
      device_type: 'emulator_bot',
      primary_payment_method: 'virtual_card',
    },
  },
  {
    id: 'syndicate_mule',
    name: 'High-Risk Suspicious Syndicate Mule',
    category: 'Synthetic Scenario: Coordinated Abuse',
    description: 'High velocity order burst on newly aged profile with heavy payment shuffling and crypto/gift card instruments.',
    icon: ShieldAlert,
    accentColor: 'var(--risk-critical)',
    data: {
      account_id: 'ACC_SYNTH_HIGH_RISK_9901',
      order_count: 20,
      return_count: 18,
      refund_count: 17,
      total_spend: 3200.0,
      average_order_value: 160.0,
      account_age_days: 8,
      device_count: 6,
      ip_count: 7,
      payment_instrument_count: 5,
      high_value_order_count: 14,
      suspicious_activity_score: 0.96,
      device_type: 'emulator_bot',
      primary_payment_method: 'crypto_gift_card',
    },
  },
];

interface ScenarioPresetsProps {
  onSelect: (preset: AccountRiskRequest) => void;
  selectedId?: string;
  disabled?: boolean;
}

export const ScenarioPresets: React.FC<ScenarioPresetsProps> = ({
  onSelect,
  selectedId,
  disabled = false,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Sparkles size={14} color="var(--accent-cyan)" />
          <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            1-Click Synthetic Presets
          </span>
        </div>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          Realistic benchmark accounts
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '10px',
        }}
      >
        {PRESET_SCENARIOS.map((preset) => {
          const Icon = preset.icon;
          const isSelected = selectedId === preset.id;

          return (
            <button
              key={preset.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(preset.data)}
              style={{
                textAlign: 'left',
                padding: '12px',
                backgroundColor: isSelected ? 'var(--bg-elevated)' : 'var(--bg-app)',
                border: `1px solid ${isSelected ? preset.accentColor : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius-md)',
                cursor: disabled ? 'not-allowed' : 'pointer',
                opacity: disabled ? 0.6 : 1,
                transition: 'all var(--transition-fast)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
              onMouseEnter={(e) => {
                if (!disabled && !isSelected) {
                  e.currentTarget.style.borderColor = 'var(--border-muted)';
                }
              }}
              onMouseLeave={(e) => {
                if (!disabled && !isSelected) {
                  e.currentTarget.style.borderColor = 'var(--border-subtle)';
                }
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div
                    style={{
                      padding: '5px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'var(--bg-card)',
                      color: preset.accentColor,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Icon size={14} />
                  </div>
                  <span style={{ fontSize: '9px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Preset
                  </span>
                </div>

                <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '3px' }}>
                  {preset.name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  {preset.description}
                </div>
              </div>

              <div style={{ marginTop: '10px', fontSize: '10px', color: 'var(--accent-cyan)', fontWeight: '600' }}>
                Load Scenario →
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
