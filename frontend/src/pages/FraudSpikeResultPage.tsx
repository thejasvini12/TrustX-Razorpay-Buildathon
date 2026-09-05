import React, { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { FraudSpikeRequest, FraudSpikeResponse } from '../types/api';
import { RawVsPolicyPanel } from '../components/fraud-spike/RawVsPolicyPanel';
import { GuardrailPanel } from '../components/fraud-spike/GuardrailPanel';
import { PersistencePanel } from '../components/fraud-spike/PersistencePanel';
import { TelemetryResultPanel } from '../components/fraud-spike/TelemetryResultPanel';
import { SpikeArchitectureFlow } from '../components/fraud-spike/SpikeArchitectureFlow';
import {
  TrendingUp,
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Layers,
  ChevronDown,
  ChevronUp,
  Cpu,
  Zap,
  Building2,
  Clock,
  ExternalLink,
} from 'lucide-react';

const SESSION_RESULT_KEY = 'ai_risk_last_fraud_spike_result';

interface StoredAssessmentData {
  result: FraudSpikeResponse;
  formData: FraudSpikeRequest;
  timestamp: string;
  source?: 'LIVE_RAZORPAY_WEBHOOK' | 'MANUAL_SYNTHETIC_SIMULATION' | string;
}

function getInitialData(locationState: any): StoredAssessmentData | null {
  if (locationState && locationState.result) {
    return {
      result: locationState.result,
      formData: locationState.formData || {},
      timestamp: locationState.timestamp || new Date().toISOString(),
      source: locationState.source || 'MANUAL_SYNTHETIC_SIMULATION',
    };
  }
  try {
    const raw = sessionStorage.getItem(SESSION_RESULT_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.result) {
        return {
          result: parsed.result,
          formData: parsed.formData || {},
          timestamp: parsed.timestamp || new Date().toISOString(),
          source: parsed.source || 'MANUAL_SYNTHETIC_SIMULATION',
        };
      }
    }
  } catch {
    // Non-blocking fallback
  }
  return null;
}

