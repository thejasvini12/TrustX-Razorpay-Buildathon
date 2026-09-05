import {
  HealthResponse,
  AccountRiskRequest,
  RiskAssessmentResponse,
  FraudSpikeRequest,
  FraudSpikeResponse,
  AbuseRingRequest,
  AbuseRingResponse,
  RazorpayWebhookStatusResponse,
  RazorpayWebhookRiskEventResponse,
  LiveActivityData,
  LiveAbuseGraphResponse,
  LiveGraphAnalysisRequest,
  LiveFraudSpikeTelemetryResponse,
  LiveAbuseSimulationResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  public status: number;
  public details?: any;

  constructor(message: string, status: number, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      let errorDetails: any = null;
      try {
        const errorJson = await response.json();
        errorDetails = errorJson;
        if (errorJson.detail) {
          if (typeof errorJson.detail === 'string') {
            errorMessage = errorJson.detail;
          } else if (Array.isArray(errorJson.detail)) {
            errorMessage = errorJson.detail.map((e: any) => `${e.loc?.join('.') || 'param'}: ${e.msg}`).join(', ');
          }
        }
      } catch {
        // Fallback to text or generic error
      }
      throw new ApiError(errorMessage, response.status, errorDetails);
    }

    return (await response.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    // Network / fetch failure
    throw new ApiError(
      err?.message || 'Unable to connect to TrustX backend server. Please verify backend is running on port 8000.',
      0
    );
  }
}

export const riskApi = {
  /** Check engine health and model status */
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health', { method: 'GET' });
  },

  /** Retrieve an authentic account profile from the backend registry by ID */
  async getAccountProfile(accountId: string): Promise<AccountRiskRequest> {
    return request<AccountRiskRequest>(`/risk/account/${encodeURIComponent(accountId)}`, {
      method: 'GET',
    });
  },

  /** Retrieve real-time live activity for an account */
  async getAccountLiveActivity(accountId: string): Promise<LiveActivityData> {
    return request<LiveActivityData>(`/risk/account/${encodeURIComponent(accountId)}/live`, {
      method: 'GET',
    });
  },

  /** Retrieve sample account IDs from the backend registry */
  async getSampleAccounts(): Promise<string[]> {
    const res = await request<{ samples: string[]; total_available: number }>('/risk/accounts/samples', {
      method: 'GET',
    });
    return res.samples || [];
  },

  /** Score an account profile for coordinated abuse and return risk */
  async scoreAccount(payload: AccountRiskRequest): Promise<RiskAssessmentResponse> {
    return request<RiskAssessmentResponse>('/risk/score', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /** Detect temporal fraud spikes, velocity bursts, and 5-min sub-window surges */
  async detectFraudSpike(payload: FraudSpikeRequest): Promise<FraudSpikeResponse> {
    return request<FraudSpikeResponse>('/risk/fraud-spike', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /** Retrieve live rolling telemetry and 5m/1h window metrics for Fraud Spike */
  async getLiveFraudTelemetry(merchantId?: string): Promise<LiveFraudSpikeTelemetryResponse> {
    const query = merchantId ? `?merchant_id=${encodeURIComponent(merchantId)}` : '';
    return request<LiveFraudSpikeTelemetryResponse>(`/risk/fraud-spike/live${query}`, {
      method: 'GET',
    });
  },

  /** Evaluate current live telemetry using the existing frozen FraudSpikeDetector */
  async evaluateLiveFraudSpike(merchantId?: string): Promise<FraudSpikeResponse> {
    return request<FraudSpikeResponse>('/risk/fraud-spike/live/evaluate', {
      method: 'POST',
      body: JSON.stringify(merchantId ? { merchant_id: merchantId } : {}),
    });
  },

  /** Detect coordinated abuse rings across bipartite graph topologies */
  async detectAbuseRing(payload: AbuseRingRequest): Promise<AbuseRingResponse> {
    return request<AbuseRingResponse>('/risk/abuse-ring', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /** Get operational telemetry and health metrics for the Razorpay Test Mode webhook pipeline */
  async getRazorpayWebhookStatus(): Promise<RazorpayWebhookStatusResponse> {
    return request<RazorpayWebhookStatusResponse>('/webhooks/razorpay/status', {
      method: 'GET',
    });
  },

  /** Retrieve recent risk events from Razorpay Test Mode ingestion */
  async getRazorpayRecentEvents(): Promise<RazorpayWebhookRiskEventResponse[]> {
    return request<RazorpayWebhookRiskEventResponse[]>('/webhooks/razorpay/events', {
      method: 'GET',
    });
  },

  /** Get operational state, candidate clusters, and recent linkages from the live abuse graph */
  async getLiveAbuseGraph(): Promise<LiveAbuseGraphResponse> {
    return request<LiveAbuseGraphResponse>('/risk/abuse-ring/live', {
      method: 'GET',
    });
  },

  /** Get live graph subgraph and candidate cluster for a specific account */
  async getLiveAbuseGraphForAccount(accountId: string): Promise<any> {
    return request<any>(`/risk/abuse-ring/live/${encodeURIComponent(accountId)}`, {
      method: 'GET',
    });
  },

  /** Evaluate a live candidate cluster using the frozen Abuse-Ring Sentinel */
  async analyzeLiveCluster(params?: LiveGraphAnalysisRequest): Promise<AbuseRingResponse> {
    return request<AbuseRingResponse>('/risk/abuse-ring/live/analyze', {
      method: 'POST',
      body: params ? JSON.stringify(params) : undefined,
    });
  },

  /** Execute a deterministic live attack simulation scenario */
  async simulateLiveAbuseRing(scenario: string): Promise<LiveAbuseSimulationResponse> {
    return request<LiveAbuseSimulationResponse>('/risk/abuse-ring/live/simulate', {
      method: 'POST',
      body: JSON.stringify({ scenario }),
    });
  },
};
