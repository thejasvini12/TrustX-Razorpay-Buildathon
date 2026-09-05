"""Comprehensive test suite for Live Fraud Spike Telemetry Store and API endpoints.

Tests:
1. Empty store
2. Event recording
3. Rolling 5-minute calculation
4. Rolling 1-hour calculation
5. Event expiration from rolling windows
6. Duplicate event_id rejection
7. authorized + captured counts exactly once
8. duplicate captured rejection
9. failed payment increments failed_payment_count
10. failed payment does NOT increment fraud_count
11. explicit notes.is_fraud=True increments fraud_count
12. duplicate explicit fraud event does not double-count
13. chronological 5-minute buckets
14. bounded memory behavior
15. reset()
16. export_fraud_spike_request()
17. GET /risk/fraud-spike/live
18. POST /risk/fraud-spike/live/evaluate
19. live result source is LIVE_ASSESSMENT / webhook integration
20. manual simulation remains unaffected
"""

import time
import pytest
from fastapi.testclient import TestClient

from src.api import app, get_spike_detector
from src.live_fraud_telemetry import LiveFraudSpikeTelemetryStore, get_live_fraud_telemetry_store
from src.razorpay_webhook import get_webhook_manager, get_webhook_secret, verify_razorpay_signature
import hmac
import hashlib
import json


@pytest.fixture
def client():
    """Create a FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the global live telemetry store before and after each test."""
    store = get_live_fraud_telemetry_store()
    store.reset()
    yield
    store.reset()


# Test 1: Empty store
def test_1_empty_store():
    store = LiveFraudSpikeTelemetryStore()
    metrics = store.get_rolling_metrics(merchant_id="MERCH_TEST_EMPTY")
    assert metrics["status"] == "IDLE"
    assert metrics["total_events_processed"] == 0
    assert metrics["last_event_timestamp"] is None
    assert metrics["rolling_5m"]["tx_count"] == 0
    assert metrics["rolling_5m"]["tx_volume"] == 0.0
    assert metrics["rolling_5m"]["failed_count"] == 0
    assert metrics["rolling_5m"]["fraud_count"] == 0
    assert metrics["rolling_1h"]["tx_count"] == 0
    assert metrics["rolling_1h"]["tx_volume"] == 0.0
    assert metrics["rolling_1h"]["failed_count"] == 0
    assert metrics["rolling_1h"]["fraud_count"] == 0
    assert metrics["unique_devices_1h"] == 0


# Test 2: Event recording
def test_2_event_recording():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()
    res = store.record_webhook_event(
        event_id="evt_001",
        event_type="payment.captured",
        payment_id="pay_001",
        amount=500.0,
        currency="INR",
        status="captured",
        merchant_id="MERCH_01",
        timestamp=now,
    )
    assert res["accepted"] is True
    assert res["counted_velocity"] is True

    metrics = store.get_rolling_metrics(merchant_id="MERCH_01", now_ts=now)
    assert metrics["status"] == "ACTIVE"
    assert metrics["total_events_processed"] == 1
    assert metrics["rolling_5m"]["tx_count"] == 1
    assert metrics["rolling_5m"]["tx_volume"] == 500.0
    assert metrics["rolling_1h"]["tx_count"] == 1
    assert metrics["rolling_1h"]["tx_volume"] == 500.0


# Test 3: Rolling 5-minute calculation
def test_3_rolling_5_minute_calculation():
    store = LiveFraudSpikeTelemetryStore()
    base_time = 1700000000.0

    # 3 payments within 5 minutes (within 300s of base_time)
    store.record_webhook_event(
        event_id="evt_5m_1",
        event_type="payment.captured",
        payment_id="pay_5m_1",
        amount=100.0,
        merchant_id="MERCH_5M",
        timestamp=base_time - 120,  # 2 minutes ago
    )
    store.record_webhook_event(
        event_id="evt_5m_2",
        event_type="payment.captured",
        payment_id="pay_5m_2",
        amount=250.0,
        merchant_id="MERCH_5M",
        timestamp=base_time - 60,   # 1 minute ago
    )
    store.record_webhook_event(
        event_id="evt_5m_3",
        event_type="payment.captured",
        payment_id="pay_5m_3",
        amount=150.0,
        merchant_id="MERCH_5M",
        timestamp=base_time,        # now
    )

    metrics = store.get_rolling_metrics(merchant_id="MERCH_5M", now_ts=base_time)
    assert metrics["rolling_5m"]["tx_count"] == 3
    assert metrics["rolling_5m"]["tx_volume"] == 500.0


