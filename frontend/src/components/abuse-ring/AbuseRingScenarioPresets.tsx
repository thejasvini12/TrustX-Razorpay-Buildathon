import React from 'react';
import { AbuseRingRequest } from '../../types/api';
import { UserCheck, ShieldAlert, CreditCard, Gift, ShoppingBag, Users, Sparkles, LucideIcon } from 'lucide-react';

export interface RingPreset {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: LucideIcon;
  accentColor: string;
  data: AbuseRingRequest;
}

export const RING_PRESETS: RingPreset[] = [
  {
    id: 'clean_independent',
    name: 'Clean Independent Accounts',
    category: 'Synthetic Scenario: Benign Isolated',
    description: '3 independent legitimate accounts with distinct payment methods and non-overlapping infrastructure.',
    icon: UserCheck,
    accentColor: 'var(--risk-low)',
    data: {
      cluster_metadata: { cluster_id: 'RING_BENIGN_001', cluster_type: 'INDEPENDENT_CLEAN' },
      accounts: [
        {
          account_id: 'ACC_LEGIT_101',
          created_at: '2026-01-15T10:00:00',
          average_order_value: 65.0,
          return_rate: 0.03,
          suspicious_activity_score: 0.02,
          order_count: 18,
          total_spend: 1170.0,
          device_type: 'desktop_chrome',
          primary_payment_method: 'credit_card',
        },
        {
          account_id: 'ACC_LEGIT_102',
          created_at: '2026-02-10T14:30:00',
          average_order_value: 82.5,
          return_rate: 0.05,
          suspicious_activity_score: 0.04,
          order_count: 12,
          total_spend: 990.0,
          device_type: 'mobile_ios',
          primary_payment_method: 'paypal',
        },
        {
          account_id: 'ACC_LEGIT_103',
          created_at: '2026-03-01T09:15:00',
          average_order_value: 45.0,
          return_rate: 0.0,
          suspicious_activity_score: 0.01,
          order_count: 8,
          total_spend: 360.0,
          device_type: 'desktop_firefox',
          primary_payment_method: 'debit_card',
        },
      ],
      edges: [
        { account_id: 'ACC_LEGIT_101', entity_type: 'DEVICE', entity_id: 'DEV_ALPHA_101' },
        { account_id: 'ACC_LEGIT_101', entity_type: 'IP', entity_id: 'IP_RESIDENTIAL_101' },
        { account_id: 'ACC_LEGIT_101', entity_type: 'PAYMENT', entity_id: 'CARD_VISA_101' },
        { account_id: 'ACC_LEGIT_102', entity_type: 'DEVICE', entity_id: 'DEV_BETA_102' },
        { account_id: 'ACC_LEGIT_102', entity_type: 'IP', entity_id: 'IP_MOBILE_102' },
        { account_id: 'ACC_LEGIT_102', entity_type: 'PAYMENT', entity_id: 'PAYPAL_USER_102' },
        { account_id: 'ACC_LEGIT_103', entity_type: 'DEVICE', entity_id: 'DEV_GAMMA_103' },
        { account_id: 'ACC_LEGIT_103', entity_type: 'IP', entity_id: 'IP_OFFICE_103' },
        { account_id: 'ACC_LEGIT_103', entity_type: 'PAYMENT', entity_id: 'DEBIT_USER_103' },
      ],
    },
  },
  {
    id: 'identity_ring',
    name: 'Synthetic Identity Ring',
    category: 'Synthetic Scenario: Coordinated Syndicate',
    description: 'High-density clique of accounts sharing synthetic devices, IPs, and burner virtual cards.',
    icon: ShieldAlert,
    accentColor: 'var(--risk-critical)',
    data: {
      cluster_metadata: { cluster_id: 'RING_SYNTH_IDENTITY_043', cluster_type: 'SYNTHETIC_IDENTITY_RING' },
      accounts: [
        {
          account_id: 'ACC_MULE_201',
          created_at: '2026-08-01T02:00:00',
          average_order_value: 175.0,
          return_rate: 0.85,
          suspicious_activity_score: 0.94,
          order_count: 22,
          total_spend: 3850.0,
          device_type: 'emulator_bot',
          primary_payment_method: 'virtual_card',
        },
        {
          account_id: 'ACC_MULE_202',
          created_at: '2026-08-01T02:05:00',
          average_order_value: 180.0,
          return_rate: 0.88,
          suspicious_activity_score: 0.96,
          order_count: 20,
          total_spend: 3600.0,
          device_type: 'emulator_bot',
          primary_payment_method: 'virtual_card',
        },
        {
          account_id: 'ACC_MULE_203',
          created_at: '2026-08-01T02:10:00',
          average_order_value: 165.0,
          return_rate: 0.80,
          suspicious_activity_score: 0.91,
          order_count: 19,
          total_spend: 3135.0,
          device_type: 'emulator_bot',
          primary_payment_method: 'virtual_card',
        },
        {
          account_id: 'ACC_MULE_204',
          created_at: '2026-08-01T02:15:00',
          average_order_value: 190.0,
          return_rate: 0.90,
          suspicious_activity_score: 0.98,
          order_count: 24,
          total_spend: 4560.0,
          device_type: 'emulator_bot',
          primary_payment_method: 'virtual_card',
        },
      ],
      edges: [
        { account_id: 'ACC_MULE_201', entity_type: 'DEVICE', entity_id: 'DEV_SYNDICATE_EMU_01' },
        { account_id: 'ACC_MULE_201', entity_type: 'IP', entity_id: 'IP_HOSTING_VPN_99' },
        { account_id: 'ACC_MULE_201', entity_type: 'PAYMENT', entity_id: 'CARD_BIN_4111_MULE' },
        { account_id: 'ACC_MULE_201', entity_type: 'ADDRESS', entity_id: 'ADDR_DROP_SUITE_12' },
        { account_id: 'ACC_MULE_202', entity_type: 'DEVICE', entity_id: 'DEV_SYNDICATE_EMU_01' },
        { account_id: 'ACC_MULE_202', entity_type: 'IP', entity_id: 'IP_HOSTING_VPN_99' },
        { account_id: 'ACC_MULE_202', entity_type: 'PAYMENT', entity_id: 'CARD_BIN_4111_MULE' },
        { account_id: 'ACC_MULE_202', entity_type: 'ADDRESS', entity_id: 'ADDR_DROP_SUITE_12' },
        { account_id: 'ACC_MULE_203', entity_type: 'DEVICE', entity_id: 'DEV_SYNDICATE_EMU_01' },
        { account_id: 'ACC_MULE_203', entity_type: 'IP', entity_id: 'IP_HOSTING_VPN_99' },
        { account_id: 'ACC_MULE_203', entity_type: 'PAYMENT', entity_id: 'CARD_BIN_4111_MULE' },
        { account_id: 'ACC_MULE_203', entity_type: 'ADDRESS', entity_id: 'ADDR_DROP_SUITE_12' },
        { account_id: 'ACC_MULE_204', entity_type: 'DEVICE', entity_id: 'DEV_SYNDICATE_EMU_01' },
        { account_id: 'ACC_MULE_204', entity_type: 'IP', entity_id: 'IP_HOSTING_VPN_99' },
        { account_id: 'ACC_MULE_204', entity_type: 'PAYMENT', entity_id: 'CARD_BIN_4111_MULE' },
        { account_id: 'ACC_MULE_204', entity_type: 'ADDRESS', entity_id: 'ADDR_DROP_SUITE_12' },
      ],
    },
  },
  {
    id: 'card_testing',
    name: 'Card Testing Syndicate',
    category: 'Synthetic Scenario: Automated Velocity',
    description: 'High velocity account cluster rapidly cycling dozens of compromised credit cards from single proxy endpoint.',
    icon: CreditCard,
    accentColor: 'var(--risk-high)',
    data: {
      cluster_metadata: { cluster_id: 'RING_CARD_TEST_029', cluster_type: 'CARD_TESTING_SYNDICATE' },
      accounts: [
        {
          account_id: 'ACC_TESTER_301',
          created_at: '2026-08-15T04:10:00',
          average_order_value: 12.0,
          return_rate: 0.0,
          suspicious_activity_score: 0.95,
          order_count: 45,
          total_spend: 540.0,
          device_type: 'emulator_bot',
          primary_payment_method: 'credit_card',
        },
        {
          account_id: 'ACC_TESTER_302',
          created_at: '2026-08-15T04:12:00',
          average_order_value: 14.5,
          return_rate: 0.0,
          suspicious_activity_score: 0.92,
          order_count: 38,
          total_spend: 551.0,
          device_type: 'emulator_bot',
          primary_payment_method: 'credit_card',
        },
        {
          account_id: 'ACC_TESTER_303',
          created_at: '2026-08-15T04:15:00',
          average_order_value: 10.0,
          return_rate: 0.0,
          suspicious_activity_score: 0.89,
          order_count: 52,
          total_spend: 520.0,
          device_type: 'emulator_bot',
          primary_payment_method: 'credit_card',
        },
      ],
      edges: [
        { account_id: 'ACC_TESTER_301', entity_type: 'DEVICE', entity_id: 'DEV_SCRIPTER_BOX_01' },
        { account_id: 'ACC_TESTER_301', entity_type: 'IP', entity_id: 'IP_TOR_EXIT_NODE_44' },
        { account_id: 'ACC_TESTER_301', entity_type: 'PAYMENT', entity_id: 'CARD_STOLEN_9011' },
        { account_id: 'ACC_TESTER_301', entity_type: 'PAYMENT', entity_id: 'CARD_STOLEN_9012' },
        { account_id: 'ACC_TESTER_302', entity_type: 'DEVICE', entity_id: 'DEV_SCRIPTER_BOX_01' },
        { account_id: 'ACC_TESTER_302', entity_type: 'IP', entity_id: 'IP_TOR_EXIT_NODE_44' },
        { account_id: 'ACC_TESTER_302', entity_type: 'PAYMENT', entity_id: 'CARD_STOLEN_9013' },
        { account_id: 'ACC_TESTER_302', entity_type: 'PAYMENT', entity_id: 'CARD_STOLEN_9014' },
        { account_id: 'ACC_TESTER_303', entity_type: 'DEVICE', entity_id: 'DEV_SCRIPTER_BOX_01' },
        { account_id: 'ACC_TESTER_303', entity_type: 'IP', entity_id: 'IP_TOR_EXIT_NODE_44' },
        { account_id: 'ACC_TESTER_303', entity_type: 'PAYMENT', entity_id: 'CARD_STOLEN_9015' },
      ],
    },
  },
  {
    id: 'promo_farm',
    name: 'Promo Exploitation Farm',
    category: 'Synthetic Scenario: Multi-Accounting',
    description: 'Sybil accounts sharing device hardware fingerprint to drain new-user registration discounts and referral perks.',
    icon: Gift,
    accentColor: 'var(--risk-medium)',
    data: {
      cluster_metadata: { cluster_id: 'RING_PROMO_FARM_004', cluster_type: 'PROMO_FARMING_RING' },
      accounts: [
        {
          account_id: 'ACC_FARMER_401',
          created_at: '2026-08-20T11:00:00',
          average_order_value: 15.0,
          return_rate: 0.0,
          suspicious_activity_score: 0.88,
          order_count: 2,
          total_spend: 30.0,
          device_type: 'mobile_android',
          primary_payment_method: 'virtual_card',
        },
        {
          account_id: 'ACC_FARMER_402',
          created_at: '2026-08-20T11:02:00',
          average_order_value: 15.0,
          return_rate: 0.0,
          suspicious_activity_score: 0.86,
          order_count: 2,
          total_spend: 30.0,
          device_type: 'mobile_android',
          primary_payment_method: 'virtual_card',
        },
        {
          account_id: 'ACC_FARMER_403',
          created_at: '2026-08-20T11:05:00',
          average_order_value: 15.0,
          return_rate: 0.0,
          suspicious_activity_score: 0.85,
          order_count: 1,
          total_spend: 15.0,
          device_type: 'mobile_android',
          primary_payment_method: 'virtual_card',
        },
        {
          account_id: 'ACC_FARMER_404',
          created_at: '2026-08-20T11:07:00',
          average_order_value: 15.0,
          return_rate: 0.0,
          suspicious_activity_score: 0.90,
          order_count: 1,
          total_spend: 15.0,
          device_type: 'mobile_android',
          primary_payment_method: 'virtual_card',
        },
      ],
      edges: [
        { account_id: 'ACC_FARMER_401', entity_type: 'DEVICE', entity_id: 'DEV_FARM_CLONED_IMEI' },
        { account_id: 'ACC_FARMER_401', entity_type: 'IP', entity_id: 'IP_DYNAMIC_VPN_77' },
        { account_id: 'ACC_FARMER_401', entity_type: 'ADDRESS', entity_id: 'ADDR_LOCKER_BOX_88' },
        { account_id: 'ACC_FARMER_402', entity_type: 'DEVICE', entity_id: 'DEV_FARM_CLONED_IMEI' },
        { account_id: 'ACC_FARMER_402', entity_type: 'IP', entity_id: 'IP_DYNAMIC_VPN_77' },
        { account_id: 'ACC_FARMER_402', entity_type: 'ADDRESS', entity_id: 'ADDR_LOCKER_BOX_88' },
        { account_id: 'ACC_FARMER_403', entity_type: 'DEVICE', entity_id: 'DEV_FARM_CLONED_IMEI' },
        { account_id: 'ACC_FARMER_403', entity_type: 'IP', entity_id: 'IP_DYNAMIC_VPN_77' },
        { account_id: 'ACC_FARMER_403', entity_type: 'ADDRESS', entity_id: 'ADDR_LOCKER_BOX_88' },
        { account_id: 'ACC_FARMER_404', entity_type: 'DEVICE', entity_id: 'DEV_FARM_CLONED_IMEI' },
        { account_id: 'ACC_FARMER_404', entity_type: 'IP', entity_id: 'IP_DYNAMIC_VPN_77' },
        { account_id: 'ACC_FARMER_404', entity_type: 'ADDRESS', entity_id: 'ADDR_LOCKER_BOX_88' },
      ],
    },
  },
  {
    id: 'wardrober_cluster',
    name: 'Serial Wardrober Cluster',
    category: 'Synthetic Scenario: Return Abuse Mule Ring',
    description: 'Coordinated accounts ordering expensive apparel and sharing physical drop return destinations with extreme refund rates.',
    icon: ShoppingBag,
    accentColor: 'var(--risk-high)',
    data: {
      cluster_metadata: { cluster_id: 'RING_WARDROBE_003', cluster_type: 'WARDROBING_MULE_CLUSTER' },
      accounts: [
        {
          account_id: 'ACC_WARDROBE_501',
          created_at: '2026-07-10T15:00:00',
          average_order_value: 280.0,
          return_rate: 0.88,
          suspicious_activity_score: 0.76,
          order_count: 16,
          total_spend: 4480.0,
          device_type: 'mobile_ios',
          primary_payment_method: 'paypal',
        },
        {
          account_id: 'ACC_WARDROBE_502',
          created_at: '2026-07-12T16:20:00',
          average_order_value: 310.0,
          return_rate: 0.92,
          suspicious_activity_score: 0.79,
          order_count: 14,
          total_spend: 4340.0,
          device_type: 'mobile_ios',
          primary_payment_method: 'paypal',
        },
        {
          account_id: 'ACC_WARDROBE_503',
          created_at: '2026-07-15T18:00:00',
          average_order_value: 260.0,
          return_rate: 0.85,
          suspicious_activity_score: 0.72,
          order_count: 12,
          total_spend: 3120.0,
          device_type: 'mobile_ios',
          primary_payment_method: 'credit_card',
        },
      ],
      edges: [
        { account_id: 'ACC_WARDROBE_501', entity_type: 'ADDRESS', entity_id: 'ADDR_RESIDENTIAL_MULE_APT4B' },
        { account_id: 'ACC_WARDROBE_501', entity_type: 'DEVICE', entity_id: 'DEV_IPHONE_SHARED_01' },
        { account_id: 'ACC_WARDROBE_502', entity_type: 'ADDRESS', entity_id: 'ADDR_RESIDENTIAL_MULE_APT4B' },
        { account_id: 'ACC_WARDROBE_502', entity_type: 'DEVICE', entity_id: 'DEV_IPHONE_SHARED_01' },
        { account_id: 'ACC_WARDROBE_503', entity_type: 'ADDRESS', entity_id: 'ADDR_RESIDENTIAL_MULE_APT4B' },
        { account_id: 'ACC_WARDROBE_503', entity_type: 'IP', entity_id: 'IP_RESIDENTIAL_SHARED_50' },
      ],
    },
  },
  {
    id: 'shared_family_bystander',
    name: 'Shared-IP Family & Campus Bystander',
    category: 'Synthetic Scenario: Bystander Protection',
    description: 'Legitimate household / campus users sharing IP and physical address with low suspicious scores and established history.',
    icon: Users,
    accentColor: 'var(--accent-cyan)',
    data: {
      cluster_metadata: { cluster_id: 'RING_FAMILY_020', cluster_type: 'FAMILY_HOUSEHOLD' },
      accounts: [
        {
          account_id: 'ACC_PARENT_601',
          created_at: '2025-05-10T12:00:00',
          average_order_value: 75.0,
          return_rate: 0.04,
          suspicious_activity_score: 0.02,
          order_count: 32,
          total_spend: 2400.0,
          device_type: 'desktop_chrome',
          primary_payment_method: 'credit_card',
        },
        {
          account_id: 'ACC_STUDENT_602',
          created_at: '2025-09-01T15:30:00',
          average_order_value: 48.0,
          return_rate: 0.02,
          suspicious_activity_score: 0.03,
          order_count: 14,
          total_spend: 672.0,
          device_type: 'mobile_ios',
          primary_payment_method: 'debit_card',
        },
        {
          account_id: 'ACC_SIBLING_603',
          created_at: '2026-02-14T18:00:00',
          average_order_value: 55.0,
          return_rate: 0.06,
          suspicious_activity_score: 0.05,
          order_count: 9,
          total_spend: 495.0,
          device_type: 'mobile_android',
          primary_payment_method: 'paypal',
        },
      ],
      edges: [
        { account_id: 'ACC_PARENT_601', entity_type: 'ADDRESS', entity_id: 'ADDR_HOME_OAK_ST_104' },
        { account_id: 'ACC_PARENT_601', entity_type: 'IP', entity_id: 'IP_HOME_WIFI_ROUTER_12' },
        { account_id: 'ACC_PARENT_601', entity_type: 'DEVICE', entity_id: 'DEV_MOM_MACBOOK' },
        { account_id: 'ACC_STUDENT_602', entity_type: 'ADDRESS', entity_id: 'ADDR_HOME_OAK_ST_104' },
        { account_id: 'ACC_STUDENT_602', entity_type: 'IP', entity_id: 'IP_HOME_WIFI_ROUTER_12' },
        { account_id: 'ACC_STUDENT_602', entity_type: 'DEVICE', entity_id: 'DEV_STUDENT_IPHONE' },
        { account_id: 'ACC_SIBLING_603', entity_type: 'ADDRESS', entity_id: 'ADDR_HOME_OAK_ST_104' },
        { account_id: 'ACC_SIBLING_603', entity_type: 'IP', entity_id: 'IP_HOME_WIFI_ROUTER_12' },
        { account_id: 'ACC_SIBLING_603', entity_type: 'DEVICE', entity_id: 'DEV_SIBLING_PIXEL' },
      ],
    },
  },
];

