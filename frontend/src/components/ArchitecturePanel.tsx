import React from 'react';
import { Layers, ArrowDown, Server, Cpu, ShieldAlert, CheckCircle2 } from 'lucide-react';

export const ArchitecturePanel: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} color="var(--accent-cyan)" />
            <h3 className="card-title">System Architecture & Multi-Engine Defense Pipeline</h3>
          </div>
          <p className="card-description">
            End-to-end telemetry flow from front-of-house intake to deterministic defense policy execution.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', position: 'relative' }}>
        {/* Layer 1: Client Intake */}
        <div
          style={{
            padding: '14px 18px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ padding: '6px', backgroundColor: 'var(--accent-cyan-bg)', color: 'var(--accent-cyan)', borderRadius: 'var(--radius-sm)' }}>
              <Layers size={16} />
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                1. Operations Client Layer (React 18 + Vite SPA)
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                Interactive Analyst Workspace • Telemetry Visualizer • Preset Attack Injector
              </div>
            </div>
          </div>
          <span className="badge badge-cyan" style={{ fontSize: '10px' }}>Front-End</span>
        </div>

        {/* Connector */}
        <div style={{ display: 'flex', justifyContent: 'center', margin: '-4px 0' }}>
          <ArrowDown size={14} color="var(--text-muted)" />
        </div>

        {/* Layer 2: API Gateway */}
        <div
          style={{
            padding: '14px 18px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ padding: '6px', backgroundColor: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent-indigo)', borderRadius: 'var(--radius-sm)' }}>
              <Server size={16} />
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                2. Enterprise API Service (FastAPI REST Engine)
              </div>
              <div className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                POST /risk/score • POST /risk/fraud-spike • POST /risk/abuse-ring • GET /health
              </div>
            </div>
          </div>
          <span className="badge badge-low" style={{ fontSize: '10px' }}>CORS Enabled</span>
        </div>

        {/* Connector */}
        <div style={{ display: 'flex', justifyContent: 'center', margin: '-4px 0' }}>
          <ArrowDown size={14} color="var(--text-muted)" />
        </div>

        {/* Layer 3: Risk Engines Grid */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-elevated)',
            border: '1px solid var(--border-muted)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={14} color="var(--accent-cyan)" />
            <span>3. Coordinated Risk Inference Engines (4 Frozen ML Sub-Systems)</span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '10px',
            }}
          >
            <div style={{ padding: '10px 12px', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--accent-cyan)' }}>Account Risk</div>
              <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '2px' }}>RandomForest Pipeline</div>
            </div>

            <div style={{ padding: '10px 12px', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--risk-low)' }}>Return Abuse</div>
              <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '2px' }}>Serial Wardrobing Scorer</div>
            </div>

            <div style={{ padding: '10px 12px', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--risk-medium)' }}>Fraud Spike Radar</div>
              <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '2px' }}>P1/P3/P5 5-Min Telemetry</div>
            </div>

            <div style={{ padding: '10px 12px', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--risk-critical)' }}>Abuse Ring Sentinel</div>
              <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '2px' }}>15-Feature Bipartite Graph</div>
            </div>
          </div>
        </div>

        {/* Connector */}
        <div style={{ display: 'flex', justifyContent: 'center', margin: '-4px 0' }}>
          <ArrowDown size={14} color="var(--text-muted)" />
        </div>

        {/* Layer 4: Decision & Explainability */}
        <div
          style={{
            padding: '14px 18px',
            backgroundColor: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ padding: '6px', backgroundColor: 'var(--risk-low-bg)', color: 'var(--risk-low)', borderRadius: 'var(--radius-sm)' }}>
              <ShieldAlert size={16} />
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                4. Deterministic Defense Policies & Dual-Layer Explainability
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                ALLOW • MANUAL_REVIEW • CHALLENGE • BLOCK • Feature Contributions • Plain-Language Reasoning
              </div>
            </div>
          </div>
          <span className="badge badge-low" style={{ fontSize: '10px' }}>
            <CheckCircle2 size={11} />
            <span>Policy Guardrailed</span>
          </span>
        </div>
      </div>
    </div>
  );
};
