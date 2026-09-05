import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AbuseRingRequest,
  AccountNodeInput,
  EntityEdgeInput,
  LiveAbuseGraphResponse,
  LiveClusterCandidateItem,
} from '../types/api';
import { riskApi, ApiError } from '../services/api';
import { useRiskFeed } from '../context/RiskFeedContext';
import { AbuseRingScenarioPresets, RING_PRESETS, RingPreset } from '../components/abuse-ring/AbuseRingScenarioPresets';
import { LiveAbuseGraphPanel } from '../components/abuse-ring/LiveAbuseGraphPanel';
import { AccountNodeEditor } from '../components/abuse-ring/AccountNodeEditor';
import { EntityEdgeEditor } from '../components/abuse-ring/EntityEdgeEditor';
import { AbuseRingGraph } from '../components/abuse-ring/AbuseRingGraph';
import { ABUSE_RING_SESSION_KEY, StoredRingAssessment } from './AbuseRingResultPage';
import {
  Network,
  AlertOctagon,
  RotateCcw,
  Loader2,
  Play,
  HelpCircle,
  Wrench,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Cpu,
  Layers,
  CheckCircle2,
} from 'lucide-react';

const DEFAULT_SANDBOX_CLUSTER: AbuseRingRequest = RING_PRESETS[1].data; // Default to Identity Ring

