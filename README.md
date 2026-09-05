# AI-RISK: Defense-Only Merchant Abuse & Abuse-Ring Detection Engine

**Track 02: Coordinated Merchant Abuse / Abuse-Ring Detection**  
*Milestone 1: Production-Grade ML Risk & Inference Engine*

---

## 1. Overview & Problem Scope

This repository provides a **defense-only AI Risk Management Engine** engineered specifically for e-commerce platforms and digital merchants to detect and mitigate **coordinated abuse**, including:

- **Serial Wardrobing & Refund Abuse**: High-velocity order-return loops on high-value items.
- **Coordinated Abuse Rings & Syndicates**: Distributed multi-account clusters exhibiting shared device footprints, high payment card cycling, and collusive dispute patterns.
- **Voucher / Promo Exploitation Bots**: Burst transactions across short-lived accounts created to drain promotions.

> **Important Defense Disclaimer**: This system is designed exclusively for merchant defense, risk mitigation, and fraud prevention. It contains no components for evading detection or committing abuse.

---

## 2. Project Architecture

```
AI-RISK/
├── data/                         # Datasets & partitions
│   ├── synthetic_accounts.csv   # Full synthetic dataset (reproducible seed=42)
│   ├── train.csv                # Training partition (80%)
│   └── test.csv                 # Held-out evaluation partition (20%)
├── models/                       # Model artifacts & metadata
│   ├── risk_engine_rf.joblib    # Serialized unified Scikit-Learn Pipeline
│   └── model_metadata.json      # Training parameters & evaluation metrics
├── src/                          # Modular Python engine
│   ├── __init__.py
│   ├── features.py              # Feature schemas, sanitization, validation & data quality scoring
│   ├── data_generator.py        # Realistic behavioral & syndicate data generator
│   ├── model_pipeline.py        # Unified Pipeline (ColumnTransformer + Imputer + OneHot + RF)
│   ├── evaluate.py              # Precision, Recall, F1, CM, FPR metrics
│   ├── train.py                 # Training pipeline & artifact persistence
│   └── risk_scorer.py           # Robust inference engine (predict_account_risk)
├── tests/                        # Automated unit & integration tests
│   ├── test_data_generator.py   # Dataset schema & reproducibility checks
│   └── test_risk_scorer.py      # Unseen records, missing values, extreme values & edge cases
├── run_pipeline.py              # End-to-end one-click runner
├── requirements.txt             # Project dependencies
└── README.md                    # Documentation & runbook
```

---

## 3. Account Prediction Input Schema

| Field Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `account_id` | String | No | Unique account identifier (*Never used as a predictive feature*) |
| `order_count` | Numeric | Yes* | Total lifetime orders placed (must be $\ge 0$) |
| `return_count` | Numeric | Yes* | Total returns initiated ($\le$ `order_count`) |
| `refund_count` | Numeric | Yes* | Total refunds claimed ($\le$ `order_count`) |
| `total_spend` | Numeric | Yes* | Cumulative dollar amount spent |
| `average_order_value` | Numeric | Yes* | Average spend per order ($) |
| `account_age_days` | Numeric | Yes* | Account age in days |
| `device_count` | Numeric | Yes* | Number of distinct hardware devices linked |
| `ip_count` | Numeric | Yes* | Number of distinct IP addresses used |
| `payment_instrument_count` | Numeric | Yes* | Distinct payment cards/methods linked |
| `return_rate` | Numeric | Yes* | `return_count / order_count` (clamped to $[0, 1]$) |
| `refund_rate` | Numeric | Yes* | `refund_count / order_count` (clamped to $[0, 1]$) |
| `high_value_order_count` | Numeric | Yes* | Orders exceeding high-value threshold |
| `suspicious_activity_score` | Numeric | Yes* | Ring connectivity / velocity indicator ($[0, 1]$) |
| `device_type` | Categorical | Optional | E.g. `mobile_ios`, `desktop_chrome`, `emulator_bot` |
| `primary_payment_method` | Categorical | Optional | E.g. `credit_card`, `virtual_card`, `paypal` |

*\*Note: If any fields are omitted, the engine does NOT crash. It safely imputes default values, flags detailed warnings, and adjusts the `data_quality_score`.*

---

## 4. Unified Preprocessing & Pipeline Guarantee

The engine uses a single, reusable **`sklearn.pipeline.Pipeline`**:
1. **Numeric Transformer**: `SimpleImputer(strategy="median")`
2. **Categorical Transformer**: `SimpleImputer(strategy="constant", fill_value="unknown")` + `OneHotEncoder(handle_unknown="ignore")`
3. **Classifier**: `RandomForestClassifier(n_estimators=150, max_depth=12, min_samples_split=4, min_samples_leaf=2, class_weight="balanced_subsample")`

The exact same pipeline is executed during training and live inference, ensuring consistency and preventing training-serving skew.

---

## 5. Input Validation & Fault Tolerance Rules

