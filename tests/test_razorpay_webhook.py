"""Unit and integration tests for Razorpay Test Mode webhook ingestion pipeline.

Verifies:
- Scenario A: Valid HMAC-SHA256 signature acceptance
- Scenario B: Invalid signature rejection (HTTP 400)
- Scenario C: Missing signature rejection (HTTP 400)
- Scenario D: Duplicate event ID idempotency (HTTP 200, duplicate=True, zero telemetry modification)
- Scenario E: payment.captured canonical completed-payment velocity ingestion
- Scenario F: payment.failed safe failure signal (NOT fraud, fraud_count remains 0)
- Scenario G: payment.authorized + payment.captured order independence (authorized->captured & captured->authorized)
- Scenario H: order.paid safe acknowledgment without velocity double-counting
- Scenario I: Unsupported events (e.g. refund.processed, payout.created) safe acknowledgment without telemetry
- Scenario J: Malformed JSON with valid signature (HTTP 400, no server crash or telemetry corruption)
- Scenario K: Merchant isolation (Merchant A events never contaminate Merchant B telemetry)
- Scenario L: Status endpoint (/webhooks/razorpay/status) operational health metrics without secret exposure
"""

import os
import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient

from src.api import app, get_spike_detector
from src.razorpay_webhook import (
    get_webhook_manager,
    verify_razorpay_signature,
    IdempotencyStore,
    PaymentLifecycleTracker,
    RiskPaymentEvent,
    normalize_razorpay_payload,
    ENV_WEBHOOK_SECRET,
)

TEST_SECRET = "test_razorpay_webhook_secret_xyz123"


def compute_test_signature(raw_body: bytes, secret: str = TEST_SECRET) -> str:
    """Compute HMAC-SHA256 signature directly from raw request bytes."""
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def setup_webhook_env(monkeypatch):
    """Set test webhook secret and reset manager state before every test."""
    monkeypatch.setenv(ENV_WEBHOOK_SECRET, TEST_SECRET)
    monkeypatch.setenv("RAZORPAY_DEFAULT_MERCHANT_ID", "MERCH_TEST_DEFAULT")
    manager = get_webhook_manager()
    manager.reset_metrics()
    detector = get_spike_detector()
    detector.reset_tracker()
    yield
    manager.reset_metrics()
    detector.reset_tracker()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def build_razorpay_payload(
    event: str = "payment.captured",
    payment_id: str = "pay_test123",
    account_id: str = "acc_merchantA",
    amount: int = 50000,
    status: str = "captured",
    method: str = "card",
    currency: str = "INR",
) -> bytes:
    """Generate exact raw bytes for a standard Razorpay webhook event."""
    payload_dict = {
        "entity": "event",
        "account_id": account_id,
        "event": event,
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "amount": amount,
                    "currency": currency,
                    "status": status,
                    "order_id": f"order_{payment_id}",
                    "invoice_id": None,
                    "international": False,
                    "method": method,
                    "amount_refunded": 0,
                    "refund_status": None,
                    "captured": (status == "captured"),
                    "description": "Test Transaction",
                    "email": "customer@example.com",
                    "contact": "+919876543210",
                    "error_code": None,
                    "error_description": None,
                    "created_at": 1772635200,
                }
            }
        },
        "created_at": 1772635200,
    }
    return json.dumps(payload_dict).encode("utf-8")


# --------------------------------------------------------------------------
# Scenario A: Valid Signature Acceptance
# --------------------------------------------------------------------------
def test_scenario_a_valid_signature_accepted(client):
    """Scenario A: Given a valid HMAC-SHA256 signature, webhook is accepted (200 OK)."""
    raw_body = build_razorpay_payload(event="payment.captured", payment_id="pay_valid_001")
    sig = compute_test_signature(raw_body)

    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": sig,
        "x-razorpay-event-id": "evt_valid_001",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "accepted"
    assert data["duplicate"] is False
    assert data["event_id"] == "evt_valid_001"
    assert data["event_type"] == "payment.captured"
    assert data["velocity_counted"] is True
    assert data["merchant_id"] == "acc_merchantA"
    assert "fraud_spike_assessment" in data


# --------------------------------------------------------------------------
# Scenario B: Invalid Signature Rejection
# --------------------------------------------------------------------------
def test_scenario_b_invalid_signature_rejected(client):
    """Scenario B: Invalid HMAC-SHA256 signature must be rejected with HTTP 400 and no telemetry updated."""
    raw_body = build_razorpay_payload(event="payment.captured", payment_id="pay_invalid_001")
    invalid_sig = "bad_signature_deadbeef1234567890"

    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": invalid_sig,
        "x-razorpay-event-id": "evt_invalid_001",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "rejected"
    assert "Invalid webhook signature" in data["error"]

    # Verify no telemetry recorded
    detector = get_spike_detector()
    obs = detector.telemetry_store.get_observations("acc_merchantA")
    assert len(obs) == 0


