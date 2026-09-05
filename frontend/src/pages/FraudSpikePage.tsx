import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FraudSpikeRequest,
  LiveFraudSpikeTelemetryResponse,
} from '../types/api';
import { riskApi, ApiError } from '../services/api';
import { useRiskFeed } from '../context/RiskFeedContext';
import { FraudScenarioPresets, FraudPreset } from '../components/fraud-spike/FraudScenarioPresets';
import { FraudSpikeForm } from '../components/fraud-spike/FraudSpikeForm';
import {
  TrendingUp,
  AlertOctagon,
  RotateCcw,
  RefreshCw,
  Radio,
  Clock,
  Activity,
  Layers,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Loader2,
  AlertCircle,
  Cpu,
} from 'lucide-react';

const DEFAULT_MANUAL_FORM: FraudSpikeRequest = {
  merchant_id: 'MERCH_DEFAULT_RETAIL_01',
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
};

const SESSION_RESULT_KEY = 'ai_risk_last_fraud_spike_result';

export const FraudSpikePage: React.FC = () => {
  const navigate = useNavigate();
  const { addEvent } = useRiskFeed();

  // Live Telemetry state (15s calm auto-polling)
  const [liveTelemetry, setLiveTelemetry] = useState<LiveFraudSpikeTelemetryResponse | null>(null);
  const [liveLoading, setLiveLoading] = useState<boolean>(false);

  // Assessment & simulation states
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [evaluatingTarget, setEvaluatingTarget] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Manual simulation collapsed accordion
  const [showManualSection, setShowManualSection] = useState<boolean>(false);
  const [manualFormData, setManualFormData] = useState<FraudSpikeRequest>(DEFAULT_MANUAL_FORM);
  const [selectedPresetId, setSelectedPresetId] = useState<string | undefined>(undefined);
  const [manualLoading, setManualLoading] = useState<boolean>(false);

  // Fetch live rolling telemetry
  const fetchLiveTelemetry = async (silent: boolean = false) => {
    try {
      if (!silent) setLiveLoading(true);
      const data = await riskApi.getLiveFraudTelemetry();
      setLiveTelemetry(data);
    } catch (err) {
      console.warn('Unable to poll live fraud spike telemetry:', err);
    } finally {
      if (!silent) setLiveLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveTelemetry();
    const interval = setInterval(() => {
      fetchLiveTelemetry(true);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Action: Evaluate Live Telemetry with frozen FraudSpikeDetector
  const handleEvaluateLive = async () => {
    try {
      setEvaluating(true);
      setEvaluatingTarget('Live Razorpay Webhook Telemetry');
      setError(null);

      const res = await riskApi.evaluateLiveFraudSpike();
      const assessmentTimestamp = new Date().toISOString();

      const assessmentPayload = {
        result: res,
        formData: liveTelemetry?.synthesized_request || {},
        timestamp: assessmentTimestamp,
        source: 'LIVE_RAZORPAY_WEBHOOK',
      };

      try {
        sessionStorage.setItem(SESSION_RESULT_KEY, JSON.stringify(assessmentPayload));
      } catch {
        // Fallback
      }

      // Emit live event to Risk Operations session feed
      addEvent({
        engine: 'FRAUD_SPIKE',
        source: 'LIVE_ASSESSMENT',
        title: `Live Velocity Assessment (${res.spike_level})`,
        entityId: liveTelemetry?.merchant_id || 'MERCH_RAZORPAY_TEST',
        entityType: 'MERCHANT',
        severity: res.spike_level,
        score: res.spike_score,
        decision: res.recommended_action,
        rawMl: {
          probability: res.raw_spike_probability !== null ? res.raw_spike_probability : undefined,
          score: res.raw_spike_score !== null ? res.raw_spike_score : undefined,
        },
        evidence: res.spike_factors,
        telemetry: {
          burstRatio: res.five_minute_velocity_ratio !== null ? res.five_minute_velocity_ratio : undefined,
          consecutiveWindows: res.consecutive_anomaly_windows,
          observationCount: res.five_minute_observation_count,
          currentTxCount: res.five_minute_current_tx_count,
          baselineFraudRate: res.baseline_fraud_rate,
          currentFraudRate: res.current_fraud_rate,
          fraudRateChange: res.fraud_rate_change,
          evidenceQuality: res.evidence_quality,
          guardrailTriggered: res.guardrail_triggered || res.five_minute_guardrail_triggered,
          spikeFactors: res.spike_factors,
          mitigatingFactors: res.mitigating_factors,
          explanation: res.explanation,
        },
      });

      navigate('/fraud-spike/result', { state: assessmentPayload });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(`API Error (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to evaluate live fraud spike telemetry.');
      }
    } finally {
      setEvaluating(false);
      setEvaluatingTarget(null);
    }
  };

  // Action: Run Benchmark / Offline Simulation
  const handleRunSimulation = async (preset: FraudPreset) => {
    try {
      setEvaluating(true);
      setEvaluatingTarget(`Benchmark Scenario: ${preset.name}`);
      setError(null);

      const res = await riskApi.detectFraudSpike(preset.data);
      const assessmentTimestamp = new Date().toISOString();

      const assessmentPayload = {
        result: res,
        formData: preset.data,
        timestamp: assessmentTimestamp,
        source: 'MANUAL_SYNTHETIC_SIMULATION',
      };

      try {
        sessionStorage.setItem(SESSION_RESULT_KEY, JSON.stringify(assessmentPayload));
      } catch {
        // Fallback
      }

      addEvent({
        engine: 'FRAUD_SPIKE',
        source: 'SIMULATION',
        title: `Benchmark Velocity (${preset.name})`,
        entityId: preset.data.merchant_id || 'MERCH_SYNTH',
        entityType: 'MERCHANT',
        severity: res.spike_level,
        score: res.spike_score,
        decision: res.recommended_action,
        rawMl: {
          probability: res.raw_spike_probability !== null ? res.raw_spike_probability : undefined,
          score: res.raw_spike_score !== null ? res.raw_spike_score : undefined,
        },
        evidence: res.spike_factors,
        telemetry: {
          burstRatio: res.five_minute_velocity_ratio !== null ? res.five_minute_velocity_ratio : undefined,
          consecutiveWindows: res.consecutive_anomaly_windows,
          observationCount: res.five_minute_observation_count,
          currentTxCount: res.five_minute_current_tx_count,
          baselineFraudRate: res.baseline_fraud_rate,
          currentFraudRate: res.current_fraud_rate,
          fraudRateChange: res.fraud_rate_change,
          evidenceQuality: res.evidence_quality,
          guardrailTriggered: res.guardrail_triggered || res.five_minute_guardrail_triggered,
          spikeFactors: res.spike_factors,
          mitigatingFactors: res.mitigating_factors,
          explanation: res.explanation,
        },
      });

      navigate('/fraud-spike/result', { state: assessmentPayload });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(`API Error (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to run benchmark simulation.');
      }
    } finally {
      setEvaluating(false);
      setEvaluatingTarget(null);
    }
  };

  // Action: Manual Temporal Simulation Form Submit
  const handleManualAssess = async () => {
    try {
      setManualLoading(true);
      setError(null);

      const res = await riskApi.detectFraudSpike(manualFormData);
      const assessmentTimestamp = new Date().toISOString();

      const assessmentPayload = {
        result: res,
        formData: manualFormData,
        timestamp: assessmentTimestamp,
        source: 'MANUAL_SYNTHETIC_SIMULATION',
      };

      try {
        sessionStorage.setItem(SESSION_RESULT_KEY, JSON.stringify(assessmentPayload));
      } catch {
        // Fallback
      }

      addEvent({
        engine: 'FRAUD_SPIKE',
        source: selectedPresetId ? 'SIMULATION' : 'MANUAL_INVESTIGATION',
        title: `Manual Velocity Assessment (${manualFormData.merchant_id || 'MERCHANT'})`,
        entityId: manualFormData.merchant_id || 'MERCH_DEFAULT',
        entityType: 'MERCHANT',
        severity: res.spike_level,
        score: res.spike_score,
        decision: res.recommended_action,
        rawMl: {
          probability: res.raw_spike_probability !== null ? res.raw_spike_probability : undefined,
          score: res.raw_spike_score !== null ? res.raw_spike_score : undefined,
        },
        evidence: res.spike_factors,
        telemetry: {
          burstRatio: res.five_minute_velocity_ratio !== null ? res.five_minute_velocity_ratio : undefined,
          consecutiveWindows: res.consecutive_anomaly_windows,
          observationCount: res.five_minute_observation_count,
          currentTxCount: res.five_minute_current_tx_count,
          baselineFraudRate: res.baseline_fraud_rate,
          currentFraudRate: res.current_fraud_rate,
          fraudRateChange: res.fraud_rate_change,
          evidenceQuality: res.evidence_quality,
          guardrailTriggered: res.guardrail_triggered || res.five_minute_guardrail_triggered,
          spikeFactors: res.spike_factors,
          mitigatingFactors: res.mitigating_factors,
          explanation: res.explanation,
        },
      });

      navigate('/fraud-spike/result', { state: assessmentPayload });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(`API Error (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to run manual temporal assessment.');
      }
    } finally {
      setManualLoading(false);
    }
  };

  const isLiveActive = liveTelemetry?.status === 'ACTIVE';
  const totalEvents = liveTelemetry?.total_events_processed ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={22} color="var(--risk-medium)" />
            <h1 style={{ fontSize: '22px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Fraud Spike Sentinel
            </h1>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              className={`badge ${isLiveActive ? 'badge-green' : 'badge-amber'}`}
              style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '10px' }}
            >
              <Radio size={10} className={isLiveActive ? 'pulse' : ''} />
              <span>{isLiveActive ? 'LIVE MONITOR ACTIVE' : 'IDLE — WAITING FOR WEBHOOKS'}</span>
            </span>
            <span className="badge badge-cyan" style={{ fontSize: '10px' }}>LIVE / RAZORPAY WEBHOOK</span>
            <span className="badge badge-purple" style={{ fontSize: '10px' }}>Rolling 5m/1h Radar</span>
          </div>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Real-time transaction velocity surveillance and temporal burst detection fed continuously by verified Razorpay Test Mode webhooks.
        </p>
      </div>

      {/* Evaluating Status Banner */}
      {evaluating && (
        <div
          style={{
            padding: '16px 20px',
            backgroundColor: 'rgba(245, 158, 11, 0.12)',
            border: '1px solid var(--risk-medium)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            color: 'var(--text-primary)',
          }}
        >
          <Loader2 size={18} className="spin" color="var(--risk-medium)" />
          <div>
            <div style={{ fontWeight: '700', fontSize: '13px', color: 'var(--risk-medium)' }}>
              Evaluating Temporal Velocity with Fraud Spike Engine...
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              Target: {evaluatingTarget || 'Live Telemetry'}. Computing rolling baseline ratio, P1 fraud delta floor, and P5 sub-window burst metrics.
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div
          style={{
            padding: '14px 18px',
            backgroundColor: 'var(--risk-high-bg)',
            border: '1px solid var(--risk-high-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--risk-high)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '13px',
          }}
        >
          <AlertOctagon size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* SECTION A — LIVE FRAUD SPIKE MONITOR */}
      <div
        className="card"
        style={{
          padding: '22px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          border: '1px solid var(--border-color)',
          background: 'linear-gradient(180deg, rgba(245, 158, 11, 0.04) 0%, rgba(15, 23, 42, 0.6) 100%)',
        }}
      >
        {/* Radar Top Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={18} color="var(--risk-medium)" />
              <h2 style={{ fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                LIVE FRAUD TELEMETRY RADAR
              </h2>
              <span className="badge badge-cyan" style={{ fontSize: '10px' }}>
                {liveTelemetry?.merchant_id || 'MERCH_RAZORPAY_TEST'}
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Continuous rolling telemetry from incoming payment webhooks. Discretizes velocity into rolling 5m and 1h windows with zero manual data entry.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Auto-polling: 15s
            </span>
            <button
              onClick={() => fetchLiveTelemetry(false)}
              disabled={liveLoading}
              className="btn btn-secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}
              title="Refresh live rolling telemetry"
            >
              <RefreshCw size={13} className={liveLoading ? 'spin' : ''} />
              <span>Refresh Live Radar</span>
            </button>
          </div>
        </div>

        {/* Live Metrics Strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
          {/* 5-Min Transactions */}
          <div style={{ padding: '12px 14px', backgroundColor: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
              <Clock size={13} color="var(--accent-cyan)" />
              <span>5-Min Transactions</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--accent-cyan)', marginTop: '4px' }}>
              {liveTelemetry?.rolling_5m?.tx_count ?? 0}
            </div>
          </div>

          {/* 5-Min Volume */}
          <div style={{ padding: '12px 14px', backgroundColor: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
              <span>5-Min Volume</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '4px' }}>
              ₹{Number(liveTelemetry?.rolling_5m?.tx_volume ?? 0).toLocaleString()}
            </div>
          </div>

          {/* 1-Hour Transactions */}
          <div style={{ padding: '12px 14px', backgroundColor: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
              <Layers size={13} color="var(--risk-medium)" />
              <span>1-Hour Transactions</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '4px' }}>
              {liveTelemetry?.rolling_1h?.tx_count ?? 0}
            </div>
          </div>

          {/* 1-Hour Volume */}
          <div style={{ padding: '12px 14px', backgroundColor: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
              <span>1-Hour Volume</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '4px' }}>
              ₹{Number(liveTelemetry?.rolling_1h?.tx_volume ?? 0).toLocaleString()}
            </div>
          </div>

          {/* Failed Payments */}
          <div
            style={{ padding: '12px 14px', backgroundColor: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
            title="Operational payment failures. Failed payments are never equated with fraud without explicit application note."
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
              <AlertCircle size={13} color="var(--risk-medium)" />
              <span>Failed Payments</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--risk-medium)', marginTop: '4px' }}>
              {liveTelemetry?.rolling_1h?.failed_count ?? 0}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
              {liveTelemetry?.rolling_5m?.failed_count ?? 0} in last 5m
            </div>
          </div>

          {/* Explicit Fraud Signals */}
          <div
            style={{ padding: '12px 14px', backgroundColor: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
            title="Explicit fraud notes (notes.is_fraud = true). Never fabricated."
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
              <ShieldCheck size={13} color="var(--risk-high)" />
              <span>Explicit Fraud Signals</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--risk-high)', marginTop: '4px' }}>
              {liveTelemetry?.rolling_1h?.fraud_count ?? 0}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Strictly verified notes
            </div>
          </div>
        </div>

        {/* Five-Minute Velocity Buckets & Evaluation Action */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h3 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                Five-Minute Velocity Buckets (Latest 1 Hour)
              </h3>
              <p style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                Contiguous 5-minute observation windows feeding the P5 sub-window velocity guardrail.
              </p>
            </div>

            <button
              onClick={handleEvaluateLive}
              disabled={evaluating}
              className="btn btn-primary"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 18px',
                fontSize: '12px',
                fontWeight: '700',
              }}
            >
              {evaluating ? (
                <>
                  <Loader2 size={14} className="spin" />
                  <span>Evaluating Live Telemetry...</span>
                </>
              ) : (
                <>
                  <span>Evaluate Live Fraud Spike</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </div>

          {/* Table or Empty State */}
          {!isLiveActive && totalEvents === 0 ? (
            <div
              style={{
                padding: '24px 18px',
                textAlign: 'center',
                backgroundColor: 'rgba(15, 23, 42, 0.4)',
                borderRadius: 'var(--radius-md)',
                border: '1px dashed var(--border-color)',
              }}
            >
              <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-secondary)' }}>
                NO LIVE WEBHOOK ACTIVITY
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Waiting for verified Razorpay payment events. Send a test payment or run benchmark simulation below.
              </div>
            </div>
          ) : (
            <div
              style={{
                overflowX: 'auto',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(15, 23, 42, 0.4)',
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', backgroundColor: 'rgba(30, 41, 59, 0.4)', textAlign: 'left' }}>
                    <th style={{ padding: '10px 14px', color: 'var(--text-muted)', fontWeight: '600' }}>Time Window</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-muted)', fontWeight: '600' }}>Transactions</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-muted)', fontWeight: '600' }}>Failed Payments</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-muted)', fontWeight: '600' }}>Explicit Fraud</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-muted)', fontWeight: '600' }}>Fraud Rate</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-muted)', fontWeight: '600' }}>Devices</th>
                  </tr>
                </thead>
                <tbody>
                  {(liveTelemetry?.five_minute_observations || []).slice(-8).map((bucket, idx) => (
                    <tr
                      key={`${bucket.timestamp}_${idx}`}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                        backgroundColor: bucket.tx_count > 0 ? 'rgba(6, 182, 212, 0.03)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '8px 14px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                        {bucket.timestamp}
                      </td>
                      <td style={{ padding: '8px 14px', fontWeight: '700', color: bucket.tx_count > 0 ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                        {bucket.tx_count}
                      </td>
                      <td style={{ padding: '8px 14px', color: (bucket.failed_count ?? 0) > 0 ? 'var(--risk-medium)' : 'var(--text-muted)' }}>
                        {bucket.failed_count ?? 0}
                      </td>
                      <td style={{ padding: '8px 14px', color: (bucket.fraud_count ?? 0) > 0 ? 'var(--risk-high)' : 'var(--text-muted)' }}>
                        {bucket.fraud_count ?? 0}
                      </td>
                      <td style={{ padding: '8px 14px', color: (bucket.fraud_rate ?? 0) > 0 ? 'var(--risk-high)' : 'var(--text-muted)' }}>
                        {bucket.fraud_rate !== null && bucket.fraud_rate !== undefined ? `${(bucket.fraud_rate * 100).toFixed(1)}%` : '0.0%'}
                      </td>
                      <td style={{ padding: '8px 14px', color: 'var(--text-secondary)' }}>
                        {bucket.device_count !== null && bucket.device_count !== undefined ? bucket.device_count : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* SECTION B — BENCHMARK SCENARIOS */}
      <FraudScenarioPresets
        onSelect={(presetData) => {
          setManualFormData(presetData);
          setShowManualSection(true);
        }}
        onRunSimulation={handleRunSimulation}
        selectedId={selectedPresetId}
      />

      {/* SECTION C — ADVANCED MANUAL SIMULATION (Collapsed by default) */}
      <div
        className="card"
        style={{
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-color)',
          overflow: 'hidden',
        }}
      >
        <button
          onClick={() => setShowManualSection((prev) => !prev)}
          style={{
            width: '100%',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--text-primary)',
            textAlign: 'left',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={16} color="var(--accent-purple)" />
            <span style={{ fontSize: '13px', fontWeight: '700' }}>
              Advanced: Manual Temporal Simulation & Window Tuning
            </span>
            <span className="badge badge-purple" style={{ fontSize: '10px' }}>
              MANUAL / SYNTHETIC SIMULATION
            </span>
          </div>
          {showManualSection ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
        </button>

        {showManualSection && (
          <div style={{ padding: '0 18px 18px 18px', borderTop: '1px solid var(--border-color)', paddingTop: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  Manual Temporal Window Parameters
                </h3>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                  Tune baseline vs current window observations or test hypothetical velocity surges.
                </p>
              </div>

              <button
                onClick={() => {
                  setManualFormData(DEFAULT_MANUAL_FORM);
                  setSelectedPresetId(undefined);
                }}
                className="btn btn-secondary"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}
              >
                <RotateCcw size={13} />
                <span>Reset Form</span>
              </button>
            </div>

            <FraudSpikeForm
              formData={manualFormData}
              onChange={(newData) => {
                setManualFormData(newData);
                setSelectedPresetId(undefined);
              }}
              onSubmit={handleManualAssess}
              onReset={() => {
                setManualFormData(DEFAULT_MANUAL_FORM);
                setSelectedPresetId(undefined);
              }}
              loading={manualLoading}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default FraudSpikePage;
