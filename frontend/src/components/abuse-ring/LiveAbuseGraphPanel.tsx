import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LiveAbuseGraphResponse,
  LiveClusterCandidateItem,
  LiveAbuseSimulationResponse,
} from '../../types/api';
import { riskApi } from '../../services/api';
import {
  Activity,
  RefreshCw,
  Network,
  Users,
  Layers,
  ArrowRight,
  Clock,
  Radio,
  Play,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';

interface LiveAbuseGraphPanelProps {
  data: LiveAbuseGraphResponse | null;
  loading: boolean;
  onRefresh: () => void;
  onAnalyzeCluster: (cluster: LiveClusterCandidateItem) => void;
  selectedClusterId?: string | null;
}

export const LiveAbuseGraphPanel: React.FC<LiveAbuseGraphPanelProps> = ({
  data,
  loading,
  onRefresh,
  onAnalyzeCluster,
  selectedClusterId,
}) => {
  const navigate = useNavigate();
  const isIdle = !data || data.total_webhook_events === 0;

  const [selectedScenario, setSelectedScenario] = useState<string>('CLEAN_SHARED_INFRASTRUCTURE');
  const [simulating, setSimulating] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<LiveAbuseSimulationResponse | null>(null);
  const [simError, setSimError] = useState<string | null>(null);

  const handleRunSimulation = async () => {
    setSimulating(true);
    setSimError(null);
    try {
      const res = await riskApi.simulateLiveAbuseRing(selectedScenario);
      setSimulationResult(res);
      onRefresh();
    } catch (err: any) {
      setSimError(err?.message || 'Simulation failed to execute.');
    } finally {
      setSimulating(false);
    }
  };

  const handleOpenResult = () => {
    if (!simulationResult) return;
    navigate('/abuse-ring/result', {
      state: {
        result: simulationResult.evaluation,
        clusterData: simulationResult.cluster_data,
        source: 'LIVE_SIMULATION',
        title: `Live Attack Simulation (${simulationResult.scenario})`,
        clusterId: simulationResult.cluster_id,
        timestamp: new Date().toISOString(),
      },
    });
  };

  return (
    <div
      className="card"
      style={{
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        border: '1px solid var(--accent-cyan-border, rgba(6, 182, 212, 0.3))',
        background: 'linear-gradient(180deg, rgba(6, 182, 212, 0.04) 0%, rgba(15, 23, 42, 0.6) 100%)',
      }}
    >
      {/* Panel Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={18} color="var(--accent-cyan)" />
            <h2 style={{ fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              LIVE ABUSE GRAPH (REAL-TIME RAZORPAY WEBHOOKS)
            </h2>
            <span
              className={`badge ${isIdle ? 'badge-amber' : 'badge-green'}`}
              style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px' }}
            >
              <Radio size={10} className={!isIdle ? 'pulse' : ''} />
              <span>{isIdle ? 'IDLE (NO WEBHOOKS YET)' : 'ACTIVE STREAM'}</span>
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Event-driven bipartite relationship graph constructed strictly from verified Razorpay Test Mode webhooks.
            Distinct from frozen offline benchmark topologies.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Auto-polling: 15s
          </span>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}
            title="Refresh Live Abuse Graph"
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            <span>Refresh Live Graph</span>
          </button>
        </div>
      </div>

      {/* Metrics Strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
        <div
          style={{
            padding: '12px 14px',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
            <Users size={13} />
            <span>Observed Accounts</span>
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '4px' }}>
            {data?.total_accounts ?? 0}
          </div>
        </div>

        <div
          style={{
            padding: '12px 14px',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
            <Layers size={13} />
            <span>Entities Recorded</span>
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--accent-cyan)', marginTop: '4px' }}>
            {data?.total_entities ?? 0}
          </div>
        </div>

        <div
          style={{
            padding: '12px 14px',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
            <Network size={13} />
            <span>Live Edges</span>
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '4px' }}>
            {data?.total_edges ?? 0}
          </div>
        </div>

        <div
          style={{
            padding: '12px 14px',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
            <Activity size={13} />
            <span>Candidate Clusters</span>
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--accent-purple)', marginTop: '4px' }}>
            {data?.candidate_clusters_count ?? 0}
          </div>
        </div>

        <div
          style={{
            padding: '12px 14px',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '11px' }}>
            <Clock size={13} />
            <span>Total Webhooks</span>
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--text-primary)', marginTop: '4px' }}>
            {data?.total_webhook_events ?? 0}
          </div>
        </div>
      </div>

      {/* Live Attack Simulation & Validation Control */}
      <div
        style={{
          padding: '16px 18px',
          backgroundColor: 'rgba(15, 23, 42, 0.7)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Play size={15} color="var(--risk-medium)" />
            <span style={{ fontSize: '13px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '0.02em' }}>
              LIVE ATTACK SIMULATION & GENUINE HIGH-RISK VALIDATION
            </span>
            <span className="badge badge-amber" style={{ fontSize: '9px', padding: '1px 6px' }}>
              DEMO / SYNTHETIC DATA
            </span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Passes synthetic checkouts & webhooks through live graph to evaluate with frozen ML
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <select
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
            disabled={simulating}
            className="input"
            style={{
              flex: '1',
              minWidth: '280px',
              fontSize: '12px',
              padding: '8px 12px',
              backgroundColor: 'rgba(30, 41, 59, 0.8)',
              borderColor: 'rgba(245, 158, 11, 0.3)',
              color: 'var(--text-primary)',
            }}
          >
            <option value="CLEAN_SHARED_INFRASTRUCTURE">
              Clean Shared Infrastructure (Legitimate Office/Lab) &rarr; Expect NO_RING
            </option>
            <option value="COORDINATED_SUSPICIOUS_CLUSTER">
              Coordinated Suspicious Cluster (Moderate Coordination) &rarr; Expect REVIEW
            </option>
            <option value="HIGH_CONFIDENCE_ABUSE_RING">
              High-Confidence Abuse Ring (Syndicate Attack Pattern) &rarr; Expect BLOCK_ENTIRE_RING
            </option>
            <option value="BYSTANDER_MIXED_CLUSTER">
              Bystander Mixed Cluster (Syndicate + Protected Resident) &rarr; Expect Bystander Protection
            </option>
          </select>

          <button
            onClick={handleRunSimulation}
            disabled={simulating}
            className="btn btn-primary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              fontSize: '12px',
              backgroundColor: 'var(--risk-medium)',
              borderColor: 'var(--risk-medium)',
              color: '#000',
              fontWeight: '700',
            }}
          >
            <Play size={13} className={simulating ? 'spin' : ''} />
            <span>{simulating ? 'Simulating Attack...' : 'Run Attack Simulation'}</span>
          </button>
        </div>

        {simError && (
          <div style={{ padding: '8px 12px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--risk-critical)', borderRadius: 'var(--radius-sm)', color: 'var(--risk-critical)', fontSize: '11px' }}>
            {simError}
          </div>
        )}

        {/* Progressive Disclosure: Simulation Result Banner */}
        {simulationResult && (
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              fontSize: '12px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={15} color="var(--risk-low)" />
                <strong style={{ color: 'var(--text-primary)' }}>Simulation Executed:</strong>
                <span className="badge badge-subtle" style={{ fontFamily: 'var(--font-mono)' }}>
                  {simulationResult.scenario}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  className={`badge ${
                    simulationResult.evaluation.verdict === 'HIGH_CONFIDENCE_RING'
                      ? 'badge-red'
                      : simulationResult.evaluation.verdict === 'LIKELY_RING'
                      ? 'badge-amber'
                      : simulationResult.evaluation.verdict === 'POSSIBLE_RING'
                      ? 'badge-amber'
                      : 'badge-green'
                  }`}
                  style={{ fontSize: '11px', fontWeight: '700' }}
                >
                  Verdict: {simulationResult.evaluation.verdict} ({Math.round(simulationResult.evaluation.final_ring_score * 100)}/100)
                </span>

                <button
                  onClick={handleOpenResult}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '4px 10px', fontSize: '11px' }}
                >
                  <span>Open in Result Inspector</span>
                  <ExternalLink size={11} />
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', color: 'var(--text-secondary)', fontSize: '11px' }}>
              <span>
                Recommended Action: <strong style={{ color: 'var(--text-primary)' }}>{simulationResult.evaluation.recommended_action}</strong>
              </span>
              <span>
                Observed Members: <strong style={{ color: 'var(--text-primary)' }}>{simulationResult.account_count}</strong>
              </span>
              <span>
                Shared Infrastructure: <strong style={{ color: 'var(--accent-cyan)' }}>{simulationResult.shared_entities.length} tokens</strong>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Candidate Clusters & Recent Feed Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '16px' }}>
        {/* Candidate Clusters Section */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'rgba(15, 23, 42, 0.4)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Candidate Connected Components
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {data?.candidate_clusters?.length || 0} component(s)
            </span>
          </div>

          {(!data?.candidate_clusters || data.candidate_clusters.length === 0) ? (
            <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '12px' }}>
              No clusters formed yet. When payments arrive with notes containing shared devices, IPs, or addresses, candidate clusters will be discovered automatically.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '280px', overflowY: 'auto' }}>
              {data.candidate_clusters.map((cluster) => {
                const isSelected = selectedClusterId === cluster.cluster_id;
                return (
                  <div
                    key={cluster.cluster_id}
                    style={{
                      padding: '12px',
                      backgroundColor: isSelected ? 'rgba(6, 182, 212, 0.12)' : 'rgba(30, 41, 59, 0.5)',
                      border: isSelected
                        ? '1px solid var(--accent-cyan)'
                        : cluster.is_multi_account
                        ? '1px solid var(--accent-purple-border, rgba(168, 85, 247, 0.3))'
                        : '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontWeight: '700', fontSize: '12px', color: 'var(--text-primary)' }}>
                          {cluster.cluster_id}
                        </span>
                        <span
                          className={`badge ${cluster.is_multi_account ? 'badge-purple' : 'badge-cyan'}`}
                          style={{ fontSize: '10px', padding: '2px 6px' }}
                        >
                          {cluster.is_multi_account ? `${cluster.member_count} Accounts` : '1 Account'}
                        </span>
                      </div>

                      <button
                        onClick={() => onAnalyzeCluster(cluster)}
                        className="btn btn-primary"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '4px 10px',
                          fontSize: '11px',
                        }}
                      >
                        <span>Investigate Cluster</span>
                        <ArrowRight size={11} />
                      </button>
                    </div>

                    {/* Member Accounts List */}
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Members: </span>
                      {cluster.account_ids.map((acc, idx) => (
                        <span key={acc} style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                          {acc}{idx < cluster.account_ids.length - 1 ? ', ' : ''}
                        </span>
                      ))}
                    </div>

                    {/* Shared Infrastructure Entities */}
                    {cluster.shared_entities && cluster.shared_entities.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '2px' }}>
                        {cluster.shared_entities.map((se) => (
                          <span
                            key={`${se.entity_type}_${se.entity_id}`}
                            className="badge badge-amber"
                            style={{ fontSize: '10px', padding: '2px 6px' }}
                            title={
                              se.entity_type === 'DEVICE'
                                ? `Application-observed device identifier (shared by ${se.account_count} accounts)`
                                : se.entity_type === 'IP'
                                ? `Application-observed network identifier (shared by ${se.account_count} accounts)`
                                : se.entity_type === 'ADDRESS'
                                ? `Application-observed address identifier (shared by ${se.account_count} accounts)`
                                : `Shared ${se.entity_type} (shared by ${se.account_count} accounts)`
                            }
                          >
                            {se.entity_type}: {se.entity_id}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Webhook Events Stream */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'rgba(15, 23, 42, 0.4)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Recent Webhook Linkages
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Last 10 events
            </span>
          </div>

          {(!data?.recent_events || data.recent_events.length === 0) ? (
            <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '12px' }}>
              No webhook events ingested yet. Send a signed Razorpay Test Mode webhook to see live linkages appear.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
              {data.recent_events.slice(0, 10).map((evt) => (
                <div
                  key={evt.event_id}
                  style={{
                    padding: '8px 10px',
                    backgroundColor: 'rgba(30, 41, 59, 0.4)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    fontSize: '11px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="badge badge-green" style={{ fontSize: '9px', padding: '1px 5px' }}>
                        {evt.event_type}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '600', color: 'var(--text-primary)' }}>
                        {evt.account_id}
                      </span>
                    </div>
                    <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>
                      {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : ''}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', color: 'var(--text-secondary)' }}>
                    {evt.payment_id && (
                      <span>Payment: <strong style={{ color: 'var(--accent-cyan)' }}>{evt.payment_id}</strong></span>
                    )}
                    {evt.entities_observed?.map((ent) => (
                      <span key={`${ent.entity_type}_${ent.entity_id}`} style={{ color: 'var(--text-muted)' }}>
                        [{ent.entity_type}: {ent.entity_id}]
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