interface AbuseRingScenarioPresetsProps {
  onSelect: (preset: AbuseRingRequest) => void;
  onRunBenchmark?: (preset: RingPreset) => void;
  selectedId?: string;
  disabled?: boolean;
}

export const AbuseRingScenarioPresets: React.FC<AbuseRingScenarioPresetsProps> = ({
  onSelect,
  onRunBenchmark,
  selectedId,
  disabled = false,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={16} color="var(--accent-purple)" />
          <h3 style={{ fontSize: '13px', fontWeight: '800', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            SECTION C — BENCHMARK SCENARIOS (OFFLINE REFERENCE)
          </h3>
          <span className="badge badge-purple" style={{ fontSize: '10px', padding: '2px 6px' }}>
            BENCHMARK / OFFLINE
          </span>
        </div>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          Frozen synthetic topologies for evaluation & stress testing
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '12px',
        }}
      >
        {RING_PRESETS.map((preset) => {
          const Icon = preset.icon;
          const isSelected = selectedId === preset.id;

          return (
            <div
              key={preset.id}
              style={{
                textAlign: 'left',
                padding: '14px',
                backgroundColor: isSelected ? 'var(--bg-elevated)' : 'rgba(30, 41, 59, 0.4)',
                border: `1px solid ${isSelected ? preset.accentColor : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '12px',
                transition: 'all var(--transition-fast)',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div
                      style={{
                        padding: '4px',
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
                    <span style={{ fontSize: '9px', fontWeight: '700', color: 'var(--accent-purple)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      BENCHMARK
                    </span>
                  </div>

                  <span style={{ fontSize: '10px', fontWeight: '600', color: 'var(--text-muted)' }}>
                    {preset.data.accounts.length} Acc • {preset.data.edges.length} Edges
                  </span>
                </div>

                <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  {preset.name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  {preset.description}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)' }}>
                {onRunBenchmark ? (
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => onRunBenchmark(preset)}
                    className="btn btn-primary"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      fontSize: '11px',
                      width: '100%',
                    }}
                  >
                    <span>Run Benchmark →</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => onSelect(preset.data)}
                    className="btn btn-secondary"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      fontSize: '11px',
                      width: '100%',
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