# Test 4: Rolling 1-hour calculation
def test_4_rolling_1_hour_calculation():
    store = LiveFraudSpikeTelemetryStore()
    base_time = 1700000000.0

    # 1 payment 20 minutes ago (in 1h, but outside 5m)
    store.record_webhook_event(
        event_id="evt_1h_1",
        event_type="payment.captured",
        payment_id="pay_1h_1",
        amount=300.0,
        merchant_id="MERCH_1H",
        timestamp=base_time - 1200,  # 20 min ago
    )
    # 1 payment 2 minutes ago (in both 1h and 5m)
    store.record_webhook_event(
        event_id="evt_1h_2",
        event_type="payment.captured",
        payment_id="pay_1h_2",
        amount=200.0,
        merchant_id="MERCH_1H",
        timestamp=base_time - 120,   # 2 min ago
    )

    metrics = store.get_rolling_metrics(merchant_id="MERCH_1H", now_ts=base_time)
    assert metrics["rolling_5m"]["tx_count"] == 1
    assert metrics["rolling_5m"]["tx_volume"] == 200.0
    assert metrics["rolling_1h"]["tx_count"] == 2
    assert metrics["rolling_1h"]["tx_volume"] == 500.0


# Test 5: Event expiration from rolling windows
def test_5_event_expiration_from_rolling_windows():
    store = LiveFraudSpikeTelemetryStore()
    base_time = 1700000000.0

    # Payment 400s ago (expired from 5m window, present in 1h window)
    store.record_webhook_event(
        event_id="evt_exp_1",
        event_type="payment.captured",
        payment_id="pay_exp_1",
        amount=150.0,
        merchant_id="MERCH_EXP",
        timestamp=base_time - 400,
    )
    # Payment 3700s ago (expired from 1h window completely)
    store.record_webhook_event(
        event_id="evt_exp_2",
        event_type="payment.captured",
        payment_id="pay_exp_2",
        amount=800.0,
        merchant_id="MERCH_EXP",
        timestamp=base_time - 3700,
    )

    metrics = store.get_rolling_metrics(merchant_id="MERCH_EXP", now_ts=base_time)
    assert metrics["rolling_5m"]["tx_count"] == 0
    assert metrics["rolling_5m"]["tx_volume"] == 0.0
    assert metrics["rolling_1h"]["tx_count"] == 1
    assert metrics["rolling_1h"]["tx_volume"] == 150.0


# Test 6: Duplicate event_id rejection
def test_6_duplicate_event_id_rejection():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()

    res1 = store.record_webhook_event(
        event_id="evt_dup_999",
        event_type="payment.captured",
        payment_id="pay_orig",
        amount=100.0,
        merchant_id="MERCH_DUP",
        timestamp=now,
    )
    assert res1["accepted"] is True

    # Same event_id must be rejected
    res2 = store.record_webhook_event(
        event_id="evt_dup_999",
        event_type="payment.captured",
        payment_id="pay_orig",
        amount=100.0,
        merchant_id="MERCH_DUP",
        timestamp=now,
    )
    assert res2["accepted"] is False
    assert res2["duplicate"] is True

    metrics = store.get_rolling_metrics(merchant_id="MERCH_DUP", now_ts=now)
    assert metrics["rolling_1h"]["tx_count"] == 1
    assert metrics["total_events_processed"] == 1