# --------------------------------------------------------------------------
# Scenario C: Missing Signature Rejection
# --------------------------------------------------------------------------
def test_scenario_c_missing_signature_rejected(client):
    """Scenario C: Request without X-Razorpay-Signature header must be rejected with HTTP 400."""
    raw_body = build_razorpay_payload(event="payment.captured", payment_id="pay_missing_sig")

    headers = {
        "Content-Type": "application/json",
        "x-razorpay-event-id": "evt_missing_sig",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "rejected"
    assert "Missing X-Razorpay-Signature header" in data["error"]


# --------------------------------------------------------------------------
# Scenario D: Duplicate Event ID Idempotency
# --------------------------------------------------------------------------
def test_scenario_d_duplicate_event_id_idempotent(client):
    """Scenario D: Repeated event with identical x-razorpay-event-id returns HTTP 200 with duplicate=true."""
    raw_body = build_razorpay_payload(event="payment.captured", payment_id="pay_dup_001")
    sig = compute_test_signature(raw_body)
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": sig,
        "x-razorpay-event-id": "evt_dup_test_id",
    }

    # 1. First attempt: Accepted
    res1 = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "accepted"
    assert res1.json()["duplicate"] is False

    detector = get_spike_detector()
    obs_after_first = detector.telemetry_store.get_observations("acc_merchantA")
    assert len(obs_after_first) == 1
    tx_count_first = obs_after_first[0]["tx_count"]
    assert tx_count_first == 1

    # 2. Second attempt: Duplicate detected
    res2 = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "duplicate"
    assert data2["duplicate"] is True
    assert data2["event_id"] == "evt_dup_test_id"

    # Telemetry should NOT be incremented
    obs_after_second = detector.telemetry_store.get_observations("acc_merchantA")
    assert len(obs_after_second) == 1
    assert obs_after_second[0]["tx_count"] == tx_count_first


# --------------------------------------------------------------------------
# Scenario E: payment.captured Canonical Ingestion
# --------------------------------------------------------------------------
def test_scenario_e_payment_captured_velocity_ingestion(client):
    """Scenario E: payment.captured is normalized and enters FiveMinuteTelemetryStore."""
    raw_body = build_razorpay_payload(
        event="payment.captured",
        payment_id="pay_cap_999",
        account_id="acc_merchant_retail",
        amount=12500,  # 125.00 INR
    )
    sig = compute_test_signature(raw_body)
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": sig,
        "x-razorpay-event-id": "evt_cap_999",
    }

    res = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["velocity_counted"] is True
    assert data["normalized_event"]["amount"] == 125.0
    assert data["normalized_event"]["currency"] == "INR"
    assert data["normalized_event"]["success"] is True
    assert data["normalized_event"]["source"] == "razorpay_test"

    # Check store
    detector = get_spike_detector()
    obs = detector.telemetry_store.get_observations("acc_merchant_retail")
    assert len(obs) == 1
    assert obs[0]["tx_count"] == 1
    assert obs[0]["fraud_count"] == 0


# --------------------------------------------------------------------------
# Scenario F: payment.failed is NOT Fraud
# --------------------------------------------------------------------------
def test_scenario_f_payment_failed_is_not_fraud(client):
    """Scenario F: payment.failed is a payment signal, NOT fraud. fraud_count remains 0."""
    raw_body = build_razorpay_payload(
        event="payment.failed",
        payment_id="pay_fail_001",
        account_id="acc_merchant_fail_test",
        status="failed",
    )
    sig = compute_test_signature(raw_body)
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": sig,
        "x-razorpay-event-id": "evt_fail_001",
    }

    res = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "accepted"
    assert data["normalized_event"]["payment_status"] == "failed"
    assert data["normalized_event"]["success"] is False

    # Velocity not counted for failed payment, and fraud_count must remain 0
    detector = get_spike_detector()
    obs = detector.telemetry_store.get_observations("acc_merchant_fail_test")
    # No completed-payment velocity added
    for o in obs:
        assert o.get("fraud_count", 0) == 0


