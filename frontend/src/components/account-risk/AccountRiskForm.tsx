import React, { useState } from 'react';
import { AccountRiskRequest } from '../../types/api';
import {
  User,
  ShoppingBag,
  CreditCard,
  Smartphone,
  ChevronDown,
  ChevronUp,
  Loader2,
  Search,
  Sliders,
  CheckCircle2,
  Activity,
  RefreshCw,
} from 'lucide-react';

export interface AccountRiskFormProps {
  accountIdInput: string;
  onAccountIdChange: (val: string) => void;
  onInvestigate: (targetId?: string) => void;
  onAssessModified?: () => void;
  onRefreshLive?: () => void;
  isRefreshingLive?: boolean;
  formData: AccountRiskRequest;
  onFormChange: (data: AccountRiskRequest) => void;
  onReset: () => void;
  loading: boolean;
  profileLoaded: boolean;
  sampleIds?: string[];
}

export const DEVICE_OPTIONS = [
  { value: 'mobile_ios', label: 'Mobile iOS' },
  { value: 'mobile_android', label: 'Mobile Android' },
  { value: 'desktop_chrome', label: 'Desktop Chrome' },
  { value: 'desktop_safari', label: 'Desktop Safari' },
  { value: 'emulator_bot', label: 'Emulator / Bot Fingerprint' },
  { value: 'unknown', label: 'Unknown Fingerprint' },
];

export const PAYMENT_OPTIONS = [
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'debit_card', label: 'Debit Card' },
  { value: 'paypal', label: 'PayPal' },
  { value: 'apple_pay', label: 'Apple Pay' },
  { value: 'virtual_card', label: 'Virtual Card (Prepaid)' },
  { value: 'crypto_gift_card', label: 'Crypto / Gift Card' },
  { value: 'unknown', label: 'Unknown Method' },
];

export const DEFAULT_SUGGESTIONS = [
  { id: 'ACC_MERCHANT_90210', label: 'Standard Merchant (90210)' },
  { id: 'ACC_WARD_00001', label: 'Serial Wardrober (86% Returns)' },
  { id: 'ACC_LEGIT_STD_01502', label: 'Seasoned Buyer (Clean)' },
  { id: 'ACC_SYNTH_PROMO_BOT_9104', label: 'Promo Exploitation Bot' },
  { id: 'ACC_SYNTH_HIGH_RISK_9901', label: 'Syndicate Mule' },
];