1. **Unseen Account IDs**: `account_id` is stripped from model inputs and preserved only for traceability.
2. **Missing Values**: Imputed with safe defaults, reducing `data_quality_score` with informative warnings.
3. **Negative Numbers**: Automatically clamped to `0.0` with warning logs.
4. **Count Inconsistencies**: If `return_count > order_count` or `refund_count > order_count`, counts are clamped to `order_count` and rates are recalculated.
5. **Extreme Values**: Values exceeding operational bounds (e.g. spend > $1,000,000, age > 25,000 days) are clamped to prevent numerical distortion.
6. **Unknown Categoricals**: Any previously unseen device or payment method is handled gracefully via `handle_unknown='ignore'`.

---

## 6. Risk Scoring & Decision Tiers

$$\text{Risk Score} = \text{round}(P(\text{abuse} = 1) \times 100)$$

| Risk Score Range | Risk Level | Defense Action | Description |
| :---: | :---: | :---: | :--- |
| **0 – 29** | `LOW` | `ALLOW` | Standard customer behavior; frictionless checkout & returns. |
| **30 – 69** | `MEDIUM` | `MANUAL_REVIEW` | Borderline signals; flagged for risk analyst investigation or 2FA verification. |
| **70 – 100** | `HIGH` | `CHALLENGE_OR_BLOCK` | Strong abuse syndicate or wardrobing indicators; order hold or return restriction. |

---

## 7. Python API & Prediction Usage

```python
from src.risk_scorer import predict_account_risk

# Single unseen account (even with missing fields or unknown categories)
unseen_account = {
    "account_id": "ACC_NEW_RING_EXPL_777",
    "order_count": 18,
    "return_count": 15,
    "refund_count": 14,
    "total_spend": 2800.0,
    "average_order_value": 155.55,
    "account_age_days": 12,
    "device_count": 5,
    "ip_count": 6,
    "payment_instrument_count": 5,
    "return_rate": 0.8333,
    "refund_rate": 0.7778,
    "high_value_order_count": 11,
    "suspicious_activity_score": 0.94,
    "device_type": "emulator_bot",
    "primary_payment_method": "virtual_card",
}

result = predict_account_risk(unseen_account)
print(result)
# Output:
# {
#   'account_id': 'ACC_NEW_RING_EXPL_777',
#   'risk_probability': 1.0,
#   'risk_score': 100,
#   'risk_level': 'HIGH',
#   'data_quality_score': 1.0,
#   'warnings': [],
#   'recommended_action': 'CHALLENGE_OR_BLOCK',
#   'risk_factors': ['High return rate (83.3%)', 'High refund claim rate (77.8%)', 'Elevated syndicate activity indicator (0.94)', ...]
# }
```

---

## 8. Quickstart & Testing

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run automated test suite
python -m pytest

# 3. Run complete training, evaluation & inference pipeline
python run_pipeline.py
```

---

## 9. Razorpay Test Mode Real-Time Webhook Setup

AI-RISK integrates with **Razorpay Test Mode** to provide near-real-time transaction event ingestion directly into the frozen Fraud Spike detection engine and `FiveMinuteTelemetryStore`.

### Environment Configuration

Set the following environment variables (e.g. in `.env`, which is strictly ignored by Git):

```bash
RAZORPAY_KEY_ID=rzp_test_yourKeyIdHere
RAZORPAY_KEY_SECRET=yourKeySecretHere
RAZORPAY_WEBHOOK_SECRET=yourDedicatedWebhookSecretHere
RAZORPAY_DEFAULT_MERCHANT_ID=MERCH_RAZORPAY_TEST  # Optional fallback
```

> [!IMPORTANT]
> - `RAZORPAY_WEBHOOK_SECRET` is the dedicated secret created in the Razorpay Dashboard Webhook settings. It is distinct from the API Key Secret.
> - Secrets are **never** logged, exposed in API responses, or committed to source control.

### Webhook Ingestion Architecture

```
Razorpay Test Mode (payment.captured / payment.authorized / payment.failed)
        ↓
POST /webhooks/razorpay
        ↓
Raw-Body HMAC-SHA256 Signature Verification (constant-time)
        ↓
x-razorpay-event-id Idempotency Store (bounded: 10,000)
        ↓
Order-Independent Canonical Payment Deduplication (payment.captured canonical)
        ↓
Internal Normalized RiskPaymentEvent (zero data fabrication)
        ↓
Existing FiveMinuteTelemetryStore (merchant-isolated)
        ↓
Existing Fraud Spike Detector (P1 / P3 / P5 preserved)
        ↓