# --------------------------------------------------------------------------
# Scenario G: payment.authorized + payment.captured Order Independence
# --------------------------------------------------------------------------
def test_scenario_g_authorized_then_captured_counts_once(client):
    """Case A: payment.authorized -> payment.captured counts exactly 1 completed payment."""
    payment_id = "pay_order_case_a"
    account_id = "acc_merchant_order_a"

    # 1. authorized arrives
    raw_auth = build_razorpay_payload(
        event="payment.authorized",
        payment_id=payment_id,
        account_id=account_id,
        status="authorized",
    )
    res_auth = client.post(
        "/webhooks/razorpay",
        content=raw_auth,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": compute_test_signature(raw_auth),
            "x-razorpay-event-id": "evt_order_a_auth",
        },
    )
    assert res_auth.status_code == 200
    assert res_auth.json()["velocity_counted"] is False  # Authorized does not count as completed

    # 2. captured arrives
    raw_cap = build_razorpay_payload(
        event="payment.captured",
        payment_id=payment_id,
        account_id=account_id,
        status="captured",
    )
    res_cap = client.post(
        "/webhooks/razorpay",
        content=raw_cap,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": compute_test_signature(raw_cap),
            "x-razorpay-event-id": "evt_order_a_cap",
        },
    )
    assert res_cap.status_code == 200
    assert res_cap.json()["velocity_counted"] is True  # Exactly once

    detector = get_spike_detector()
    obs = detector.telemetry_store.get_observations(account_id)
    assert len(obs) == 1
    assert obs[0]["tx_count"] == 1


def test_scenario_g_captured_then_authorized_counts_once(client):
    """Case B: payment.captured -> payment.authorized counts exactly 1 completed payment."""
    payment_id = "pay_order_case_b"
    account_id = "acc_merchant_order_b"

    # 1. captured arrives first
    raw_cap = build_razorpay_payload(
        event="payment.captured",
        payment_id=payment_id,
        account_id=account_id,
        status="captured",
    )
    res_cap = client.post(
        "/webhooks/razorpay",
        content=raw_cap,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": compute_test_signature(raw_cap),
            "x-razorpay-event-id": "evt_order_b_cap",
        },
    )
    assert res_cap.status_code == 200
    assert res_cap.json()["velocity_counted"] is True

    # 2. authorized arrives afterwards
    raw_auth = build_razorpay_payload(
        event="payment.authorized",
        payment_id=payment_id,
        account_id=account_id,
        status="authorized",
    )
    res_auth = client.post(
        "/webhooks/razorpay",
        content=raw_auth,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": compute_test_signature(raw_auth),
            "x-razorpay-event-id": "evt_order_b_auth",
        },
    )
    assert res_auth.status_code == 200
    assert res_auth.json()["velocity_counted"] is False  # Must not double-count

    detector = get_spike_detector()
    obs = detector.telemetry_store.get_observations(account_id)
    assert len(obs) == 1
    assert obs[0]["tx_count"] == 1


# --------------------------------------------------------------------------
# Scenario H: order.paid Safe Acknowledgment
# --------------------------------------------------------------------------
def test_scenario_h_order_paid_safely_ignored(client):
    """Scenario H: order.paid is safely acknowledged and not counted for velocity."""
    raw_body = json.dumps({
        "entity": "event",
        "account_id": "acc_merchant_order_paid",
        "event": "order.paid",
        "payload": {"order": {"entity": {"id": "order_123", "amount_paid": 50000}}},
    }).encode("utf-8")
    sig = compute_test_signature(raw_body)

    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": sig,
        "x-razorpay-event-id": "evt_order_paid_01",
    }

    res = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ignored"
    assert data["event_type"] == "order.paid"

    # Velocity not modified
    detector = get_spike_detector()
    assert len(detector.telemetry_store.get_observations("acc_merchant_order_paid")) == 0


# --------------------------------------------------------------------------
# Scenario I: Unsupported Event Handling
# --------------------------------------------------------------------------
def test_scenario_i_unsupported_event_acknowledged_safely(client):
    """Scenario I: Unsupported events (e.g. refund.processed) acknowledged safely (200 OK) without error."""
    raw_body = json.dumps({
        "entity": "event",
        "account_id": "acc_merchant_refund",
        "event": "refund.processed",
        "payload": {"refund": {"entity": {"id": "rfnd_123"}}},
    }).encode("utf-8")
    sig = compute_test_signature(raw_body)

    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": sig,
        "x-razorpay-event-id": "evt_refund_proc_01",
    }

    res = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ignored"
    assert data["event_type"] == "refund.processed"


# --------------------------------------------------------------------------
# Scenario J: Malformed JSON with Valid Signature
# --------------------------------------------------------------------------
def test_scenario_j_malformed_json_rejected_safely(client):
    """Scenario J: Malformed JSON with valid signature returns HTTP 400 without crashing."""
    raw_body = b"NOT_VALID_JSON{:::broken"
    sig = compute_test_signature(raw_body)

    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": sig,
        "x-razorpay-event-id": "evt_broken_json",
    }

    res = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert res.status_code == 400
    data = res.json()
    assert data["status"] == "rejected"
    assert "Malformed JSON payload" in data["error"]