# Test 7: authorized + captured counts exactly once
def test_7_authorized_plus_captured_counts_exactly_once():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()

    # 1. authorized arrives first
    res_auth = store.record_webhook_event(
        event_id="evt_auth_101",
        event_type="payment.authorized",
        payment_id="pay_lifecycle_001",
        amount=1000.0,
        status="authorized",
        merchant_id="MERCH_LIFE",
        timestamp=now,
    )
    assert res_auth["accepted"] is True
    assert res_auth["counted_velocity"] is False

    # Velocity must be 0 after authorized
    metrics1 = store.get_rolling_metrics(merchant_id="MERCH_LIFE", now_ts=now)
    assert metrics1["rolling_1h"]["tx_count"] == 0
    assert metrics1["rolling_1h"]["tx_volume"] == 0.0

    # 2. captured arrives
    res_cap = store.record_webhook_event(
        event_id="evt_cap_101",
        event_type="payment.captured",
        payment_id="pay_lifecycle_001",
        amount=1000.0,
        status="captured",
        merchant_id="MERCH_LIFE",
        timestamp=now + 1,
    )
    assert res_cap["accepted"] is True
    assert res_cap["counted_velocity"] is True

    # Velocity must be exactly 1 after captured
    metrics2 = store.get_rolling_metrics(merchant_id="MERCH_LIFE", now_ts=now + 1)
    assert metrics2["rolling_1h"]["tx_count"] == 1
    assert metrics2["rolling_1h"]["tx_volume"] == 1000.0


# Test 8: Duplicate captured rejection
def test_8_duplicate_captured_rejection():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()

    # First captured event
    store.record_webhook_event(
        event_id="evt_first_cap",
        event_type="payment.captured",
        payment_id="pay_canonical_dup",
        amount=450.0,
        status="captured",
        merchant_id="MERCH_DUP_CAP",
        timestamp=now,
    )

    # Replayed second captured event with distinct event_id
    res_second = store.record_webhook_event(
        event_id="evt_second_cap",
        event_type="payment.captured",
        payment_id="pay_canonical_dup",
        amount=450.0,
        status="captured",
        merchant_id="MERCH_DUP_CAP",
        timestamp=now + 2,
    )
    assert res_second["accepted"] is True
    assert res_second["counted_velocity"] is False

    metrics = store.get_rolling_metrics(merchant_id="MERCH_DUP_CAP", now_ts=now + 2)
    assert metrics["rolling_1h"]["tx_count"] == 1
    assert metrics["rolling_1h"]["tx_volume"] == 450.0


# Test 9: Failed payment increments failed_payment_count
def test_9_failed_payment_increments_failed_payment_count():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()

    res = store.record_webhook_event(
        event_id="evt_fail_1",
        event_type="payment.failed",
        payment_id="pay_failed_1",
        amount=75.0,
        status="failed",
        merchant_id="MERCH_FAIL",
        timestamp=now,
    )
    assert res["accepted"] is True
    assert res["counted_failure"] is True
    assert res["counted_velocity"] is False

    metrics = store.get_rolling_metrics(merchant_id="MERCH_FAIL", now_ts=now)
    assert metrics["rolling_5m"]["failed_count"] == 1
    assert metrics["rolling_1h"]["failed_count"] == 1
    assert metrics["rolling_1h"]["tx_count"] == 0


# Test 10: Failed payment does NOT increment fraud_count
def test_10_failed_payment_does_not_increment_fraud_count():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()

    # Ingest 5 failed payments without explicit fraud notes
    for i in range(5):
        store.record_webhook_event(
            event_id=f"evt_fail_no_fraud_{i}",
            event_type="payment.failed",
            payment_id=f"pay_fail_no_fraud_{i}",
            amount=100.0,
            status="failed",
            merchant_id="MERCH_FAIL_SAFE",
            timestamp=now + i,
        )

    metrics = store.get_rolling_metrics(merchant_id="MERCH_FAIL_SAFE", now_ts=now + 10)
    assert metrics["rolling_1h"]["failed_count"] == 5
    # MANDATORY CONSTRAINT: failed payments must NOT be equated with fraud
    assert metrics["rolling_1h"]["fraud_count"] == 0
    assert metrics["rolling_1h"]["fraud_rate"] == 0.0


# Test 11: Explicit notes.is_fraud=True increments fraud_count
def test_11_explicit_notes_is_fraud_increments_fraud_count():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()

    store.record_webhook_event(
        event_id="evt_fraud_note_1",
        event_type="payment.captured",
        payment_id="pay_fraud_1",
        amount=250.0,
        status="captured",
        merchant_id="MERCH_FRAUD_NOTE",
        notes={"is_fraud": True},
        timestamp=now,
    )

    metrics = store.get_rolling_metrics(merchant_id="MERCH_FRAUD_NOTE", now_ts=now)
    assert metrics["rolling_1h"]["tx_count"] == 1
    assert metrics["rolling_1h"]["fraud_count"] == 1
    assert metrics["rolling_1h"]["fraud_rate"] == 1.0


