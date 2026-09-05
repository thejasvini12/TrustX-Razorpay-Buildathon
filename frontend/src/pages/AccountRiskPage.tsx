import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AccountRiskRequest, RiskAssessmentResponse } from '../types/api';
import { riskApi, ApiError } from '../services/api';
import { useRiskFeed } from '../context/RiskFeedContext';
import { ScenarioPresets, PRESET_SCENARIOS } from '../components/account-risk/ScenarioPresets';
import { AccountRiskForm } from '../components/account-risk/AccountRiskForm';
import { RiskScoreCard } from '../components/account-risk/RiskScoreCard';
import { DefenseDecisionPanel } from '../components/account-risk/DefenseDecisionPanel';
import { DataQualityPanel } from '../components/account-risk/DataQualityPanel';
import { ExplainabilityPanel } from '../components/account-risk/ExplainabilityPanel';
import { FeatureContributionList } from '../components/account-risk/FeatureContributionList';
import { ReturnRiskPanel } from '../components/account-risk/ReturnRiskPanel';
import {
  AlertOctagon,
  Search,
  TestTube,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';

const SESSION_STORAGE_KEY = 'ai_risk_last_account_investigation';

const DEFAULT_FORM_DATA: AccountRiskRequest = {
  account_id: 'ACC_MERCHANT_90210',
  order_count: 12,
  return_count: 1,
  refund_count: 0,
  total_spend: 650.0,
  average_order_value: 54.17,
  account_age_days: 180,
  device_count: 1,
  ip_count: 2,
  payment_instrument_count: 1,
  high_value_order_count: 1,
  suspicious_activity_score: 0.05,
  device_type: 'desktop_chrome',
  primary_payment_method: 'credit_card',
};

export const AccountRiskPage: React.FC = () => {
  const [accountIdInput, setAccountIdInput] = useState<string>('ACC_MERCHANT_90210');
  const [formData, setFormData] = useState<AccountRiskRequest>(DEFAULT_FORM_DATA);
  const [profileLoaded, setProfileLoaded] = useState<boolean>(false);
  const [selectedPresetId, setSelectedPresetId] = useState<string | undefined>(undefined);
  const [activeMode, setActiveMode] = useState<'INVESTIGATE' | 'DEMO'>('INVESTIGATE');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [notFoundId, setNotFoundId] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<RiskAssessmentResponse | null>(null);
  const [isStale, setIsStale] = useState<boolean>(false);
  const [sampleIds, setSampleIds] = useState<string[]>([]);
  const [isRefreshingLive, setIsRefreshingLive] = useState<boolean>(false);

  const { addEvent } = useRiskFeed();

  // Restore previous investigation state from sessionStorage on component mount
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved && saved.accountId && saved.assessment) {
          setAccountIdInput(saved.accountId);
          if (saved.profile) {
            setFormData(saved.profile);
            setProfileLoaded(true);
          }
          setAssessment(saved.assessment);
        }
      }
    } catch (err) {
      console.warn('Could not restore session investigation state:', err);
    }

    // Fetch sample suggestions from AccountStore
    riskApi.getSampleAccounts()
      .then((ids) => {
        if (Array.isArray(ids) && ids.length > 0) {
          setSampleIds(ids);
        }
      })
      .catch(() => {
        // Fallback to internal constants if offline
      });
  }, []);

  // Calm 15-second polling for real-time Razorpay live activity ONLY while page is actively mounted
  useEffect(() => {
    if (!profileLoaded) return;
    const target = formData.account_id || accountIdInput;
    if (!target) return;

    let mounted = true;
    const intervalId = setInterval(async () => {
      try {
        const live = await riskApi.getAccountLiveActivity(target);
        if (mounted && live) {
          setFormData((prev) => ({
            ...prev,
            live_activity: live,
          }));
        }
      } catch {
        // Calm polling: silent failure without disturbing user
      }
    }, 15000); // 15-second calm polling constraint

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, [profileLoaded, formData.account_id, accountIdInput]);

  /**
   * Manual Refresh Handler for Live Activity
   */
  const handleRefreshLive = async () => {
    const target = formData.account_id || accountIdInput;
    if (!target) return;
    try {
      setIsRefreshingLive(true);
      const live = await riskApi.getAccountLiveActivity(target);
      setFormData((prev) => ({
        ...prev,
        live_activity: live,
      }));
    } catch (err) {
      console.warn('Failed to refresh live activity:', err);
    } finally {
      setIsRefreshingLive(false);
    }
  };

  /**
   * Primary Investigation Handler:
   * Account ID -> GET /risk/account/{account_id} -> populate profile -> POST /risk/score -> display assessment.
   */
  const handleInvestigate = async (targetId?: string) => {
    const target = (targetId || accountIdInput).trim();
    if (!target) return;

    setLoading(true);
    setError(null);
    setNotFoundId(null);

    try {
      // Step 1: Deterministic retrieval from AccountStore
      const profile = await riskApi.getAccountProfile(target);

      const accountId = profile.account_id || target;

      // Populate profile state
      setAccountIdInput(accountId);
      setFormData(profile);
      setProfileLoaded(true);
      setNotFoundId(null);

      // Step 2: Score using canonical RiskScorer ML pipeline
      const res = await riskApi.scoreAccount(profile);
      setAssessment(res);
      setIsStale(false);

      // Step 3: Session Persistence
      try {
        sessionStorage.setItem(
          SESSION_STORAGE_KEY,
          JSON.stringify({
            accountId,
            profile,
            assessment: res,
          })
        );
      } catch (storageErr) {
        console.warn('Session persistence error:', storageErr);
      }

      // Step 4: Publish/Update deduplicated Risk Operations event
      addEvent({
        id: `evt_acc_${accountId}`,
        engine: 'ACCOUNT_RISK',
        source: selectedPresetId ? 'SIMULATION' : 'MANUAL_INVESTIGATION',
        title: `Account Assessment (${accountId})`,
        entityId: accountId,
        entityType: 'ACCOUNT',
        severity: res.risk_level,
        score: res.risk_score,
        decision: res.recommended_action,
        rawMl: {
          probability: res.risk_probability,
          prediction: res.prediction,
        },
        evidence: res.risk_increasing_signals || res.risk_factors,
        policy: res.decision_policy
          ? {
              pattern: res.decision_policy.abuse_pattern,
              primaryAction: res.decision_policy.primary_action,
              reasoning: res.decision_policy.policy_reasoning,
            }
          : undefined,
        returnRisk: res.return_risk
          ? {
              score: res.return_risk.return_risk_score,
              level: res.return_risk.return_risk_level,
              action: res.return_risk.recommended_return_action,
              factors: res.return_risk.return_risk_factors,
            }
          : undefined,
      });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setNotFoundId(target);
          setAssessment(null);
          setProfileLoaded(false);
          setError(null);
        } else {
          setError(`API Error (${err.status}): ${err.message}`);
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to connect to TrustX backend engine.');
      }
    } finally {
      setLoading(false);
    }
  };

  /**
   * Re-score when manual parameters inside Advanced section are modified
   */
  const handleAssessModified = async () => {
    try {
      setLoading(true);
      setError(null);
      setNotFoundId(null);
      const res = await riskApi.scoreAccount(formData);
      setAssessment(res);
      setIsStale(false);

      // Persist modified assessment
      try {
        sessionStorage.setItem(
          SESSION_STORAGE_KEY,
          JSON.stringify({
            accountId: formData.account_id,
            profile: formData,
            assessment: res,
          })
        );
      } catch (storageErr) {
        console.warn('Session persistence error:', storageErr);
      }

      // Update Risk Operations event
      addEvent({
        id: `evt_acc_${formData.account_id || 'MODIFIED'}`,
        engine: 'ACCOUNT_RISK',
        source: 'MANUAL_INVESTIGATION',
        title: `Account Assessment (${formData.account_id || 'ACCOUNT'}) [Modified]`,
        entityId: formData.account_id || 'UNSEEN_ACCOUNT',
        entityType: 'ACCOUNT',
        severity: res.risk_level,
        score: res.risk_score,
        decision: res.recommended_action,
        rawMl: {
          probability: res.risk_probability,
          prediction: res.prediction,
        },
        evidence: res.risk_increasing_signals || res.risk_factors,
        policy: res.decision_policy
          ? {
              pattern: res.decision_policy.abuse_pattern,
              primaryAction: res.decision_policy.primary_action,
              reasoning: res.decision_policy.policy_reasoning,
            }
          : undefined,
        returnRisk: res.return_risk
          ? {
              score: res.return_risk.return_risk_score,
              level: res.return_risk.return_risk_level,
              action: res.return_risk.recommended_return_action,
              factors: res.return_risk.return_risk_factors,
            }
          : undefined,
      });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(`API Error (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to connect to TrustX backend engine.');
      }
    } finally {
      setLoading(false);
    }
  };

  /**
   * Demo Scenarios handler:
   * Every demo scenario flows through the SAME lookup -> scoring pipeline
   */
  const handlePresetSelect = (presetData: AccountRiskRequest) => {
    const matched = PRESET_SCENARIOS.find((p) => p.data.account_id === presetData.account_id);
    setSelectedPresetId(matched?.id);
    setActiveMode('INVESTIGATE');
    // Flow through canonical lookup and scoring pipeline
    handleInvestigate(presetData.account_id);
  };

  const handleFormChange = (newData: AccountRiskRequest) => {
    setFormData(newData);
    setSelectedPresetId(undefined);
    setError(null);
    if (assessment) {
      setIsStale(true);
    }
  };

  const handleReset = () => {
    setFormData(DEFAULT_FORM_DATA);
    setAccountIdInput('ACC_MERCHANT_90210');
    setSelectedPresetId(undefined);
    setError(null);
    setNotFoundId(null);
    setAssessment(null);
    setProfileLoaded(false);
    setIsStale(false);
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* 1. Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            Account Risk
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Investigate account behavioral profiles from authentic datasets and identify abuse before it becomes a loss.
          </p>
        </div>

        {/* Mode Selector Tabs */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className={activeMode === 'INVESTIGATE' ? 'btn btn-primary' : 'btn btn-secondary'}
            onClick={() => setActiveMode('INVESTIGATE')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px' }}
          >
            <Search size={14} />
            <span>Investigate Account</span>
          </button>
          <button
            type="button"
            className={activeMode === 'DEMO' ? 'btn btn-primary' : 'btn btn-secondary'}
            onClick={() => setActiveMode('DEMO')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px' }}
          >
            <TestTube size={14} />
            <span>Demo Scenarios</span>
          </button>
        </div>
      </div>

      {/* 2. Current Assessment Hero Section */}
      <div
        className="card"
        style={{
          padding: '18px 24px',
          backgroundColor: assessment ? 'var(--bg-card)' : 'var(--bg-app)',
          border: assessment
            ? `1px solid ${
                assessment.risk_level === 'HIGH'
                  ? 'var(--risk-high-border)'
                  : assessment.risk_level === 'MEDIUM'
                  ? 'var(--risk-medium-border)'
                  : 'var(--border-subtle)'
              }`
            : '1px dashed var(--border-subtle)',
        }}
      >
        {!assessment ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div
                style={{
                  padding: '8px',
                  borderRadius: '50%',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  color: 'var(--text-muted)',
                }}
              >
                <ShieldCheck size={20} />
              </div>
              <div>
                <div style={{ fontSize: '14.5px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  No account assessed
                </div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                  Enter an Account ID above to retrieve its behavioral record and evaluate operational risk.
                </div>
              </div>
            </div>

            <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
              Ready for assessment
            </span>
          </div>
        ) : (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
              {/* Account ID */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '10.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Account
                </span>
                <span style={{ fontSize: '15px', fontWeight: '800', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-primary)' }}>
                  {assessment.account_id}
                </span>
              </div>

              {/* Risk Score */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '10.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Risk Score
                </span>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                  <span style={{ fontSize: '20px', fontWeight: '800', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-primary)' }}>
                    {assessment.risk_score}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>/ 100</span>
                  <span
                    className={`badge ${
                      assessment.risk_level === 'HIGH'
                        ? 'badge-rose'
                        : assessment.risk_level === 'MEDIUM'
                        ? 'badge-amber'
                        : 'badge-green'
                    }`}
                    style={{ fontSize: '10px', marginLeft: '4px' }}
                  >
                    {assessment.risk_level}
                  </span>
                </div>
              </div>

              {/* Operational Decision */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '10.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Decision
                </span>
                <span
                  style={{
                    fontSize: '14.5px',
                    fontWeight: '800',
                    color:
                      assessment.recommended_action.includes('BLOCK') || assessment.recommended_action.includes('CHALLENGE')
                        ? 'var(--risk-high)'
                        : assessment.recommended_action.includes('REVIEW')
                        ? 'var(--risk-medium)'
                        : 'var(--risk-low)',
                  }}
                >
                  {assessment.recommended_action}
                </span>
              </div>
            </div>

            {/* Link to Risk Operations */}
            <Link
              to="/risk-operations"
              className="btn btn-secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
            >
              <span>View in Risk Operations</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        )}
      </div>

      {/* 3. Mode Content: DEMO SCENARIOS or INVESTIGATE ACCOUNT */}
      {activeMode === 'DEMO' ? (
        <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-purple" style={{ fontSize: '10.5px' }}>
                DEMO / TEST SCENARIOS
              </span>
            </div>
            <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '6px' }}>
              Synthetic Benchmark Profiles
            </h2>
            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Select a benchmark test scenario. Each scenario executes the canonical lookup → profile load → ML risk assessment workflow.
            </p>
          </div>

          <ScenarioPresets onSelect={handlePresetSelect} selectedId={selectedPresetId} />
        </div>
      ) : (
        /* INVESTIGATE ACCOUNT MODE */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Account Investigation Console */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <AccountRiskForm
              accountIdInput={accountIdInput}
              onAccountIdChange={setAccountIdInput}
              onInvestigate={handleInvestigate}
              onAssessModified={handleAssessModified}
              onRefreshLive={handleRefreshLive}
              isRefreshingLive={isRefreshingLive}
              formData={formData}
              onFormChange={handleFormChange}
              onReset={handleReset}
              loading={loading}
              profileLoaded={profileLoaded}
              sampleIds={sampleIds}
            />
          </div>

          {/* Account Not Found Clean State (404) */}
          {notFoundId && (
            <div
              className="card"
              style={{
                padding: '22px 24px',
                backgroundColor: 'rgba(239, 68, 68, 0.06)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: 'var(--radius-lg)',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                <div
                  style={{
                    padding: '10px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(239, 68, 68, 0.12)',
                    color: 'var(--risk-high)',
                    flexShrink: 0,
                  }}
                >
                  <AlertOctagon size={22} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '15px', fontWeight: '800', color: 'var(--risk-high)' }}>
                      Account Not Found (404)
                    </h3>
                    <span className="badge badge-rose" style={{ fontSize: '10px' }}>
                      NO RECORD
                    </span>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                    No behavioral records or transactional history exist for identifier{' '}
                    <strong style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-primary)' }}>
                      "{notFoundId}"
                    </strong>{' '}
                    in the verified AccountStore dataset.
                  </p>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    TrustX strictly adheres to real telemetry and does not fabricate customer data or return randomized defaults.
                  </p>
                </div>
              </div>

              <div
                style={{
                  borderTop: '1px solid rgba(239, 68, 68, 0.15)',
                  paddingTop: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  flexWrap: 'wrap',
                }}
              >
                <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)', fontWeight: '600' }}>
                  Try a verified account:
                </span>
                {['ACC_MERCHANT_90210', 'ACC_WARD_00001', 'ACC_LEGIT_STD_01502'].map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => {
                      setAccountIdInput(id);
                      handleInvestigate(id);
                    }}
                    className="btn btn-secondary"
                    style={{ fontSize: '11.5px', padding: '5px 12px', fontFamily: 'JetBrains Mono, monospace' }}
                  >
                    {id}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* General Error Banner */}
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

          {/* Stale Warning Banner */}
          {isStale && (
            <div
              style={{
                padding: '10px 16px',
                backgroundColor: 'var(--risk-medium-bg)',
                border: '1px solid var(--risk-medium-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--risk-medium)',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span>Parameters have been modified since last assessment. Re-score or investigate to refresh evaluation.</span>
            </div>
          )}

          {/* 4. Assessment Results Grid */}
          {assessment && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {/* Primary Assessment Cards Row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
                <RiskScoreCard assessment={assessment} />
                <DefenseDecisionPanel decisionPolicy={assessment.decision_policy} />
                <DataQualityPanel score={assessment.data_quality_score} warnings={assessment.warnings} />
              </div>

              {/* Dedicated Return Risk Section */}
              {assessment.return_risk && <ReturnRiskPanel returnRisk={assessment.return_risk} />}

              {/* Explainability Section: "Why this result?" */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
                    Why this result?
                  </h3>
                  <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    Dual-layer explainability decomposing frozen Random Forest feature weights and deterministic policy rules.
                  </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
                  <ExplainabilityPanel
                    explanationSummary={assessment.explanation_summary}
                    decisionReasoning={assessment.decision_policy?.policy_reasoning}
                    increasingSignals={assessment.risk_increasing_signals}
                    reducingSignals={assessment.risk_reducing_signals}
                  />
                  {assessment.feature_contributions && (
                    <FeatureContributionList contributions={assessment.feature_contributions} />
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AccountRiskPage;