# --------------------------------------------------------------------------
# Scenario K: Merchant Isolation
# --------------------------------------------------------------------------
def test_scenario_k_merchant_isolation(client):
    """Scenario K: Events from Merchant A never affect Merchant B telemetry."""
    # Merchant A event
    raw_a = build_razorpay_payload(event="payment.captured", payment_id="pay_a_1", account_id="MERCH_ISOLATED_A")
    res_a = client.post(
        "/webhooks/razorpay",
        content=raw_a,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": compute_test_signature(raw_a),
            "x-razorpay-event-id": "evt_iso_a_1",
        },
    )
    assert res_a.status_code == 200

    # Merchant B event
    raw_b = build_razorpay_payload(event="payment.captured", payment_id="pay_b_1", account_id="MERCH_ISOLATED_B")
    res_b = client.post(
        "/webhooks/razorpay",
        content=raw_b,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": compute_test_signature(raw_b),
            "x-razorpay-event-id": "evt_iso_b_1",
        },
    )
    assert res_b.status_code == 200

    detector = get_spike_detector()
    obs_a = detector.telemetry_store.get_observations("MERCH_ISOLATED_A")
    obs_b = detector.telemetry_store.get_observations("MERCH_ISOLATED_B")

    assert len(obs_a) == 1
    assert len(obs_b) == 1
    assert obs_a[0]["tx_count"] == 1
    assert obs_b[0]["tx_count"] == 1

    # Add second event to Merchant A only
    raw_a2 = build_razorpay_payload(event="payment.captured", payment_id="pay_a_2", account_id="MERCH_ISOLATED_A")
    client.post(
        "/webhooks/razorpay",
        content=raw_a2,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": compute_test_signature(raw_a2),
            "x-razorpay-event-id": "evt_iso_a_2",
        },
    )

    obs_a_updated = detector.telemetry_store.get_observations("MERCH_ISOLATED_A")
    obs_b_updated = detector.telemetry_store.get_observations("MERCH_ISOLATED_B")

    assert obs_a_updated[0]["tx_count"] == 2
    assert obs_b_updated[0]["tx_count"] == 1  # Merchant B remains untouched


# --------------------------------------------------------------------------
# Scenario L: Status Endpoint and Risk Event Output
# --------------------------------------------------------------------------
def test_scenario_l_status_endpoint_metrics(client):
    """Scenario L: /webhooks/razorpay/status returns accurate metrics without exposing secrets."""
    raw_body = build_razorpay_payload(event="payment.captured", payment_id="pay_stat_1", account_id="MERCH_STATUS_TEST")
    sig = compute_test_signature(raw_body)
    client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": "evt_stat_1",
        },
    )

    res = client.get("/webhooks/razorpay/status")
    assert res.status_code == 200
    status_data = res.json()

    assert status_data["enabled"] is True
    assert status_data["environment"] == "test"
    assert status_data["received"] >= 1
    assert status_data["accepted"] >= 1
    assert status_data["latest_event_type"] == "payment.captured"
    assert status_data["latest_merchant_id"] == "MERCH_STATUS_TEST"

    # Assert no secrets in output
    for key in ["key_secret", "webhook_secret", "secret", "password"]:
        assert key not in status_data

    # Check recent events endpoint
    res_events = client.get("/webhooks/razorpay/events")
    assert res_events.status_code == 200
    events_list = res_events.json()
    assert len(events_list) >= 1
    first_evt = events_list[0]
    assert first_evt["engine"] == "FRAUD_SPIKE"
    assert first_evt["source"] == "LIVE_ASSESSMENT"
    assert first_evt["entityType"] == "MERCHANT"


# --------------------------------------------------------------------------
# Idempotency and Lifecycle Unit Tests
# --------------------------------------------------------------------------
def test_idempotency_store_capacity_eviction():
    """Verify bounded memory behavior of IdempotencyStore under capacity pressure."""
    store = IdempotencyStore(capacity=3)
    assert store.record_event("evt_1") is True
    assert store.record_event("evt_2") is True
    assert store.record_event("evt_3") is True
    assert store.get_size() == 3

    # Adding 4th evicts oldest (evt_1)
    assert store.record_event("evt_4") is True
    assert store.get_size() == 3
    assert store.is_duplicate("evt_1") is False
    assert store.is_duplicate("evt_4") is True


def test_payment_lifecycle_tracker_idempotency():
    """Verify payment lifecycle tracker prevents double counting on duplicated captured events."""
    tracker = PaymentLifecycleTracker(capacity=10)
    should_count1, is_dup1 = tracker.record_payment_event("pay_abc", "payment.captured")
    assert should_count1 is True
    assert is_dup1 is False

    # Second captured event for same payment_id
    should_count2, is_dup2 = tracker.record_payment_event("pay_abc", "payment.captured")
    assert should_count2 is False
    assert is_dup2 is True