# Test 12: Duplicate explicit fraud event does not double-count
def test_12_duplicate_explicit_fraud_event_does_not_double_count():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()

    store.record_webhook_event(
        event_id="evt_fraud_dup_1",
        event_type="payment.captured",
        payment_id="pay_fraud_dup",
        amount=300.0,
        status="captured",
        merchant_id="MERCH_FRAUD_DUP",
        notes={"fraud": True},
        timestamp=now,
    )
    # Another event for same payment_id with fraud note
    store.record_webhook_event(
        event_id="evt_fraud_dup_2",
        event_type="payment.captured",
        payment_id="pay_fraud_dup",
        amount=300.0,
        status="captured",
        merchant_id="MERCH_FRAUD_DUP",
        notes={"fraud": True},
        timestamp=now + 1,
    )

    metrics = store.get_rolling_metrics(merchant_id="MERCH_FRAUD_DUP", now_ts=now + 2)
    assert metrics["rolling_1h"]["fraud_count"] == 1


# Test 13: Chronological 5-minute buckets
def test_13_chronological_5_minute_buckets():
    store = LiveFraudSpikeTelemetryStore()
    base_time = 1700003600.0  # Exactly on an hour boundary

    # Add transactions across two distinct 5-minute intervals
    store.record_webhook_event(
        event_id="evt_bucket_1",
        event_type="payment.captured",
        payment_id="pay_b1",
        amount=100.0,
        merchant_id="MERCH_BUCKETS",
        timestamp=base_time - 600,  # 10 min ago
    )
    store.record_webhook_event(
        event_id="evt_bucket_2",
        event_type="payment.captured",
        payment_id="pay_b2",
        amount=200.0,
        merchant_id="MERCH_BUCKETS",
        timestamp=base_time - 60,   # 1 min ago
    )

    metrics = store.get_rolling_metrics(merchant_id="MERCH_BUCKETS", now_ts=base_time)
    buckets = metrics["five_minute_observations"]

    assert len(buckets) == 12  # exactly 12 5-minute intervals
    total_bucketed_tx = sum(b["tx_count"] for b in buckets)
    assert total_bucketed_tx == 2

    # Latest bucket should have the 1 min ago transaction
    assert buckets[-1]["tx_count"] == 1


# Test 14: Bounded memory behavior
def test_14_bounded_memory_behavior():
    store = LiveFraudSpikeTelemetryStore(max_events_per_merchant=50)
    now = time.time()

    # Ingest 100 events into a store with capacity 50
    for i in range(100):
        store.record_webhook_event(
            event_id=f"evt_bounded_{i}",
            event_type="payment.captured",
            payment_id=f"pay_bounded_{i}",
            amount=10.0,
            merchant_id="MERCH_BOUNDED",
            timestamp=now + i,
        )

    state = store._merchants["MERCH_BOUNDED"]
    assert len(state["completed_txs"]) <= 50


# Test 15: reset()
def test_15_reset_clears_store():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()

    store.record_webhook_event(
        event_id="evt_reset_1",
        event_type="payment.captured",
        payment_id="pay_reset_1",
        amount=50.0,
        merchant_id="MERCH_RESET",
        timestamp=now,
    )
    assert store.get_rolling_metrics(merchant_id="MERCH_RESET", now_ts=now)["rolling_1h"]["tx_count"] == 1

    store.reset()
    assert store.get_rolling_metrics(merchant_id="MERCH_RESET", now_ts=now)["rolling_1h"]["tx_count"] == 0
    assert len(store._seen_event_ids) == 0


# Test 16: export_fraud_spike_request()
def test_16_export_fraud_spike_request():
    store = LiveFraudSpikeTelemetryStore()
    now = time.time()

    store.record_webhook_event(
        event_id="evt_exp_req_1",
        event_type="payment.captured",
        payment_id="pay_exp_req_1",
        amount=200.0,
        merchant_id="MERCH_EXP_REQ",
        notes={"device_id": "DEV_TEST_01"},
        timestamp=now,
    )

    req = store.export_fraud_spike_request(merchant_id="MERCH_EXP_REQ")
    assert req["merchant_id"] == "MERCH_EXP_REQ"
    assert req["baseline_window"] == "previous_24h"
    assert req["current_window"] == "latest_1h"
    assert req["current_tx_count"] == 1
    assert req["current_device_count"] == 1
    assert isinstance(req["five_minute_telemetry"], list)
    assert len(req["five_minute_telemetry"]) == 12


