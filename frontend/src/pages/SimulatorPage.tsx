import React from 'react';
import { useSimulator } from '../hooks/useSimulator';
import { SimulatorScenarioDeck } from '../components/simulator/SimulatorScenarioDeck';
import { SimulatorExecutionTimeline } from '../components/simulator/SimulatorExecutionTimeline';
import { SimulatorResultMatrix } from '../components/simulator/SimulatorResultMatrix';
import { SimulatorSynthesisPanel } from '../components/simulator/SimulatorSynthesisPanel';
import {
  Zap,
  Play,
  RotateCcw,
  ShieldCheck,
  Target,
  FileText,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';

export const SimulatorPage: React.FC = () => {
  const {
    currentScenario,
    availableScenarios,
    selectScenario,
    status,
    stages,
    accountRiskResult,
    fraudSpikeResult,
    abuseRingResult,
    sequentialFraudResults,
    totalLatencyMs,
    overallError,
    runSimulation,
    resetSimulation,
  } = useSimulator('legitimate_buyer');

  const isRunning = status === 'RUNNING';
  const isCompleted = status === 'COMPLETED';
  const isPartialFailure = status === 'PARTIAL_FAILURE';
  const isError = status === 'ERROR';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 1. Simulator Studio Header */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                padding: '10px',
                borderRadius: 'var(--radius-lg)',
                backgroundColor: 'rgba(99, 102, 241, 0.12)',
                color: 'var(--accent-indigo)',
              }}
            >
              <Zap size={22} />
            </div>
            <div>
              <h2 className="card-title" style={{ fontSize: '18px' }}>
                Multi-Engine Attack & Defense Simulator
              </h2>
              <p className="card-description" style={{ fontSize: '13px' }}>
                Orchestrate real-time attack scenarios across Account Risk, Fraud Spike, and Abuse Ring engines using live FastAPI backend pipelines.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-cyan" style={{ fontSize: '11px' }}>
              Real API Orchestration
            </span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '11px',
                fontWeight: '600',
                padding: '3px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: isRunning
                  ? 'rgba(56, 189, 248, 0.15)'
                  : isCompleted
                  ? 'rgba(16, 185, 129, 0.15)'
                  : isPartialFailure
                  ? 'rgba(245, 158, 11, 0.15)'
                  : isError
                  ? 'rgba(244, 63, 94, 0.15)'
                  : 'rgba(100, 116, 139, 0.15)',
                color: isRunning
                  ? 'var(--accent-cyan)'
                  : isCompleted
                  ? 'var(--risk-low)'
                  : isPartialFailure
                  ? 'var(--risk-medium)'
                  : isError
                  ? 'var(--risk-high)'
                  : 'var(--text-muted)',
                border: isRunning
                  ? '1px solid rgba(56, 189, 248, 0.3)'
                  : isCompleted
                  ? '1px solid rgba(16, 185, 129, 0.3)'
                  : isPartialFailure
                  ? '1px solid rgba(245, 158, 11, 0.3)'
                  : isError
                  ? '1px solid rgba(244, 63, 94, 0.3)'
                  : '1px solid var(--border-subtle)',
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: isRunning
                    ? 'var(--accent-cyan)'
                    : isCompleted
                    ? 'var(--risk-low)'
                    : isPartialFailure
                    ? 'var(--risk-medium)'
                    : isError
                    ? 'var(--risk-high)'
                    : 'var(--text-muted)',
                }}
              />
              {status === 'IDLE'
                ? 'Ready for Simulation'
                : status === 'RUNNING'
                ? 'Executing Pipelines...'
                : status === 'COMPLETED'
                ? 'Simulation Completed'
                : status === 'PARTIAL_FAILURE'
                ? 'Partial Failure'
                : 'Execution Error'}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Scenario Deck */}
      <SimulatorScenarioDeck
        scenarios={availableScenarios}
        selectedScenarioId={currentScenario.id}
        onSelectScenario={selectScenario}
        disabled={isRunning}
      />

      {/* 3. Selected Scenario Brief & Execution Bar */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxWidth: '780px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Target size={16} color="var(--accent-cyan)" />
              <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-cyan)' }}>
                Target Scenario Specification
              </span>
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
              {currentScenario.name}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              {currentScenario.shortDescription}
            </p>
          </div>

          {/* Action Control Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={resetSimulation}
              disabled={isRunning || status === 'IDLE'}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <RotateCcw size={14} />
              Reset
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={runSimulation}
              disabled={isRunning}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 18px',
                fontSize: '13px',
                fontWeight: '600',
              }}
            >
              <Play size={15} />
              {isRunning ? 'Running Simulation...' : 'Run Simulation'}
            </button>
          </div>
        </div>

        {/* Operational Narrative & Objective Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '12px',
            backgroundColor: 'var(--bg-app)',
            padding: '12px 14px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)' }}>
              <ShieldCheck size={13} color="var(--risk-low)" />
              DEMONSTRATION OBJECTIVE
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              {currentScenario.demoObjective}
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)' }}>
              <FileText size={13} color="var(--accent-cyan)" />
              OPERATIONAL STORY
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              {currentScenario.operationalStory}
            </p>
          </div>
        </div>

        {/* Core Differentiator Callout Banner */}
        {currentScenario.keyDifferentiatorNote && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              fontSize: '12px',
              color: 'var(--text-primary)',
            }}
          >
            <Sparkles size={16} color="var(--accent-indigo)" style={{ flexShrink: 0 }} />
            <div>
              <strong style={{ color: 'var(--accent-indigo)' }}>TrustX Architectural Advantage: </strong>
              <span style={{ color: 'var(--text-secondary)' }}>{currentScenario.keyDifferentiatorNote}</span>
            </div>
          </div>
        )}

        {/* Global Error Notice if failed */}
        {overallError && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(244, 63, 94, 0.1)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              fontSize: '12px',
              color: 'var(--risk-high)',
            }}
          >
            <AlertTriangle size={16} style={{ flexShrink: 0 }} />
            <span>{overallError}</span>
          </div>
        )}
      </div>

      {/* 4. Execution Timeline */}
      <SimulatorExecutionTimeline
        stages={stages}
        status={status}
        totalLatencyMs={totalLatencyMs}
        isPersistentIncident={currentScenario.id === 'persistent_incident'}
      />

      {/* 5. Multi-Engine Output Matrix */}
      <SimulatorResultMatrix
        scenario={currentScenario}
        status={status}
        accountRiskResult={accountRiskResult}
        fraudSpikeResult={fraudSpikeResult}
        abuseRingResult={abuseRingResult}
        sequentialFraudResults={sequentialFraudResults}
      />

      {/* 6. Cross-Engine Intelligence Synthesis */}
      <SimulatorSynthesisPanel
        scenario={currentScenario}
        status={status}
        accountRiskResult={accountRiskResult}
        fraudSpikeResult={fraudSpikeResult}
        abuseRingResult={abuseRingResult}
        sequentialFraudResults={sequentialFraudResults}
      />
    </div>
  );
};

export default SimulatorPage;