Risk Operations Live Feed Representation
```

### Supported Razorpay Events

- **`payment.captured`**: Canonical successful payment event. Increments 5-minute transaction velocity.
- **`payment.authorized`**: Tracked in payment lifecycle state; does not double-count transactions if captured arrives.
- **`payment.failed`**: Ingested as a payment failure signal. **Never** labeled as fraud (`fraud_count = 0`).
- **`order.paid` / `refund.processed` / others**: Acknowledged safely (HTTP 200) without modifying velocity telemetry.

### Razorpay Dashboard Setup Steps

1. Log in to the [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. Toggle the switch in the top header to **Test Mode**.
3. Navigate to **Settings** > **Webhooks**.
4. Click **+ Add New Webhook**.
5. Set the **Webhook URL** to your publicly reachable HTTPS endpoint:
   ```
   https://<your-public-domain-or-tunnel>/webhooks/razorpay
   ```
   *(Note: For local development, expose port 8000 via a secure tunnel).*
6. Enter a strong secret in the **Secret** field and set this exact value as `RAZORPAY_WEBHOOK_SECRET` in your environment.
7. Under **Active Events**, enable:
   - `payment.authorized`
   - `payment.captured`
   - `payment.failed`
8. Click **Save**.
9. Start the backend:
   ```bash
   python -m uvicorn src.api:app --reload --port 8000
   ```
10. Generate a Test Mode payment via Razorpay Payment Link or Test Checkout.
11. Confirm the webhook reaches AI-RISK via `GET /webhooks/razorpay/status`.
12. Inspect the normalized payment event and 5-minute telemetry accumulation.

---

## 9. Live Abuse Graph & Coordinated Syndicate Detection

### Bipartite Graph Architecture

The **Live Abuse Graph** (`src/live_abuse_graph.py`) correlates entities across incoming checkouts and verified Razorpay webhooks:

```
ACCOUNT A ──┬── DEVICE_X
            ├── IP_HASH_X (Privacy-Safe Salted SHA-256)
            ├── ADDRESS_HASH_X (Privacy-Safe Salted SHA-256)
            └── PAYMENT_A (Canonical Payment)

ACCOUNT B ──┬── DEVICE_X
            ├── IP_HASH_X
            ├── ADDRESS_HASH_X
            └── PAYMENT_B
```

- **Zero Hard-Coded Rules**: Shared infrastructure creates candidate clusters, but the **frozen Abuse-Ring ML model** (`AbuseRingSentinel`) remains the sole decision maker.
- **Privacy Model**:
  - Raw client IPs and addresses are never stored in graph nodes, edges, logs, or API responses.
  - IPs are transformed to `IP_HASH_<12-hex>` using trusted connection extraction.
  - Addresses are normalized (punctuation/case/spacing stripped) and transformed to `ADDRESS_HASH_<12-hex>`.
- **Bystander Protection**:
  - Accounts that share common carrier infrastructure (e.g. apartment building address or cafe Wi-Fi IP) but maintain independent devices, independent payments, and normal transaction behavior are classified as `INCIDENTAL_BYSTANDER` with `LOW` risk contribution.
  - When an incidental bystander is present in a candidate ring, ring-wide punitive gates (`BLOCK_ENTIRE_RING`) are strictly inhibited, protecting legitimate consumers.

---

## 10. Live Attack Simulation Engine (Phase 4)

A deterministic development and demo simulator (`scratch/simulate_live_abuse_ring.py`) and API endpoint (`POST /risk/abuse-ring/live/simulate`) validate the full pipeline:

1. **`CLEAN_SHARED_INFRASTRUCTURE`**: Benign accounts sharing office/lab device + address + IP.
   - **Result**: `Score ~0.166`, `NO_RING`, Action: `NO_ACTION`. Demonstrates shared infrastructure $\ne$ automatic fraud.
2. **`COORDINATED_SUSPICIOUS_CLUSTER`**: Elevated velocity and return coordination.
   - **Result**: `Score ~0.800`, `LIKELY_RING`, Action: `REVIEW_CLUSTER`.
3. **`HIGH_CONFIDENCE_ABUSE_RING`**: Synthetic syndicate with bot emulator devices, rapid transaction velocity, and failed payment bursts.
   - **Result**: `Score ~0.969`, `HIGH_CONFIDENCE_RING`, Action: `BLOCK_ENTIRE_RING`.
4. **`BYSTANDER_MIXED_CLUSTER`**: Syndicate sharing residential address with a benign consumer.
   - **Result**: `Score ~0.929`, `HIGH_CONFIDENCE_RING`, Action: `REVIEW_ACCOUNTS`. The bystander is protected (`INCIDENTAL_BYSTANDER`, `LOW` risk contribution) and `BLOCK_ENTIRE_RING` is blocked.

### Running Simulations

```bash
# Execute all scenarios
python scratch/simulate_live_abuse_ring.py --all

# Or run individual scenario
python scratch/simulate_live_abuse_ring.py --scenario CLEAN_SHARED_INFRASTRUCTURE
```

---

## 11. Verification & Automated Test Suite

```bash
# Run complete test suite (347 tests)
python -m pytest tests/

# Run targeted attack simulation suite (21 tests)
python -m pytest tests/test_live_abuse_ring_attack_simulation.py -v

# Run production frontend build (0 TypeScript / Vite errors)
cd frontend
npm run build
```

---

## 12. Local Quickstart & Demo Runbook

```bash
# 1. Backend Server
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload

# 2. Frontend Application
cd frontend
npm run dev

# 3. Clean Demo Reset
curl -X POST http://127.0.0.1:8000/risk/abuse-ring/live/reset
curl -X POST http://127.0.0.1:8000/risk/fraud-spike/live/reset
```


