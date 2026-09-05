import React, { useState } from 'react';
import { FiveMinuteObservation } from '../../types/api';
import { Zap, Plus, Trash2, RotateCcw, Sparkles } from 'lucide-react';

interface FiveMinuteTelemetryBuilderProps {
  observations: FiveMinuteObservation[];
  onChange: (obs: FiveMinuteObservation[]) => void;
  disabled?: boolean;
}

export const FiveMinuteTelemetryBuilder: React.FC<FiveMinuteTelemetryBuilderProps> = ({
  observations,
  onChange,
  disabled = false,
}) => {
  const [newTimestamp, setNewTimestamp] = useState<string>('14:30');
  const [newTxCount, setNewTxCount] = useState<number>(10);
  const [newFraudCount, setNewFraudCount] = useState<number>(0);
  const [newDeviceCount, setNewDeviceCount] = useState<number>(10);

  const handleAddObservation = () => {
    if (observations.length >= 12) return;
    const fraudRate = newTxCount > 0 ? Math.min(1.0, newFraudCount / newTxCount) : 0.0;
    const newObs: FiveMinuteObservation = {
      timestamp: newTimestamp || `T-${(12 - observations.length) * 5}m`,
      tx_count: Math.max(1, newTxCount),
      fraud_count: Math.max(0, newFraudCount),
      fraud_rate: parseFloat(fraudRate.toFixed(4)),
      device_count: Math.max(1, newDeviceCount),
    };
    onChange([...observations, newObs]);
  };

  const handleRemoveObservation = (index: number) => {
    const updated = observations.filter((_, idx) => idx !== index);
    onChange(updated);
  };

  const handleClear = () => {
    onChange([]);
  };

  const handleGenerateBurst = () => {
    // Generate 6 realistic 5-min intervals with a sharp spike in the latest window
    const syntheticBurst: FiveMinuteObservation[] = [
      { timestamp: '14:00', tx_count: 8, fraud_count: 0, fraud_rate: 0.0, device_count: 8 },
      { timestamp: '14:05', tx_count: 10, fraud_count: 0, fraud_rate: 0.0, device_count: 9 },
      { timestamp: '14:10', tx_count: 7, fraud_count: 0, fraud_rate: 0.0, device_count: 7 },
      { timestamp: '14:15', tx_count: 9, fraud_count: 1, fraud_rate: 0.111, device_count: 8 },
      { timestamp: '14:20', tx_count: 12, fraud_count: 2, fraud_rate: 0.167, device_count: 10 },
      { timestamp: '14:25', tx_count: 48, fraud_count: 18, fraud_rate: 0.375, device_count: 18 },
    ];
    onChange(syntheticBurst);
  };

  const totalTx = observations.reduce((sum, o) => sum + (o.tx_count || 0), 0);
  const totalFraud = observations.reduce((sum, o) => sum + (o.fraud_count || 0), 0);
  const avgTx = observations.length > 0 ? totalTx / observations.length : 0;
  const currentObs = observations[observations.length - 1];
  const velocityRatio =
    observations.length >= 3 && avgTx > 0 && currentObs
      ? (currentObs.tx_count / (totalTx / observations.length)).toFixed(2)
      : '1.00';

  return (
    <div
      style={{
        padding: '18px',
        backgroundColor: 'var(--bg-app)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      {/* Header with Title and Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={16} color="var(--risk-medium)" />
            <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>
              P5: Five-Minute Sub-Window Telemetry Builder
            </h3>
            <span className="badge badge-medium" style={{ fontSize: '10px' }}>
              {observations.length} / 12 Windows
            </span>
          </div>
          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Sequence of 5-minute telemetry intervals for intra-hour velocity burst and short-window surge detection.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            disabled={disabled}
            onClick={handleGenerateBurst}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '5px 10px', gap: '5px' }}
            title="Generate synthetic 6-interval burst sequence for testing"
          >
            <Sparkles size={12} color="var(--accent-cyan)" />
            <span>Synthetic Burst Preset</span>
          </button>

          {observations.length > 0 && (
            <button
              type="button"
              disabled={disabled}
              onClick={handleClear}
              className="btn btn-secondary"
              style={{ fontSize: '11px', padding: '5px 8px', color: 'var(--status-offline)' }}
              title="Clear all observations"
            >
              <RotateCcw size={12} />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Observation Add Form Controls */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr)) 100px',
          gap: '10px',
          alignItems: 'flex-end',
          padding: '12px',
          backgroundColor: 'var(--bg-card)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Timestamp / Tag</label>
          <input
            type="text"
            className="font-mono"
            value={newTimestamp}
            onChange={(e) => setNewTimestamp(e.target.value)}
            disabled={disabled || observations.length >= 12}
            style={{
              padding: '6px 8px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
            }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Tx Count</label>
          <input
            type="number"
            min="1"
            value={newTxCount}
            onChange={(e) => setNewTxCount(parseInt(e.target.value) || 1)}
            disabled={disabled || observations.length >= 12}
            style={{
              padding: '6px 8px',
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
            value={newFraudCount}
            onChange={(e) => setNewFraudCount(parseInt(e.target.value) || 0)}
            disabled={disabled || observations.length >= 12}
            style={{
              padding: '6px 8px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
            }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Device Count</label>
          <input
            type="number"
            min="1"
            value={newDeviceCount}
            onChange={(e) => setNewDeviceCount(parseInt(e.target.value) || 1)}
            disabled={disabled || observations.length >= 12}
            style={{
              padding: '6px 8px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
            }}
          />
        </div>

        <button
          type="button"
          onClick={handleAddObservation}
          disabled={disabled || observations.length >= 12}
          className="btn btn-secondary"
          style={{ height: '34px', fontSize: '12px', gap: '4px' }}
        >
          <Plus size={14} />
          <span>Add</span>
        </button>
      </div>

      {/* Observations Table or Empty State */}
      {observations.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '12px',
                textAlign: 'left',
              }}
            >
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '6px 8px', fontWeight: '600' }}>#</th>
                  <th style={{ padding: '6px 8px', fontWeight: '600' }}>Timestamp</th>
                  <th style={{ padding: '6px 8px', fontWeight: '600' }}>Transactions</th>
                  <th style={{ padding: '6px 8px', fontWeight: '600' }}>Fraud Count</th>
                  <th style={{ padding: '6px 8px', fontWeight: '600' }}>Fraud Rate</th>
                  <th style={{ padding: '6px 8px', fontWeight: '600' }}>Devices</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {observations.map((obs, idx) => {
                  const isLatest = idx === observations.length - 1;
                  const rate =
                    obs.fraud_rate !== undefined && obs.fraud_rate !== null
                      ? (obs.fraud_rate * 100).toFixed(1)
                      : (((obs.fraud_count || 0) / (obs.tx_count || 1)) * 100).toFixed(1);

                  return (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        backgroundColor: isLatest ? 'rgba(56, 189, 248, 0.04)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '6px 8px', color: 'var(--text-muted)' }}>{idx + 1}</td>
                      <td className="font-mono" style={{ padding: '6px 8px', color: 'var(--text-primary)' }}>
                        {obs.timestamp || `T-${(observations.length - idx) * 5}m`}
                        {isLatest && (
                          <span style={{ marginLeft: '6px', fontSize: '9px', color: 'var(--accent-cyan)', fontWeight: '700' }}>
                            (LATEST)
                          </span>
                        )}
                      </td>
                      <td className="font-mono" style={{ padding: '6px 8px', fontWeight: '600' }}>
                        {obs.tx_count}
                      </td>
                      <td className="font-mono" style={{ padding: '6px 8px', color: (obs.fraud_count || 0) > 0 ? 'var(--risk-high)' : 'var(--text-muted)' }}>
                        {obs.fraud_count || 0}
                      </td>
                      <td className="font-mono" style={{ padding: '6px 8px' }}>
                        {rate}%
                      </td>
                      <td className="font-mono" style={{ padding: '6px 8px', color: 'var(--text-secondary)' }}>
                        {obs.device_count || 1}
                      </td>
                      <td style={{ padding: '6px 8px', textAlign: 'right' }}>
                        <button
                          type="button"
                          disabled={disabled}
                          onClick={() => handleRemoveObservation(idx)}
                          style={{ color: 'var(--text-muted)', cursor: 'pointer', padding: '2px' }}
                          title="Remove observation"
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Telemetry Summary Stats */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 12px',
              backgroundColor: 'var(--bg-card)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '11px',
              color: 'var(--text-secondary)',
              flexWrap: 'wrap',
              gap: '8px',
            }}
          >
            <span>
              Total Sub-Window Tx: <strong style={{ color: 'var(--text-primary)' }}>{totalTx}</strong> • Fraud: <strong style={{ color: 'var(--risk-high)' }}>{totalFraud}</strong>
            </span>
            <span>
              Calculated Velocity Ratio: <strong className="font-mono" style={{ color: 'var(--accent-cyan)' }}>{velocityRatio}x</strong>
            </span>
          </div>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '16px', color: 'var(--text-muted)', fontSize: '12px' }}>
          No 5-minute telemetry intervals added yet. Use the controls above or click &ldquo;Synthetic Burst Preset&rdquo;.
        </div>
      )}
    </div>
  );
};