# Test 17: GET /risk/fraud-spike/live
def test_17_get_live_telemetry_endpoint(client):
    store = get_live_fraud_telemetry_store()
    now = time.time()

    store.record_webhook_event(
        event_id="evt_api_live_1",
        event_type="payment.captured",
        payment_id="pay_api_live_1",
        amount=350.0,
        merchant_id="MERCH_RAZORPAY_TEST",
        timestamp=now,
    )

    response = client.get("/risk/fraud-spike/live")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ACTIVE"
    assert data["merchant_id"] == "MERCH_RAZORPAY_TEST"
    assert data["total_events_processed"] >= 1
    assert data["rolling_1h"]["tx_count"] >= 1
    assert data["rolling_1h"]["tx_volume"] >= 350.0
    assert "five_minute_observations" in data
    assert "recent_events" in data


# Test 18: POST /risk/fraud-spike/live/evaluate
def test_18_post_live_evaluate_endpoint(client):
    store = get_live_fraud_telemetry_store()
    now = time.time()

    # Ingest captured payments
    for i in range(3):
        store.record_webhook_event(
            event_id=f"evt_eval_live_{i}",
            event_type="payment.captured",
            payment_id=f"pay_eval_live_{i}",
            amount=100.0,
            merchant_id="MERCH_RAZORPAY_TEST",
            timestamp=now + i,
        )

    response = client.post("/risk/fraud-spike/live/evaluate", json={})
    assert response.status_code == 200
    data = response.json()

    # Validates that existing FraudSpikeResponse contract is returned
    assert "spike_prediction" in data
    assert "spike_probability" in data
    assert "spike_score" in data
    assert "spike_level" in data
    assert "recommended_action" in data
    assert data["merchant_id"] == "MERCH_RAZORPAY_TEST"


# Test 19: Live result source is LIVE_ASSESSMENT / webhook integration
def test_19_live_result_source_lifecycle(client):
    # Verify razorpay webhook updates the live fraud telemetry store directly
    secret = get_webhook_secret() or "test_secret_ai_risk_2026"
    raw_payload = json.dumps({
        "event": "payment.captured",
        "account_id": "acc_merch_test_live",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_webhook_live_101",
                    "amount": 99900,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {"account_id": "ACC_MERCHANT_90210"},
                }
            }
        }
    }).encode("utf-8")

    sig = hmac.new(secret.encode("utf-8"), raw_payload, hashlib.sha256).hexdigest()

    resp = client.post(
        "/webhooks/razorpay",
        content=raw_payload,
        headers={
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": "evt_hook_live_999",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200

    # Verify that get_live_fraud_telemetry_store received the event
    store = get_live_fraud_telemetry_store()
    metrics = store.get_rolling_metrics(merchant_id="acc_merch_test_live")
    assert metrics["rolling_1h"]["tx_count"] == 1
    assert metrics["rolling_1h"]["tx_volume"] == 999.0


# Test 20: Manual simulation remains unaffected
def test_20_manual_simulation_remains_unaffected(client):
    store = get_live_fraud_telemetry_store()
    store.reset()

    # Manual simulation payload
    manual_payload = {
        "merchant_id": "MERCH_MANUAL_SIM",
        "baseline_window": "previous_24h",
        "current_window": "latest_1h",
        "baseline_tx_count": 2400,
        "current_tx_count": 100,
        "baseline_fraud_count": 24,
        "current_fraud_count": 1,
        "baseline_fraud_rate": 0.01,
        "current_fraud_rate": 0.01,
        "baseline_device_count": 2100,
        "current_device_count": 95,
        "baseline_suspicious_score": 0.03,
        "current_suspicious_score": 0.03,
    }

    # Execute manual simulation
    resp = client.post("/risk/fraud-spike", json=manual_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["merchant_id"] == "MERCH_MANUAL_SIM"
    assert data["spike_level"] == "LOW"

    # Verify that live telemetry was NOT altered by manual simulation
    live_metrics = store.get_rolling_metrics(merchant_id="MERCH_MANUAL_SIM")
    assert live_metrics["total_events_processed"] == 0
    assert live_metrics["rolling_1h"]["tx_count"] == 0
