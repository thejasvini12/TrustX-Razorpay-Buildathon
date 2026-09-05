import React, { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { AbuseRingResponse, AbuseRingRequest } from '../types/api';
import { AbuseRingGraph } from '../components/abuse-ring/AbuseRingGraph';
import { RingResultCard } from '../components/abuse-ring/RingResultCard';
import { RawVsEvidencePanel } from '../components/abuse-ring/RawVsEvidencePanel';
import { EvidenceAdjustmentPanel } from '../components/abuse-ring/EvidenceAdjustmentPanel';
import { RingFactorsPanel } from '../components/abuse-ring/RingFactorsPanel';
import { AttributionTable } from '../components/abuse-ring/AttributionTable';
import {
  ArrowLeft,
  Network,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  FileText,
  Users,
  AlertTriangle,
  Radio,
  Sparkles,
  ExternalLink,
} from 'lucide-react';

export const ABUSE_RING_SESSION_KEY = 'ai_risk_last_abuse_ring_result';

export interface StoredRingAssessment {
  result: AbuseRingResponse;
  clusterData: AbuseRingRequest;
  source: 'LIVE_RAZORPAY_WEBHOOK' | 'BENCHMARK_OFFLINE' | string;
  title?: string;
  clusterId?: string;
  timestamp: string;
}

function getInitialData(locationState: any): StoredRingAssessment | null {
  if (locationState && locationState.result) {
    const data: StoredRingAssessment = {
      result: locationState.result,
      clusterData: locationState.clusterData || { accounts: [], edges: [] },
      source: locationState.source || 'BENCHMARK_OFFLINE',
      title: locationState.title || locationState.result.cluster_id,
      clusterId: locationState.clusterId || locationState.result.cluster_id,
      timestamp: locationState.timestamp || new Date().toISOString(),
    };
    try {
      sessionStorage.setItem(ABUSE_RING_SESSION_KEY, JSON.stringify(data));
    } catch {
      // Non-blocking fallback
    }
    return data;
  }

  try {
    const raw = sessionStorage.getItem(ABUSE_RING_SESSION_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.result) {
        return parsed;
      }
    }
  } catch {
    // Non-blocking fallback
  }
  return null;
}