export const FraudSpikeResultPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const [data] = useState<StoredAssessmentData | null>(() => getInitialData(location.state));

  // Collapsible diagnostics state
  const [openSection, setOpenSection] = useState<{
    rawMl: boolean;
    p1: boolean;
    p3: boolean;
    p5: boolean;
    pipeline: boolean;
  }>({
    rawMl: false,
    p1: false,
    p3: false,
    p5: false,
    pipeline: false,
  });

  const toggleSection = (key: keyof typeof openSection) => {
    setOpenSection((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Safe fallback if assessment data is not available
  if (!data || !data.result) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '800px', margin: '40px auto' }}>
        <div className="card" style={{ padding: '36px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: 'rgba(245, 158, 11, 0.12)',
              color: 'var(--risk-medium)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <AlertTriangle size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Assessment Result Unavailable
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '6px', maxWidth: '460px', lineHeight: '1.5' }}>
              No active fraud spike assessment was found in this session. Configure and run an assessment to inspect velocity and fraud-rate behavior.
            </p>
          </div>
          <button
            onClick={() => navigate('/fraud-spike')}
            className="btn btn-primary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '9px 18px', fontSize: '13px' }}
          >
            <ArrowLeft size={14} />
            <span>Go to Fraud Spike Radar</span>
          </button>
        </div>
      </div>
    );
  }

  const { result, formData, timestamp } = data;

  const severityColor =
    result.spike_level === 'HIGH'
      ? 'var(--risk-high)'
      : result.spike_level === 'MEDIUM'
      ? 'var(--risk-medium)'
      : 'var(--risk-low)';

  const severityBg =
    result.spike_level === 'HIGH'
      ? 'var(--risk-high-bg)'
      : result.spike_level === 'MEDIUM'
      ? 'var(--risk-medium-bg)'
      : 'var(--risk-low-bg)';

  const severityBorder =
    result.spike_level === 'HIGH'
      ? 'var(--risk-high-border)'
      : result.spike_level === 'MEDIUM'
      ? 'var(--risk-medium-border)'
      : 'var(--risk-low-border)';

  const severityBadgeClass =
    result.spike_level === 'HIGH'
      ? 'badge-rose'
      : result.spike_level === 'MEDIUM'
      ? 'badge-amber'
      : 'badge-green';

  const formattedTimestamp = new Date(timestamp).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'medium',
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      {/* 1. Page Header & Breadcrumb */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <Link
              to="/fraud-spike"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                color: 'var(--text-secondary)',
                textDecoration: 'none',
              }}
            >
              <ArrowLeft size={13} />
              <span>Back to Fraud Spike</span>
            </Link>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: severityBg,
                border: `1px solid ${severityBorder}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: severityColor,
              }}
            >
              <TrendingUp size={18} />
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Fraud Spike Assessment
            </h1>

            {data.source === 'LIVE_RAZORPAY_WEBHOOK' ? (
              <span
                className="badge badge-cyan"
                style={{ fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
              >
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--accent-cyan)' }} />
                <span>LIVE / RAZORPAY WEBHOOK</span>
              </span>
            ) : (
              <span className="badge badge-purple" style={{ fontSize: '11px' }}>
                MANUAL / SYNTHETIC SIMULATION
              </span>
            )}
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Operational assessment of merchant velocity and fraud-rate behavior
          </p>
        </div>

        {/* Action Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <button
            onClick={() => navigate('/fraud-spike')}
            className="btn btn-secondary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', padding: '6px 12px' }}
          >
            <RotateCcw size={13} />
            <span>Run Another Assessment</span>
          </button>
          <button
            onClick={() => navigate('/risk-operations')}
            className="btn btn-primary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', padding: '6px 14px' }}
          >
            <span>View in Risk Operations</span>
            <ExternalLink size={13} />
          </button>
        </div>
      </div>

      {/* 2. Top Summary Card */}
      <div
        className="card"
        style={{
          padding: '20px 24px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '20px',
          borderLeft: `4px solid ${severityColor}`,
        }}
      >
        <div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Merchant Identifier
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
            <Building2 size={15} color="var(--accent-cyan)" />
            <span style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
              {result.merchant_id || formData.merchant_id || 'MERCHANT_GLOBAL'}
            </span>
          </div>
        </div>

        <div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Assessment Timestamp
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
            <Clock size={15} color="var(--text-secondary)" />
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {formattedTimestamp}
            </span>
          </div>
        </div>

        <div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Risk Level
          </span>
          <div style={{ marginTop: '4px' }}>
            <span className={`badge ${severityBadgeClass}`} style={{ fontSize: '12px', padding: '3px 10px' }}>
              {result.spike_level} RISK
            </span>
          </div>
        </div>

        <div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Fraud Spike Score
          </span>
          <div style={{ marginTop: '4px', display: 'flex', alignItems: 'baseline', gap: '4px' }}>
            <span style={{ fontSize: '20px', fontWeight: '800', color: severityColor, fontFamily: 'JetBrains Mono, monospace' }}>
              {result.spike_score}
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>/ 100</span>
          </div>
        </div>

        <div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Posterior Probability
          </span>
          <div style={{ marginTop: '4px' }}>
            <span style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
              {(result.spike_probability * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* 3. Main Decision Card */}
      <div
        className="card"
        style={{
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          backgroundColor: 'rgba(10, 25, 47, 0.7)',
          border: '1px solid rgba(0, 210, 255, 0.3)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.08em', color: '#00d2ff', textTransform: 'uppercase' }}>
              SYSTEM RECOMMENDED ACTION
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(255, 255, 255, 0.08)', color: 'var(--text-secondary)' }}>
              Operational Directive
            </span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Confidence: <strong style={{ color: 'var(--text-primary)' }}>{result.confidence}</strong>
          </span>
        </div>

        <div
          style={{
            fontSize: '18px',
            fontWeight: '800',
            color: severityColor,
            fontFamily: 'JetBrains Mono, monospace',
            letterSpacing: '0.02em',
            padding: '12px 16px',
            backgroundColor: 'var(--bg-app)',
            borderRadius: 'var(--radius-sm)',
            border: `1px solid ${severityBorder}`,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '10px',
            width: 'fit-content',
          }}
        >
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: severityColor }} />
          <span>{result.recommended_action}</span>
        </div>

        <p style={{ fontSize: '13.5px', color: 'var(--text-primary)', lineHeight: '1.5', maxWidth: '850px' }}>
          {result.explanation}
        </p>
      </div>

      {/* 4. Risk Status Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '14px',
        }}
      >
        <div className="card" style={{ padding: '16px' }}>
          <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Spike Level
          </span>
          <div style={{ fontSize: '16px', fontWeight: '700', color: severityColor, marginTop: '4px' }}>
            {result.spike_level}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
            Score: {result.spike_score}/100
          </span>
        </div>

        <div className="card" style={{ padding: '16px' }}>
          <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Spike Classification
          </span>
          <div style={{ fontSize: '16px', fontWeight: '700', color: result.spike_prediction === 1 ? 'var(--risk-high)' : 'var(--risk-low)', marginTop: '4px' }}>
            {result.spike_prediction === 1 ? 'SPIKE DETECTED' : 'NORMAL / NO SPIKE'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
            Binary model verdict ({result.spike_prediction})
          </span>
        </div>

        <div className="card" style={{ padding: '16px' }}>
          <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Evidence Quality
          </span>
          <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--accent-cyan)', marginTop: '4px' }}>
            {result.evidence_quality}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
            Confidence: {result.confidence}
          </span>
        </div>

        <div className="card" style={{ padding: '16px' }}>
          <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Observation Window
          </span>
          <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '4px', fontFamily: 'JetBrains Mono, monospace' }}>
            {result.current_window}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
            Baseline: {result.baseline_window}
          </span>
        </div>
      </div>

      {/* 5. "Why did the system make this decision?" */}
      <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Why did the system make this decision?
            </h3>
          </div>
          <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Synthesized factors, rate deltas, and evidence signals derived across evaluation windows.
          </p>
        </div>

        {/* Evidence Summary Text */}
        {result.evidence_summary && (
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: 'var(--bg-app)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              fontSize: '13px',
              color: 'var(--text-secondary)',
              lineHeight: '1.45',
            }}
          >
            {result.evidence_summary}
          </div>
        )}

        {/* Key Numerical Benchmarks */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
          <div style={{ padding: '12px', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Fraud Rate Change (Δ)</span>
            <div style={{ fontSize: '16px', fontWeight: '700', color: result.fraud_rate_change >= 0.15 ? 'var(--risk-high)' : result.fraud_rate_change > 0 ? 'var(--risk-medium)' : 'var(--risk-low)', marginTop: '4px', fontFamily: 'JetBrains Mono, monospace' }}>
              {result.fraud_rate_change >= 0 ? '+' : ''}{(result.fraud_rate_change * 100).toFixed(2)}%
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Baseline: {(result.baseline_fraud_rate * 100).toFixed(2)}% → Current: {(result.current_fraud_rate * 100).toFixed(2)}%
            </span>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Transaction Velocity</span>
            <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '4px', fontFamily: 'JetBrains Mono, monospace' }}>
              {formData.current_tx_count ?? result.five_minute_current_tx_count ?? 'N/A'} tx
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Baseline volume: {formData.baseline_tx_count ?? 'N/A'} tx
            </span>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Device/Transaction Ratio</span>
            <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '4px', fontFamily: 'JetBrains Mono, monospace' }}>
              {formData.current_device_count ?? 'N/A'} devices
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Baseline: {formData.baseline_device_count ?? 'N/A'} devices
            </span>
          </div>
        </div>

        {/* Observed Signals List */}
        {result.spike_factors && result.spike_factors.length > 0 && (
          <div>
            <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Observed Risk Signals ({result.spike_factors.length})
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
              {result.spike_factors.map((factor, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-app)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '12.5px',
                    color: 'var(--text-primary)',
                  }}
                >
                  <span style={{ color: severityColor, marginTop: '2px' }}>•</span>
                  <span>{factor}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Mitigating Factors (if present) */}
        {result.mitigating_factors && result.mitigating_factors.length > 0 && (
          <div>
            <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--risk-low)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Mitigating Signals ({result.mitigating_factors.length})
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
              {result.mitigating_factors.map((factor, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '8px 12px',
                    backgroundColor: 'rgba(16, 185, 129, 0.08)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(16, 185, 129, 0.2)',
                    fontSize: '12.5px',
                    color: 'var(--text-primary)',
                  }}
                >
                  <CheckCircle2 size={14} color="var(--risk-low)" style={{ marginTop: '2px', flexShrink: 0 }} />
                  <span>{factor}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 6. Guardrail Status Section */}
      <div>
        <div style={{ marginBottom: '12px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>
            Deterministic Guardrails & Telemetry Status
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Operational defense floors operating in parallel with the machine learning velocity estimator.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
          {/* P1 Compact Card */}
          <div
            className="card"
            style={{
              padding: '16px',
              borderLeft: result.guardrail_triggered ? '4px solid var(--risk-high)' : '4px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '10px',
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12.5px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  P1 Fraud-Rate Delta Floor
                </span>
                <span className={`badge ${result.guardrail_triggered ? 'badge-rose' : 'badge-green'}`} style={{ fontSize: '10px' }}>
                  {result.guardrail_triggered ? 'Triggered' : 'Not Triggered'}
                </span>
              </div>
              <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                Floor threshold: Δ ≥ 15%. Observed change:{' '}
                <strong style={{ color: result.fraud_rate_change >= 0.15 ? 'var(--risk-high)' : 'var(--text-primary)' }}>
                  {(result.fraud_rate_change * 100).toFixed(1)}%
                </strong>
              </p>
            </div>
            <button
              type="button"
              onClick={() => toggleSection('p1')}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-cyan)',
                fontSize: '11.5px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: 0,
                alignSelf: 'flex-start',
              }}
            >
              <span>{openSection.p1 ? 'Hide Details' : 'View Details'}</span>
              {openSection.p1 ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          </div>

          {/* P3 Compact Card */}
          <div
            className="card"
            style={{
              padding: '16px',
              borderLeft: result.persistence_escalation_triggered
                ? '4px solid var(--risk-critical)'
                : (result.consecutive_anomaly_windows ?? 0) > 0
                ? '4px solid var(--accent-cyan)'
                : '4px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '10px',
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12.5px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  P3 Multi-Window Persistence
                </span>
                <span
                  className={`badge ${
                    result.persistence_escalation_triggered
                      ? 'badge-purple'
                      : (result.consecutive_anomaly_windows ?? 0) > 0
                      ? 'badge-cyan'
                      : 'badge-green'
                  }`}
                  style={{ fontSize: '10px' }}
                >
                  {result.persistence_escalation_triggered
                    ? 'Escalation Triggered'
                    : (result.consecutive_anomaly_windows ?? 0) > 0
                    ? `Active — ${result.consecutive_anomaly_windows} ${result.consecutive_anomaly_windows === 1 ? 'window' : 'windows'}`
                    : 'Inactive'}
                </span>
              </div>
              <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                Consecutive anomalous observation windows:{' '}
                <strong>{result.consecutive_anomaly_windows ?? 0}</strong>
              </p>
            </div>
            <button
              type="button"
              onClick={() => toggleSection('p3')}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-cyan)',
                fontSize: '11.5px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: 0,
                alignSelf: 'flex-start',
              }}
            >
              <span>{openSection.p3 ? 'Hide Details' : 'View Details'}</span>
              {openSection.p3 ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          </div>

          {/* P5 Compact Card */}
          <div
            className="card"
            style={{
              padding: '16px',
              borderLeft: result.five_minute_guardrail_triggered
                ? '4px solid var(--risk-medium)'
                : result.five_minute_telemetry_available
                ? '4px solid var(--accent-cyan)'
                : '4px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '10px',
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12.5px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  P5 5-Min Sub-Window Telemetry
                </span>
                <span
                  className={`badge ${
                    result.five_minute_guardrail_triggered
                      ? 'badge-amber'
                      : result.five_minute_telemetry_available
                      ? 'badge-cyan'
                      : 'badge-gray'
                  }`}
                  style={{ fontSize: '10px' }}
                >
                  {result.five_minute_guardrail_triggered
                    ? 'Burst Triggered'
                    : result.five_minute_telemetry_available
                    ? 'Active'
                    : 'No Telemetry'}
                </span>
              </div>
              <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                Velocity ratio:{' '}
                <strong>
                  {result.five_minute_velocity_ratio != null
                    ? `${result.five_minute_velocity_ratio.toFixed(2)}x`
                    : 'N/A'}
                </strong>{' '}
                ({result.five_minute_observation_count ?? 0} intervals)
              </p>
            </div>
            <button
              type="button"
              onClick={() => toggleSection('p5')}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-cyan)',
                fontSize: '11.5px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: 0,
                alignSelf: 'flex-start',
              }}
            >
              <span>{openSection.p5 ? 'Hide Details' : 'View Details'}</span>
              {openSection.p5 ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          </div>
        </div>
      </div>

      {/* 7. Technical Diagnostics (Collapsible Sections) */}
      <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>
            Technical Diagnostics & Engine Telemetry
          </h3>
          <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
            Expand individual sections to inspect raw machine learning probabilities, policy shifts, and pipeline graphs.
          </p>
        </div>

        {/* Section A: Raw ML Output & ML vs Operational Decision */}
        <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
          <button
            type="button"
            onClick={() => toggleSection('rawMl')}
            style={{
              width: '100%',
              padding: '12px 16px',
              backgroundColor: 'var(--bg-app)',
              border: 'none',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              cursor: 'pointer',
              color: 'var(--text-primary)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={15} color="var(--accent-cyan)" />
              <span style={{ fontSize: '13px', fontWeight: '600' }}>
                Raw ML Output & Decision Policy Comparison
              </span>
            </div>
            {openSection.rawMl ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
          {openSection.rawMl && (
            <div style={{ padding: '16px', borderTop: '1px solid var(--border-subtle)' }}>
              <RawVsPolicyPanel result={result} />
            </div>
          )}
        </div>

        {/* Section B: P1 Details */}
        {openSection.p1 && (
          <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '16px' }}>
            <GuardrailPanel
              guardrailTriggered={result.guardrail_triggered}
              fraudRateChange={result.fraud_rate_change}
              baselineRate={result.baseline_fraud_rate}
              currentRate={result.current_fraud_rate}
            />
          </div>
        )}

        {/* Section C: P3 Details */}
        {openSection.p3 && (
          <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '16px' }}>
            <PersistencePanel
              consecutiveWindows={result.consecutive_anomaly_windows}
              escalationTriggered={result.persistence_escalation_triggered}
            />
          </div>
        )}

        {/* Section D: P5 Telemetry Details */}
        {openSection.p5 && (
          <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '16px' }}>
            <TelemetryResultPanel
              telemetryAvailable={result.five_minute_telemetry_available}
              observationCount={result.five_minute_observation_count}
              currentTxCount={result.five_minute_current_tx_count}
              velocityRatio={result.five_minute_velocity_ratio}
              guardrailTriggered={result.five_minute_guardrail_triggered}
            />
          </div>
        )}

        {/* Section E: Pipeline Architecture */}
        <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
          <button
            type="button"
            onClick={() => toggleSection('pipeline')}
            style={{
              width: '100%',
              padding: '12px 16px',
              backgroundColor: 'var(--bg-app)',
              border: 'none',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              cursor: 'pointer',
              color: 'var(--text-primary)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={15} color="var(--accent-cyan)" />
              <span style={{ fontSize: '13px', fontWeight: '600' }}>
                Pipeline Architecture Flow
              </span>
            </div>
            {openSection.pipeline ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
          {openSection.pipeline && (
            <div style={{ padding: '16px', borderTop: '1px solid var(--border-subtle)' }}>
              <SpikeArchitectureFlow />
            </div>
          )}
        </div>
      </div>

      {/* 8. Bottom Action Bar */}
      <div
        style={{
          padding: '16px 20px',
          backgroundColor: 'var(--bg-card)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            onClick={() => navigate('/fraud-spike')}
            className="btn btn-secondary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', padding: '8px 14px' }}
          >
            <ArrowLeft size={13} />
            <span>Back to Fraud Spike</span>
          </button>
          <button
            type="button"
            onClick={() => navigate('/fraud-spike')}
            className="btn btn-secondary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', padding: '8px 14px' }}
          >
            <RotateCcw size={13} />
            <span>Run Another Assessment</span>
          </button>
        </div>

        <button
          type="button"
          onClick={() => navigate('/risk-operations')}
          className="btn btn-primary"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', padding: '8px 16px' }}
        >
          <span>View Case in Risk Operations</span>
          <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
};

export default FraudSpikeResultPage;
