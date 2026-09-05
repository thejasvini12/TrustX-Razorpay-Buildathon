import React, { useState } from 'react';
import { FraudSpikeRequest, FiveMinuteObservation } from '../../types/api';
import { FiveMinuteTelemetryBuilder } from './FiveMinuteTelemetryBuilder';
import { TrendingUp, RotateCcw, Loader2 } from 'lucide-react';

interface FraudSpikeFormProps {
  formData: FraudSpikeRequest;
  onChange: (data: FraudSpikeRequest) => void;
  onSubmit: () => void;
  onReset: () => void;
  loading: boolean;
}

export const FraudSpikeForm: React.FC<FraudSpikeFormProps> = ({
  formData,
  onChange,
  onSubmit,
  onReset,
  loading,
}) => {
  const [overrideRates, setOverrideRates] = useState<boolean>(false);

  const handleNumericChange = (field: keyof FraudSpikeRequest, value: string) => {
    const num = value === '' ? 0 : parseFloat(value);
    onChange({
      ...formData,
      [field]: isNaN(num) ? 0 : num,
    });
  };

  const handleRateChange = (field: 'baseline_fraud_rate' | 'current_fraud_rate', value: string) => {
    if (value === '') {
      onChange({ ...formData, [field]: null });
      return;
    }
    const num = parseFloat(value);
    onChange({
      ...formData,
      [field]: isNaN(num) ? null : Math.min(1, Math.max(0, num / 100)),
    });
  };

  const handleTelemetryChange = (telemetry: FiveMinuteObservation[]) => {
    onChange({
      ...formData,
      five_minute_telemetry: telemetry,
    });
  };

  const calculatedBaseRate =
    (formData.baseline_tx_count ?? 0) > 0
      ? (((formData.baseline_fraud_count ?? 0) / (formData.baseline_tx_count ?? 1)) * 100).toFixed(2)
      : '0.00';

  const calculatedCurrRate =
    (formData.current_tx_count ?? 0) > 0
      ? (((formData.current_fraud_count ?? 0) / (formData.current_tx_count ?? 1)) * 100).toFixed(2)
      : '0.00';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <form onSubmit={handleSubmit} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* Form Header */}
      <div className="card-header" style={{ marginBottom: '0' }}>
        <div>
          <h2 className="card-title">Temporal Velocity & Window Configuration</h2>
          <p className="card-description">
            Compare merchant baseline activity against current window metrics to detect surge velocity and fraud-rate delta.
          </p>
        </div>
        <button
          type="button"
          onClick={onReset}
          disabled={loading}
          className="btn btn-secondary"
          style={{ padding: '6px 12px', fontSize: '11px' }}
        >
          <RotateCcw size={12} />
          <span>Reset Defaults</span>
        </button>
      </div>

      {/* Top Strip: Merchant ID & Windows */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '14px',
          padding: '14px',
          backgroundColor: 'var(--bg-app)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
        }}
      >
        {/* Merchant Identifier */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-secondary)' }}>
            Merchant Identifier <span style={{ color: 'var(--accent-cyan)' }}>*</span>
          </label>
          <input
            type="text"
            className="font-mono"
            value={formData.merchant_id || ''}
            onChange={(e) => onChange({ ...formData, merchant_id: e.target.value })}
            placeholder="MERCH_STORE_001"
            style={{
              padding: '8px 10px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
            }}
          />
          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>P3 persistence key</span>
        </div>

        {/* Baseline Window */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-secondary)' }}>
            Baseline Window
          </label>
          <select
            value={formData.baseline_window || 'previous_24h'}
            onChange={(e) => onChange({ ...formData, baseline_window: e.target.value })}
            style={{
              padding: '8px 10px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
            }}
          >
            <option value="previous_24h">Previous 24 Hours (Standard)</option>
            <option value="previous_7d">Previous 7 Days</option>
            <option value="previous_30d">Previous 30 Days</option>
          </select>
          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Historical benchmark timeframe</span>
        </div>

        {/* Current Window */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-secondary)' }}>
            Current Window
          </label>
          <select
            value={formData.current_window || 'latest_1h'}
            onChange={(e) => onChange({ ...formData, current_window: e.target.value })}
            style={{
              padding: '8px 10px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
            }}
          >
            <option value="latest_1h">Latest 1 Hour (Standard)</option>
            <option value="latest_2h">Latest 2 Hours</option>
            <option value="latest_30m">Latest 30 Minutes</option>
          </select>
          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Target evaluation timeframe</span>
        </div>
      </div>

      {/* 2-Column Side-by-Side: Baseline vs Current Window Metrics */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '18px',
        }}
      >
        {/* Left Column: Baseline Metrics */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            1. Baseline Historical Window
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Total Transactions</label>
              <input
                type="number"
                min="1"
                value={formData.baseline_tx_count ?? 2400}
                onChange={(e) => handleNumericChange('baseline_tx_count', e.target.value)}
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Fraud Count</label>
              <input
                type="number"
                min="0"
                value={formData.baseline_fraud_count ?? 24}
                onChange={(e) => handleNumericChange('baseline_fraud_count', e.target.value)}
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Distinct Devices</label>
              <input
                type="number"
                min="1"
                value={formData.baseline_device_count ?? 2000}
                onChange={(e) => handleNumericChange('baseline_device_count', e.target.value)}
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Auto Fraud Rate</label>
              <div
                className="font-mono"
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '12px',
                  color: 'var(--text-muted)',
                }}
              >
                {calculatedBaseRate}%
              </div>
            </div>
          </div>

          {/* Baseline Suspicious Score Slider */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)' }}>
              <span>Baseline Anomaly Score</span>
              <span className="font-mono" style={{ color: 'var(--accent-cyan)', fontWeight: '600' }}>
                {(formData.baseline_suspicious_score ?? 0.04).toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={formData.baseline_suspicious_score ?? 0.04}
              onChange={(e) => handleNumericChange('baseline_suspicious_score', e.target.value)}
              style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
            />
          </div>
        </div>

        {/* Right Column: Current Window Metrics */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--risk-medium)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            2. Current Target Window
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Total Transactions</label>
              <input
                type="number"
                min="1"
                value={formData.current_tx_count ?? 100}
                onChange={(e) => handleNumericChange('current_tx_count', e.target.value)}
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Fraud Count</label>
              <input
                type="number"
                min="0"
                value={formData.current_fraud_count ?? 1}
                onChange={(e) => handleNumericChange('current_fraud_count', e.target.value)}
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Distinct Devices</label>
              <input
                type="number"
                min="1"
                value={formData.current_device_count ?? 90}
                onChange={(e) => handleNumericChange('current_device_count', e.target.value)}
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Auto Fraud Rate</label>
              <div
                className="font-mono"
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '12px',
                  color: parseFloat(calculatedCurrRate) > 10 ? 'var(--risk-high)' : 'var(--text-primary)',
                  fontWeight: '600',
                }}
              >
                {calculatedCurrRate}%
              </div>
            </div>
          </div>

          {/* Current Suspicious Score Slider */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)' }}>
              <span>Current Anomaly Score</span>
              <span className="font-mono" style={{ color: 'var(--risk-medium)', fontWeight: '600' }}>
                {(formData.current_suspicious_score ?? 0.04).toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={formData.current_suspicious_score ?? 0.04}
              onChange={(e) => handleNumericChange('current_suspicious_score', e.target.value)}
              style={{ width: '100%', accentColor: 'var(--risk-medium)' }}
            />
          </div>
        </div>
      </div>

      {/* Manual Rate Override Drawer */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <button
          type="button"
          onClick={() => setOverrideRates(!overrideRates)}
          style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            cursor: 'pointer',
            alignSelf: 'flex-start',
          }}
        >
          <span>{overrideRates ? '▼ Hide Manual Rate Overrides' : '▶ Advanced: Manual Baseline / Current Rate Overrides'}</span>
        </button>

        {overrideRates && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px',
              padding: '12px',
              backgroundColor: 'var(--bg-app)',
              border: '1px dashed var(--border-muted)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Manual Baseline Fraud Rate (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                placeholder={calculatedBaseRate}
                value={formData.baseline_fraud_rate !== null && formData.baseline_fraud_rate !== undefined ? (formData.baseline_fraud_rate * 100).toFixed(2) : ''}
                onChange={(e) => handleRateChange('baseline_fraud_rate', e.target.value)}
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Manual Current Fraud Rate (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                placeholder={calculatedCurrRate}
                value={formData.current_fraud_rate !== null && formData.current_fraud_rate !== undefined ? (formData.current_fraud_rate * 100).toFixed(2) : ''}
                onChange={(e) => handleRateChange('current_fraud_rate', e.target.value)}
                style={{
                  padding: '6px 10px',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* P5 Five-Minute Telemetry Sub-Window Section */}
      <FiveMinuteTelemetryBuilder
        observations={formData.five_minute_telemetry || []}
        onChange={handleTelemetryChange}
        disabled={loading}
      />

      {/* Submit Action */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary"
          style={{ padding: '10px 24px', fontSize: '14px', minWidth: '200px' }}
        >
          {loading ? (
            <>
              <Loader2 size={16} className="spin" />
              <span>Analyzing Spike Radar...</span>
            </>
          ) : (
            <>
              <TrendingUp size={16} />
              <span>Assess Fraud Spike</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
};