export const AccountRiskForm: React.FC<AccountRiskFormProps> = ({
  accountIdInput,
  onAccountIdChange,
  onInvestigate,
  onAssessModified,
  onRefreshLive,
  isRefreshingLive = false,
  formData,
  onFormChange,
  onReset,
  loading,
  profileLoaded,
  sampleIds,
}) => {
  // Collapsed manual parameters section
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);

  const handleNumericChange = (field: keyof AccountRiskRequest, value: string) => {
    const num = value === '' ? 0 : parseFloat(value);
    onFormChange({
      ...formData,
      [field]: isNaN(num) ? 0 : num,
    });
  };

  const returnRatePercent =
    formData.return_rate !== undefined && formData.return_rate !== null
      ? (formData.return_rate * 100).toFixed(1)
      : (formData.order_count ?? 0) > 0
      ? (((formData.return_count ?? 0) / (formData.order_count ?? 1)) * 100).toFixed(1)
      : '0.0';

  const refundRatePercent =
    formData.refund_rate !== undefined && formData.refund_rate !== null
      ? (formData.refund_rate * 100).toFixed(1)
      : (formData.order_count ?? 0) > 0
      ? (((formData.refund_count ?? 0) / (formData.order_count ?? 1)) * 100).toFixed(1)
      : '0.0';

  const isElevatedReturnRate = parseFloat(returnRatePercent) >= 20.0;
  const isElevatedRefundRate = parseFloat(refundRatePercent) >= 15.0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onInvestigate();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 1. PRIMARY ACCOUNT ID LOOKUP BAR */}
      <div
        className="card"
        style={{
          padding: '24px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '11px',
                fontWeight: '700',
                padding: '2px 8px',
                borderRadius: 'var(--radius-pill)',
                backgroundColor: 'rgba(56, 189, 248, 0.12)',
                color: 'var(--accent-cyan)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              Account Investigation Console
            </span>
            {profileLoaded && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                  fontWeight: '600',
                  color: 'var(--risk-low)',
                }}
              >
                <CheckCircle2 size={13} />
                Profile Loaded
              </span>
            )}
          </div>

          <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '6px' }}>
            Account Lookup
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Enter an Account Identifier to retrieve authentic behavioral records and execute risk scoring without manual data entry.
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', flex: '1', minWidth: '280px' }}>
              <Search
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                type="text"
                className="font-mono"
                value={accountIdInput}
                onChange={(e) => onAccountIdChange(e.target.value)}
                placeholder="Enter Account ID (e.g. ACC_MERCHANT_90210, ACC_WARD_00001)..."
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '10px 14px 10px 38px',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '14px',
                  color: 'var(--text-primary)',
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading || !accountIdInput.trim()}
              className="btn btn-primary"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 22px',
                fontSize: '13px',
                fontWeight: '700',
                minWidth: '170px',
                justifyContent: 'center',
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={15} className="spin" />
                  <span>Investigating...</span>
                </>
              ) : (
                <>
                  <Search size={15} />
                  <span>Investigate Account</span>
                </>
              )}
            </button>
          </div>

          {/* Quick Suggestions Chips */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', paddingTop: '4px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600' }}>
              Quick Suggestions:
            </span>
            {(sampleIds && sampleIds.length > 0
              ? sampleIds.slice(0, 6).map((id) => ({ id, label: id }))
              : DEFAULT_SUGGESTIONS
            ).map((sug) => (
              <button
                key={sug.id}
                type="button"
                onClick={() => {
                  onAccountIdChange(sug.id);
                  onInvestigate(sug.id);
                }}
                disabled={loading}
                style={{
                  background: 'none',
                  border: accountIdInput.toUpperCase() === sug.id.toUpperCase()
                    ? '1px solid var(--accent-cyan)'
                    : '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-pill)',
                  padding: '3px 9px',
                  fontSize: '11px',
                  color: accountIdInput.toUpperCase() === sug.id.toUpperCase()
                    ? 'var(--accent-cyan)'
                    : 'var(--text-secondary)',
                  cursor: 'pointer',
                  backgroundColor: accountIdInput.toUpperCase() === sug.id.toUpperCase()
                    ? 'var(--accent-cyan-bg)'
                    : 'var(--bg-app)',
                  fontFamily: 'JetBrains Mono, monospace',
                }}
              >
                {sug.id}
              </button>
            ))}
          </div>
        </form>
      </div>

      {/* 2. RETRIEVED ACCOUNT PROFILE OVERVIEW (SECTIONS A - D) */}
      {profileLoaded && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>
                Account Investigation Profile
              </h3>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Authentic profile metrics retrieved from registry and server-side feature extraction.
              </p>
            </div>
            <span className="badge badge-cyan" style={{ fontSize: '10.5px' }}>
              {formData.account_id || 'ACCOUNT RECORD'}
            </span>
          </div>

          {/* REAL-TIME LIVE ACTIVITY SECTION */}
          <div
            className="card"
            style={{
              padding: '18px 20px',
              backgroundColor: 'rgba(16, 185, 129, 0.03)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              borderRadius: 'var(--radius-lg)',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    padding: '6px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: 'var(--risk-low)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Activity size={16} />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h4 style={{ fontSize: '13.5px', fontWeight: '800', color: 'var(--text-primary)' }}>
                      Live Activity (Real-Time Razorpay Webhooks)
                    </h4>
                    <span className="badge badge-green" style={{ fontSize: '10px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <span className="live-dot" />
                      LIVE ACTIVITY
                    </span>
                  </div>
                  <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    Genuine telemetry ingested live via accepted Razorpay webhooks. Kept strictly isolated from historical metrics.
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {onRefreshLive && (
                  <button
                    type="button"
                    onClick={onRefreshLive}
                    disabled={isRefreshingLive}
                    className="btn btn-secondary"
                    style={{
                      padding: '4px 10px',
                      fontSize: '11px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    <RefreshCw size={12} className={isRefreshingLive ? 'spin' : ''} />
                    <span>Refresh Live</span>
                  </button>
                )}
              </div>
            </div>

            {/* Metrics Row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px' }}>
              <div style={{ backgroundColor: 'var(--bg-app)', padding: '10px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
                  Live Payments
                </span>
                <div className="font-mono" style={{ fontSize: '16px', fontWeight: '800', color: (formData.live_activity?.payment_count ?? 0) > 0 ? 'var(--risk-low)' : 'var(--text-primary)', marginTop: '2px' }}>
                  {formData.live_activity?.payment_count ?? 0}
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-app)', padding: '10px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
                  Live Volume
                </span>
                <div className="font-mono" style={{ fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
                  ₹{Number(formData.live_activity?.payment_volume ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-app)', padding: '10px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
                  Failed Payments
                </span>
                <div className="font-mono" style={{ fontSize: '16px', fontWeight: '800', color: (formData.live_activity?.failed_payment_count ?? 0) > 0 ? 'var(--risk-high)' : 'var(--text-primary)', marginTop: '2px' }}>
                  {formData.live_activity?.failed_payment_count ?? 0}
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-app)', padding: '10px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
                  Webhooks Accepted
                </span>
                <div className="font-mono" style={{ fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
                  {formData.live_activity?.webhook_event_count ?? 0}
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-app)', padding: '10px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
                  Last Payment
                </span>
                <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {formData.live_activity?.last_payment_at
                    ? new Date(formData.live_activity.last_payment_at).toLocaleTimeString()
                    : 'No live activity'}
                </div>
              </div>
            </div>

            {/* Association Source info banner (if live events present) */}
            {formData.live_activity?.association_sources && formData.live_activity.association_sources.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--text-muted)', paddingTop: '2px' }}>
                <span>Association method:</span>
                {formData.live_activity.association_sources.map((src) => (
                  <span key={src} className="badge badge-zinc" style={{ fontSize: '9.5px' }}>
                    {src === 'test_mode_default'
                      ? 'Test Mode Default (RAZORPAY_TEST_ACCOUNT_ID)'
                      : src === 'notes'
                      ? 'Payment Notes (notes.account_id)'
                      : src === 'header_dev_test'
                      ? 'Dev/Test Header Override'
                      : src}
                  </span>
                ))}
              </div>
            )}

            {/* Recent Live Events log */}
            {formData.live_activity?.recent_events && formData.live_activity.recent_events.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-secondary)' }}>
                  Recent Live Transactions ({formData.live_activity.recent_events.length})
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '140px', overflowY: 'auto' }}>
                  {formData.live_activity.recent_events.slice(0, 5).map((evt, idx) => (
                    <div
                      key={evt.event_id || idx}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '11.5px',
                        padding: '5px 8px',
                        backgroundColor: 'var(--bg-app)',
                        borderRadius: 'var(--radius-sm)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          className={`badge ${
                            evt.status === 'captured'
                              ? 'badge-green'
                              : evt.status === 'failed'
                              ? 'badge-rose'
                              : 'badge-amber'
                          }`}
                          style={{ fontSize: '9.5px' }}
                        >
                          {evt.status.toUpperCase()}
                        </span>
                        <span className="font-mono" style={{ color: 'var(--text-primary)' }}>
                          {evt.payment_id || 'pay_unknown'}
                        </span>
                        <span style={{ color: 'var(--text-muted)' }}>({evt.event_type})</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {evt.amount !== null && evt.amount !== undefined && (
                          <span className="font-mono" style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                            ₹{evt.amount.toFixed(2)}
                          </span>
                        )}
                        <span style={{ color: 'var(--text-muted)', fontSize: '10.5px' }}>
                          {new Date(evt.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            {/* SECTION A: Account History */}
            <div
              className="card"
              style={{
                padding: '16px 18px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <User size={15} color="var(--accent-cyan)" />
                <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  A. Account History
                </h4>
                <span className="badge badge-zinc" style={{ fontSize: '9px', marginLeft: 'auto' }}>
                  HISTORICAL
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Account Identifier</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    {formData.account_id || 'N/A'}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Account Age</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    {formData.account_age_days ?? 0} days
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Total Orders</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    {formData.order_count ?? 0}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Total Spend</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    ${Number(formData.total_spend ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>
              </div>
            </div>

            {/* SECTION B: Returns & Refunds */}
            <div
              className="card"
              style={{
                padding: '16px 18px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                border: isElevatedReturnRate ? '1px solid var(--risk-high-border)' : '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShoppingBag size={15} color={isElevatedReturnRate ? 'var(--risk-high)' : 'var(--risk-low)'} />
                  <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                    B. Returns & Refunds
                  </h4>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {isElevatedReturnRate && (
                    <span className="badge badge-rose" style={{ fontSize: '10px' }}>
                      High Return Velocity
                    </span>
                  )}
                  <span className="badge badge-zinc" style={{ fontSize: '9px' }}>
                    HISTORICAL
                  </span>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Returned Orders</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: isElevatedReturnRate ? 'var(--risk-high)' : 'var(--text-primary)', marginTop: '2px' }}>
                    {formData.return_count ?? 0}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Refund Claims</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: isElevatedRefundRate ? 'var(--risk-medium)' : 'var(--text-primary)', marginTop: '2px' }}>
                    {formData.refund_count ?? 0}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Effective Return Rate</span>
                  <div className="font-mono" style={{ fontSize: '14px', fontWeight: '800', color: isElevatedReturnRate ? 'var(--risk-high)' : 'var(--risk-low)', marginTop: '2px' }}>
                    {returnRatePercent}%
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Effective Refund Rate</span>
                  <div className="font-mono" style={{ fontSize: '14px', fontWeight: '800', color: isElevatedRefundRate ? 'var(--risk-medium)' : 'var(--text-primary)', marginTop: '2px' }}>
                    {refundRatePercent}%
                  </div>
                </div>
              </div>
            </div>

            {/* SECTION C: Transaction Behavior */}
            <div
              className="card"
              style={{
                padding: '16px 18px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CreditCard size={15} color="var(--risk-medium)" />
                <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  C. Transaction Behavior
                </h4>
                <span className="badge badge-zinc" style={{ fontSize: '9px', marginLeft: 'auto' }}>
                  HISTORICAL
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Average Order Value</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    ${Number(formData.average_order_value ?? 0).toFixed(2)}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>High-Value Orders</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    {formData.high_value_order_count ?? 0}
                  </div>
                </div>

                <div style={{ gridColumn: 'span 2' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Primary Payment Method</span>
                  <div style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--text-primary)', marginTop: '2px', textTransform: 'capitalize' }}>
                    {(formData.primary_payment_method || 'Unknown').replace(/_/g, ' ')}
                  </div>
                </div>
              </div>
            </div>

            {/* SECTION D: Network & Device Signals */}
            <div
              className="card"
              style={{
                padding: '16px 18px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Smartphone size={15} color="var(--accent-purple)" />
                <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  D. Network & Hardware
                </h4>
                <span className="badge badge-zinc" style={{ fontSize: '9px', marginLeft: 'auto' }}>
                  HISTORICAL
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Hardware Devices</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    {formData.device_count ?? 1}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Distinct IPs</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    {formData.ip_count ?? 1}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Instruments Linked</span>
                  <div className="font-mono" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    {formData.payment_instrument_count ?? 1}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Device Fingerprint</span>
                  <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)', marginTop: '2px', textTransform: 'capitalize' }}>
                    {(formData.device_type || 'Unknown').replace(/_/g, ' ')}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. COLLAPSIBLE ADVANCED PARAMETER ADJUSTMENT (FOR TESTING ONLY) */}
      <div
        className="card"
        style={{
          padding: '0',
          overflow: 'hidden',
          border: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-app)',
        }}
      >
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          style={{
            width: '100%',
            padding: '12px 18px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            cursor: 'pointer',
            textAlign: 'left',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={14} color="var(--text-muted)" />
            <span style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--text-secondary)' }}>
              Advanced: Manual Parameter Adjustment (Testing & Simulation)
            </span>
          </div>
          {showAdvanced ? <ChevronUp size={15} color="var(--text-muted)" /> : <ChevronDown size={15} color="var(--text-muted)" />}
        </button>

        {showAdvanced && (
          <div style={{ padding: '18px', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Optionally override individual account metrics to simulate hypothetical behavior or test edge cases against the ML model.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Account Age (Days)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.account_age_days ?? 0}
                  onChange={(e) => handleNumericChange('account_age_days', e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12.5px', marginTop: '4px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Total Orders</label>
                <input
                  type="number"
                  min="0"
                  value={formData.order_count ?? 1}
                  onChange={(e) => handleNumericChange('order_count', e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12.5px', marginTop: '4px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Returned Orders</label>
                <input
                  type="number"
                  min="0"
                  value={formData.return_count ?? 0}
                  onChange={(e) => handleNumericChange('return_count', e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12.5px', marginTop: '4px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Refund Claims</label>
                <input
                  type="number"
                  min="0"
                  value={formData.refund_count ?? 0}
                  onChange={(e) => handleNumericChange('refund_count', e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12.5px', marginTop: '4px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Total Spend ($)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.total_spend ?? 0}
                  onChange={(e) => handleNumericChange('total_spend', e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12.5px', marginTop: '4px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Device Count</label>
                <input
                  type="number"
                  min="1"
                  value={formData.device_count ?? 1}
                  onChange={(e) => handleNumericChange('device_count', e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12.5px', marginTop: '4px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>IP Count</label>
                <input
                  type="number"
                  min="1"
                  value={formData.ip_count ?? 1}
                  onChange={(e) => handleNumericChange('ip_count', e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12.5px', marginTop: '4px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Payment Instruments</label>
                <input
                  type="number"
                  min="1"
                  value={formData.payment_instrument_count ?? 1}
                  onChange={(e) => handleNumericChange('payment_instrument_count', e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12.5px', marginTop: '4px' }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', paddingTop: '6px' }}>
              <button
                type="button"
                onClick={onReset}
                className="btn btn-secondary"
                style={{ fontSize: '12px', padding: '6px 14px' }}
              >
                Reset to Retrieved Profile
              </button>
              <button
                type="button"
                onClick={onAssessModified ? onAssessModified : () => onInvestigate()}
                disabled={loading}
                className="btn btn-primary"
                style={{ fontSize: '12px', padding: '6px 16px' }}
              >
                Re-assess with Modified Parameters
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AccountRiskForm;