export const AbuseRingPage: React.FC = () => {
  const navigate = useNavigate();
  const { addEvent } = useRiskFeed();

  // Evaluation loading & error state
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [evaluatingTarget, setEvaluatingTarget] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Live Abuse Graph state (15s auto-polling)
  const [liveGraphData, setLiveGraphData] = useState<LiveAbuseGraphResponse | null>(null);
  const [liveGraphLoading, setLiveGraphLoading] = useState<boolean>(false);
  const [selectedLiveClusterId, setSelectedLiveClusterId] = useState<string | null>(null);

  // Collapsible helper & advanced sandbox sections (collapsed by default for calm readability)
  const [showHowItWorks, setShowHowItWorks] = useState<boolean>(false);
  const [showSandbox, setShowSandbox] = useState<boolean>(false);

  // Sandbox graph state
  const [sandboxData, setSandboxData] = useState<AbuseRingRequest>(DEFAULT_SANDBOX_CLUSTER);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  // Poll live abuse graph
  const fetchLiveGraph = async (silent: boolean = false) => {
    try {
      if (!silent) setLiveGraphLoading(true);
      const data = await riskApi.getLiveAbuseGraph();
      setLiveGraphData(data);
    } catch (err) {
      console.warn('Unable to poll live abuse graph:', err);
    } finally {
      if (!silent) setLiveGraphLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveGraph();
    const interval = setInterval(() => {
      fetchLiveGraph(true);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Action: Investigate Live Cluster -> POST /risk/abuse-ring/live-cluster -> /abuse-ring/result
  const handleAnalyzeLiveCluster = async (cluster: LiveClusterCandidateItem) => {
    try {
      setEvaluating(true);
      setEvaluatingTarget(`Live Cluster ${cluster.cluster_id}`);
      setError(null);
      setSelectedLiveClusterId(cluster.cluster_id);

      const res = await riskApi.analyzeLiveCluster({ cluster_id: cluster.cluster_id });

      // Synthesize bipartite graph representation for the interactive visualizer
      const accNodes: AccountNodeInput[] = cluster.account_ids.map((accId) => ({
        account_id: accId,
        average_order_value: 100.0,
        return_rate: 0.0,
        suspicious_activity_score: 0.02,
      }));

      const entityEdges: EntityEdgeInput[] = [];
      cluster.shared_entities.forEach((se) => {
        cluster.account_ids.forEach((accId) => {
          entityEdges.push({
            account_id: accId,
            entity_type: se.entity_type,
            entity_id: se.entity_id,
            event_type: 'WEBHOOK_ATTACH',
          });
        });
      });

      const clusterPayload: AbuseRingRequest = {
        accounts: accNodes,
        edges: entityEdges,
        cluster_metadata: {
          cluster_id: cluster.cluster_id,
          source: 'LIVE_RAZORPAY_GRAPH',
          member_count: cluster.member_count,
        },
      };

      // Emit event to Risk Operations session feed
      addEvent({
        engine: 'ABUSE_RING',
        source: 'LIVE_ASSESSMENT',
        title: `Live Abuse Ring Cluster (${res.verdict})`,
        entityId: cluster.cluster_id,
        entityType: 'CLUSTER',
        severity: res.risk_level,
        score: Math.round(res.final_ring_score * 100),
        decision: res.recommended_action,
        rawMl: {
          probability: res.raw_ml_probability,
          score: Math.round(res.raw_ml_probability * 100),
        },
        evidence: res.ring_factors,
        attribution: res.account_attribution?.map((a) => ({
          accountId: a.account_id,
          role: a.attribution_role,
          reasoning: a.attribution_reasoning,
        })),
      });

      const stored: StoredRingAssessment = {
        result: res,
        clusterData: clusterPayload,
        source: 'LIVE_RAZORPAY_WEBHOOK',
        title: `Live Cluster: ${cluster.cluster_id}`,
        clusterId: cluster.cluster_id,
        timestamp: new Date().toISOString(),
      };

      try {
        sessionStorage.setItem(ABUSE_RING_SESSION_KEY, JSON.stringify(stored));
      } catch {
        // Fallback
      }

      navigate('/abuse-ring/result', { state: stored });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(`API Error (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to analyze live abuse cluster.');
      }
    } finally {
      setEvaluating(false);
      setEvaluatingTarget(null);
    }
  };

  // Action: Run Benchmark Scenario -> POST /risk/abuse-ring -> /abuse-ring/result
  const handleRunBenchmark = async (preset: RingPreset) => {
    try {
      setEvaluating(true);
      setEvaluatingTarget(`Benchmark Scenario: ${preset.name}`);
      setError(null);

      const res = await riskApi.detectAbuseRing(preset.data);

      // Emit simulation event to Risk Operations session feed
      addEvent({
        engine: 'ABUSE_RING',
        source: 'SIMULATION',
        title: `Benchmark Ring (${res.verdict}) - ${preset.name}`,
        entityId: preset.data.cluster_metadata?.cluster_id || preset.id,
        entityType: 'CLUSTER',
        severity: res.risk_level,
        score: Math.round(res.final_ring_score * 100),
        decision: res.recommended_action,
        rawMl: {
          probability: res.raw_ml_probability,
          score: Math.round(res.raw_ml_probability * 100),
        },
        evidence: res.ring_factors,
        attribution: res.account_attribution?.map((a) => ({
          accountId: a.account_id,
          role: a.attribution_role,
          reasoning: a.attribution_reasoning,
        })),
      });

      const stored: StoredRingAssessment = {
        result: res,
        clusterData: preset.data,
        source: 'BENCHMARK_OFFLINE',
        title: preset.name,
        clusterId: preset.data.cluster_metadata?.cluster_id || preset.id,
        timestamp: new Date().toISOString(),
      };

      try {
        sessionStorage.setItem(ABUSE_RING_SESSION_KEY, JSON.stringify(stored));
      } catch {
        // Fallback
      }

      navigate('/abuse-ring/result', { state: stored });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(`API Error (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to run benchmark scenario.');
      }
    } finally {
      setEvaluating(false);
      setEvaluatingTarget(null);
    }
  };

  // Action: Analyze Custom Sandbox Graph -> POST /risk/abuse-ring -> /abuse-ring/result
  const handleAnalyzeSandbox = async () => {
    if (sandboxData.accounts.length === 0) {
      setError('Please add at least one account node in the sandbox before running analysis.');
      return;
    }

    try {
      setEvaluating(true);
      setEvaluatingTarget('Custom Sandbox Graph');
      setError(null);

      const res = await riskApi.detectAbuseRing(sandboxData);

      addEvent({
        engine: 'ABUSE_RING',
        source: 'MANUAL_INVESTIGATION',
        title: `Sandbox Ring (${res.verdict})`,
        entityId: sandboxData.cluster_metadata?.cluster_id || 'CUSTOM_SANDBOX',
        entityType: 'CLUSTER',
        severity: res.risk_level,
        score: Math.round(res.final_ring_score * 100),
        decision: res.recommended_action,
        rawMl: {
          probability: res.raw_ml_probability,
          score: Math.round(res.raw_ml_probability * 100),
        },
        evidence: res.ring_factors,
        attribution: res.account_attribution?.map((a) => ({
          accountId: a.account_id,
          role: a.attribution_role,
          reasoning: a.attribution_reasoning,
        })),
      });

      const stored: StoredRingAssessment = {
        result: res,
        clusterData: sandboxData,
        source: 'BENCHMARK_OFFLINE',
        title: sandboxData.cluster_metadata?.cluster_id || 'Custom Graph Sandbox',
        clusterId: sandboxData.cluster_metadata?.cluster_id || 'CUSTOM_SANDBOX',
        timestamp: new Date().toISOString(),
      };

      try {
        sessionStorage.setItem(ABUSE_RING_SESSION_KEY, JSON.stringify(stored));
      } catch {
        // Fallback
      }

      navigate('/abuse-ring/result', { state: stored });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(`API Error (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to analyze custom sandbox graph.');
      }
    } finally {
      setEvaluating(false);
      setEvaluatingTarget(null);
    }
  };

  // Sandbox node & edge modifications
  const handleAccountsChange = (accounts: AccountNodeInput[]) => {
    const accountIds = new Set(accounts.map((a) => a.account_id));
    const validEdges = sandboxData.edges.filter((e) => accountIds.has(e.account_id));
    setSandboxData({
      ...sandboxData,
      accounts,
      edges: validEdges,
    });
  };

  const handleEdgesChange = (edges: EntityEdgeInput[]) => {
    setSandboxData({
      ...sandboxData,
      edges,
    });
  };

  const handleResetSandbox = () => {
    setSandboxData(DEFAULT_SANDBOX_CLUSTER);
    setSelectedAccountId(null);
    setSelectedEntityId(null);
    setError(null);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Network size={22} color="var(--accent-cyan)" />
            <h1 style={{ fontSize: '22px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Abuse-Ring Sentinel
            </h1>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className="badge badge-green" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--risk-low)' }} />
              <span>SENTINEL ONLINE</span>
            </span>
            <span className="badge badge-cyan" style={{ fontSize: '10px' }}>POST /risk/abuse-ring</span>
            <span className="badge badge-purple" style={{ fontSize: '10px' }}>Graph Detection</span>
            <span className="badge badge-amber" style={{ fontSize: '10px' }}>Evidence Adjustment</span>
          </div>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Graph-based collusive syndicate detection with deterministic evidence adjustments and granular account attribution.
        </p>
      </div>

      {/* Evaluating Overlay / Banner */}
      {evaluating && (
        <div
          style={{
            padding: '16px 20px',
            backgroundColor: 'rgba(6, 182, 212, 0.12)',
            border: '1px solid var(--accent-cyan)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            color: 'var(--text-primary)',
          }}
        >
          <Loader2 size={18} className="spin" color="var(--accent-cyan)" />
          <div>
            <div style={{ fontWeight: '700', fontSize: '13px', color: 'var(--accent-cyan)' }}>
              Evaluating Graph Topology with Sentinel Engine...
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              Target: {evaluatingTarget || 'Graph Component'}. Calculating raw ML features, evidence adjustments, and bystander attributions.
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

      {/* Section A & B: Live Risk Overview & Candidate Clusters */}
      <LiveAbuseGraphPanel
        data={liveGraphData}
        loading={liveGraphLoading}
        onRefresh={() => fetchLiveGraph(false)}
        onAnalyzeCluster={handleAnalyzeLiveCluster}
        selectedClusterId={selectedLiveClusterId}
      />

      {/* Section C: Benchmark Scenarios (Offline Verification) */}
      <AbuseRingScenarioPresets
        onSelect={(data) => {
          const matched = RING_PRESETS.find((p) => p.data.cluster_metadata?.cluster_id === data.cluster_metadata?.cluster_id);
          if (matched) {
            handleRunBenchmark(matched);
          }
        }}
        onRunBenchmark={handleRunBenchmark}
      />

      {/* Section D: Collapsed Helpers & Advanced Tools */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '4px' }}>
        {/* Helper 1: How Abuse-Ring Sentinel Works */}
        <div
          className="card"
          style={{
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            overflow: 'hidden',
          }}
        >
          <button
            onClick={() => setShowHowItWorks((prev) => !prev)}
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
              <HelpCircle size={16} color="var(--accent-cyan)" />
              <span style={{ fontSize: '13px', fontWeight: '700' }}>
                How Abuse-Ring Sentinel Works
              </span>
              <span className="badge badge-purple" style={{ fontSize: '10px' }}>
                Methodology & Guarantees
              </span>
            </div>
            {showHowItWorks ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
          </button>

          {showHowItWorks && (
            <div style={{ padding: '0 18px 18px 18px', borderTop: '1px solid var(--border-color)', paddingTop: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
                <div style={{ padding: '12px', backgroundColor: 'rgba(15, 23, 42, 0.4)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '12px', color: 'var(--accent-cyan)' }}>
                    <Layers size={14} />
                    <span>1. Bipartite Topology</span>
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: '1.5' }}>
                    Accounts connect to shared Device, IP, Card, and Address entities. Connected components represent potential collusive syndicates.
                  </p>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'rgba(15, 23, 42, 0.4)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '12px', color: 'var(--accent-purple)' }}>
                    <Cpu size={14} />
                    <span>2. Frozen ML Model</span>
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: '1.5' }}>
                    Extracts 8 invariant topological features (density, degree distribution, component sizes) to output an initial base ring probability.
                  </p>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'rgba(15, 23, 42, 0.4)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '12px', color: 'var(--risk-medium)' }}>
                    <ShieldCheck size={14} />
                    <span>3. Deterministic Deltas</span>
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: '1.5' }}>
                    Applies strictly audited mathematical shifts (+0.35 multi-accounting, +0.25 rapid velocity, -0.20 diverse merchant behavior) to ensure predictable risk scores.
                  </p>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'rgba(15, 23, 42, 0.4)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '12px', color: 'var(--risk-low)' }}>
                    <CheckCircle2 size={14} />
                    <span>4. Bystander Safety</span>
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: '1.5' }}>
                    Guarantees benign family or public Wi-Fi members are tagged as <code>BENIGN_BYSTANDER</code> with scores clamped to 0.15, preventing unfair collateral account bans.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Helper 2: Advanced Custom Graph Sandbox & Node/Edge Editor */}
        <div
          className="card"
          style={{
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            overflow: 'hidden',
          }}
        >
          <button
            onClick={() => setShowSandbox((prev) => !prev)}
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
              <Wrench size={16} color="var(--accent-purple)" />
              <span style={{ fontSize: '13px', fontWeight: '700' }}>
                Advanced: Custom Graph Sandbox & Node/Edge Editor
              </span>
              <span className="badge badge-cyan" style={{ fontSize: '10px' }}>
                {sandboxData.accounts.length} Nodes / {sandboxData.edges.length} Edges
              </span>
            </div>
            {showSandbox ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
          </button>

          {showSandbox && (
            <div style={{ padding: '0 18px 18px 18px', borderTop: '1px solid var(--border-color)', paddingTop: '18px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Sandbox Header & Actions */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                <div>
                  <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>
                    Interactive Topology Sandbox
                  </h3>
                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    Add or modify accounts and edges to test hypothetical ring topologies against the Sentinel engine.
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    onClick={handleResetSandbox}
                    className="btn btn-secondary"
                    style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}
                  >
                    <RotateCcw size={13} />
                    <span>Reset Sandbox</span>
                  </button>

                  <button
                    onClick={handleAnalyzeSandbox}
                    disabled={evaluating || sandboxData.accounts.length === 0}
                    className="btn btn-primary"
                    style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 16px', fontSize: '12px' }}
                  >
                    {evaluating ? (
                      <>
                        <Loader2 size={13} className="spin" />
                        <span>Analyzing...</span>
                      </>
                    ) : (
                      <>
                        <Play size={13} />
                        <span>Analyze Sandbox Graph →</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Visualizer */}
              <AbuseRingGraph
                accounts={sandboxData.accounts}
                edges={sandboxData.edges}
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

              {/* Node and Edge Editors */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '16px' }}>
                <AccountNodeEditor
                  accounts={sandboxData.accounts}
                  onChange={handleAccountsChange}
                  selectedAccountId={selectedAccountId}
                  onSelectAccount={setSelectedAccountId}
                />

                <EntityEdgeEditor
                  edges={sandboxData.edges}
                  accounts={sandboxData.accounts}
                  onChange={handleEdgesChange}
                  selectedEntityId={selectedEntityId}
                  onSelectEntity={setSelectedEntityId}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AbuseRingPage;