export const AbuseRingResultPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const [data] = useState<StoredRingAssessment | null>(() => getInitialData(location.state));

  // Graph interaction state
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  // Collapsible deep dive sections (collapsed by default to maintain high readability)
  const [openSections, setOpenSections] = useState<{
    ml: boolean;
    evidence: boolean;
    synthesis: boolean;
    attribution: boolean;
  }>({
    ml: false,
    evidence: false,
    synthesis: false,
    attribution: true, // attribution is useful to peek by default, but collapsible
  });

  const toggleSection = (key: keyof typeof openSections) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

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
            <h2 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)', marginBottom: '8px' }}>
              No Abuse Ring Assessment Found
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '440px', margin: '0 auto', lineHeight: '1.5' }}>
              No active or cached cluster assessment was found in this session. Select a benchmark scenario or investigate a live candidate cluster from the overview.
            </p>
          </div>
          <button
            onClick={() => navigate('/abuse-ring')}
            className="btn btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', marginTop: '8px' }}
          >
            <ArrowLeft size={16} />
            <span>Return to Abuse-Ring Sentinel</span>
          </button>
        </div>
      </div>
    );
  }

  const { result, clusterData, source, title, timestamp } = data;
  const isLive = source === 'LIVE_RAZORPAY_WEBHOOK';

  const accountsCount = clusterData.accounts?.length || result.cluster_size || 0;
  const edgesCount = clusterData.edges?.length || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1280px', margin: '0 auto' }}>
      {/* Top Navigation & Breadcrumb */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <button
          onClick={() => navigate('/abuse-ring')}
          className="btn btn-secondary"
          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', fontSize: '13px' }}
        >
          <ArrowLeft size={15} />
          <span>Back to Abuse Ring</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            className={`badge ${
              source === 'LIVE_SIMULATION'
                ? 'badge-amber'
                : isLive
                ? 'badge-cyan'
                : 'badge-purple'
            }`}
            style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', padding: '4px 8px' }}
          >
            {source === 'LIVE_SIMULATION' ? (
              <>
                <AlertTriangle size={11} color="var(--risk-medium)" />
                <span>LIVE SYNTHETIC SIMULATION</span>
              </>
            ) : isLive ? (
              <>
                <Radio size={11} className="pulse" />
                <span>LIVE REAL TELEMETRY</span>
              </>
            ) : (
              <>
                <Sparkles size={11} />
                <span>BENCHMARK / OFFLINE</span>
              </>
            )}
          </span>

          <span className="badge badge-subtle" style={{ fontSize: '11px', padding: '4px 8px' }}>
            Evaluated: {new Date(timestamp).toLocaleTimeString()}
          </span>

          <Link
            to="/risk-operations"
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}
          >
            <span>View Risk Operations</span>
            <ExternalLink size={12} />
          </Link>
        </div>
      </div>

      {/* Page Header Header */}
      <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: '24px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            {title || result.cluster_id}
          </h1>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Cluster ID: <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{result.cluster_id}</strong>
          </span>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          {isLive
            ? 'Real-time bipartite cluster evaluated from accepted Razorpay webhook transaction activity.'
            : 'Standard benchmark syndicate topology evaluated using frozen ML inference and deterministic evidence adjustments.'}
        </p>
      </div>

      {/* HERO SECTION: Operational Outcome Decision Card */}
      <div>
        <RingResultCard result={result} />
      </div>

      {/* RELATIONSHIP GRAPH: Clean Bipartite Visualizer */}
      <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Network size={18} color="var(--accent-cyan)" />
              <h2 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>
                Bipartite Relationship Graph
              </h2>
              <span className="badge badge-subtle" style={{ fontSize: '10px' }}>
                {accountsCount} Accounts • {edgesCount} Edges
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Accounts on the left linked to observed Device, IP, Payment, and Hashed Address tokens on the right.
            </p>
          </div>

          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Click an account or entity node to inspect connections
          </div>
        </div>

        <AbuseRingGraph
          accounts={clusterData.accounts || []}
          edges={clusterData.edges || []}
          selectedAccountId={selectedAccountId}
          selectedEntityId={selectedEntityId}
          onSelectAccount={(accId) => {
            setSelectedAccountId(accId);
            setSelectedEntityId(null);
          }}
          onSelectEntity={(entId) => {
            setSelectedEntityId(entId);
            setSelectedAccountId(null);
          }}
        />
      </div>

      {/* PROGRESSIVE DISCLOSURE: Deep-Dive Sections */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Section 1: Account Attribution & Role Classification */}
        <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
          <button
            onClick={() => toggleSection('attribution')}
            style={{
              width: '100%',
              padding: '16px 20px',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              textAlign: 'left',
              color: 'var(--text-primary)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Users size={18} color="var(--accent-purple)" />
              <div>
                <div style={{ fontSize: '14px', fontWeight: '700' }}>
                  ACCOUNT ATTRIBUTION & ROLE CLASSIFICATION
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Deterministic role attribution ({result.account_attribution?.length || 0} evaluated accounts)
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-subtle" style={{ fontSize: '11px' }}>
                {openSections.attribution ? 'Collapse ▴' : 'Expand Details ▾'}
              </span>
              {openSections.attribution ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </button>

          {openSections.attribution && (
            <div style={{ padding: '0 20px 20px 20px', borderTop: '1px solid var(--border-subtle)' }}>
              <AttributionTable
                attributionList={result.account_attribution || []}
                selectedAccountId={selectedAccountId}
                onSelectAccount={setSelectedAccountId}
              />
            </div>
          )}
        </div>

        {/* Section 2: ML Classification & Probability */}
        <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
          <button
            onClick={() => toggleSection('ml')}
            style={{
              width: '100%',
              padding: '16px 20px',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              textAlign: 'left',
              color: 'var(--text-primary)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Cpu size={18} color="var(--accent-cyan)" />
              <div>
                <div style={{ fontSize: '14px', fontWeight: '700' }}>
                  FROZEN ML CLASSIFICATION (RANDOM FOREST)
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Calibrated probability: {(result.raw_ml_probability * 100).toFixed(1)}% • Threshold: {(result.model_threshold * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-subtle" style={{ fontSize: '11px' }}>
                {openSections.ml ? 'Collapse ▴' : 'Expand Details ▾'}
              </span>
              {openSections.ml ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </button>

          {openSections.ml && (
            <div style={{ padding: '20px', borderTop: '1px solid var(--border-subtle)' }}>
              <RawVsEvidencePanel result={result} />
            </div>
          )}
        </div>

        {/* Section 3: Evidence Delta Adjustments */}
        <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
          <button
            onClick={() => toggleSection('evidence')}
            style={{
              width: '100%',
              padding: '16px 20px',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              textAlign: 'left',
              color: 'var(--text-primary)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Layers size={18} color="var(--accent-amber)" />
              <div>
                <div style={{ fontSize: '14px', fontWeight: '700' }}>
                  DETERMINISTIC EVIDENCE DELTA ADJUSTMENTS
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Net delta: {result.evidence_adjustments?.net_delta >= 0 ? '+' : ''}{(result.evidence_adjustments?.net_delta ?? 0).toFixed(2)}
                  {' '}(+{result.evidence_adjustments?.total_positive_delta?.toFixed(2) || '0.00'} / {result.evidence_adjustments?.total_negative_delta?.toFixed(2) || '0.00'})
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-subtle" style={{ fontSize: '11px' }}>
                {openSections.evidence ? 'Collapse ▴' : 'Expand Details ▾'}
              </span>
              {openSections.evidence ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </button>

          {openSections.evidence && (
            <div style={{ padding: '20px', borderTop: '1px solid var(--border-subtle)' }}>
              <EvidenceAdjustmentPanel evidenceAdjustments={result.evidence_adjustments} />
            </div>
          )}
        </div>

        {/* Section 4: Evidence Synthesis & Graph Reasoning */}
        <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
          <button
            onClick={() => toggleSection('synthesis')}
            style={{
              width: '100%',
              padding: '16px 20px',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              textAlign: 'left',
              color: 'var(--text-primary)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <FileText size={18} color="var(--accent-green)" />
              <div>
                <div style={{ fontSize: '14px', fontWeight: '700' }}>
                  EVIDENCE SYNTHESIS & REASONING SUMMARY
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Quality: {result.evidence_quality} • Confidence: {result.confidence}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-subtle" style={{ fontSize: '11px' }}>
                {openSections.synthesis ? 'Collapse ▴' : 'Expand Details ▾'}
              </span>
              {openSections.synthesis ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </button>

          {openSections.synthesis && (
            <div style={{ padding: '20px', borderTop: '1px solid var(--border-subtle)' }}>
              <RingFactorsPanel
                evidenceQuality={result.evidence_quality}
                confidence={result.confidence}
                evidenceSummary={result.evidence_summary}
                decisionReasoning={result.decision_reasoning}
                ringFactors={result.ring_factors}
                mitigatingFactors={result.mitigating_factors}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AbuseRingResultPage;
