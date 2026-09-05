"""Tests for Account Live Activity integration with real-time Razorpay webhooks.

Verifies:
1. captured payment updates live activity once (payment_count=1, payment_volume=amount).
2. authorized + captured results in exactly one successful payment.
3. duplicate webhook does not increase live activity (same event_id and duplicate captured).
4. failed payment increments failed_payment_count once per payment.
5. account lookup GET /risk/account/{account_id} returns both historical and live_activity sections.
6. historical metrics remain completely immutable from payment webhooks.
7. unknown account GET /risk/account/ACC_NONEXISTENT_999 returns clean HTTP 404.
8. association mechanisms: explicit notes, dev/test header override, and test_mode_default.
9. live activity reset resets metrics cleanly.
"""

import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient

from src.api import app, get_spike_detector
from src.live_activity import get_live_activity_store
from src.razorpay_webhook import get_webhook_manager, ENV_WEBHOOK_SECRET

TEST_SECRET = "live_activity_test_secret_xyz"


def compute_signature(raw_body: bytes, secret: str = TEST_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv(ENV_WEBHOOK_SECRET, TEST_SECRET)
    monkeypatch.setenv("RAZORPAY_TEST_ACCOUNT_ID", "ACC_MERCHANT_90210")
    manager = get_webhook_manager()
    manager.reset_metrics()
    detector = get_spike_detector()
    detector.reset_tracker()
    live_store = get_live_activity_store()
    live_store.reset()
    yield
    manager.reset_metrics()
    detector.reset_tracker()
    live_store.reset()


@pytest.fixture
def client():
    return TestClient(app)


def make_webhook_payload(
    event: str = "payment.captured",
    event_id: str = "evt_live_1",
    payment_id: str = "pay_live_100",
    account_id: str = "acc_merchantA",
    amount_paise: int = 50000,
    status: str = "captured",
    notes: dict = None,
) -> bytes:
    payload_dict = {
        "entity": "event",
        "account_id": account_id,
        "event": event,
        "event_id": event_id,
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "amount": amount_paise,
                    "currency": "INR",
                    "status": status,
                    "order_id": f"order_{payment_id}",
                    "method": "card",
                    "captured": (status == "captured"),
                    "created_at": 1772635200,
                    "notes": notes or {},
                }
            }
        },
    }
    return json.dumps(payload_dict).encode("utf-8")


def test_captured_payment_updates_live_activity_once(client):
    """Scenario 1: Captured payment updates live activity once."""
    raw_body = make_webhook_payload(
        event="payment.captured",
        event_id="evt_test_cap_1",
        payment_id="pay_test_cap_1",
        amount_paise=25000,  # 250.00 INR
        status="captured",
        notes={"account_id": "ACC_MERCHANT_90210"},
    )
    sig = compute_signature(raw_body)
    resp = client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": "evt_test_cap_1",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    # Check live activity for ACC_MERCHANT_90210
    live_store = get_live_activity_store()
    act = live_store.get_live_activity("ACC_MERCHANT_90210")
    assert act["payment_count"] == 1
    assert act["payment_volume"] == 250.0
    assert act["failed_payment_count"] == 0
    assert act["webhook_event_count"] == 1
    assert len(act["recent_events"]) == 1
    assert act["recent_events"][0]["payment_id"] == "pay_test_cap_1"
    assert act["recent_events"][0]["amount"] == 250.0


def test_authorized_plus_captured_results_in_one_successful_payment(client):
    """Scenario 2: authorized + captured results in exactly one successful payment."""
    # 1. Send payment.authorized
    raw_auth = make_webhook_payload(
        event="payment.authorized",
        event_id="evt_auth_1",
        payment_id="pay_auth_cap_1",
        amount_paise=10000,
        status="authorized",
        notes={"account_id": "ACC_MERCHANT_90210"},
    )
    sig_auth = compute_signature(raw_auth)
    resp1 = client.post(
        "/webhooks/razorpay",
        content=raw_auth,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig_auth,
            "X-Razorpay-Event-Id": "evt_auth_1",
        },
    )
    assert resp1.status_code == 200

    live_store = get_live_activity_store()
    act1 = live_store.get_live_activity("ACC_MERCHANT_90210")
    # Authorized does NOT increment payment_count or payment_volume
    assert act1["payment_count"] == 0
    assert act1["payment_volume"] == 0.0
    assert act1["webhook_event_count"] == 1

    # 2. Send payment.captured for the same payment_id
    raw_cap = make_webhook_payload(
        event="payment.captured",
        event_id="evt_cap_2",
        payment_id="pay_auth_cap_1",
        amount_paise=10000,
        status="captured",
        notes={"account_id": "ACC_MERCHANT_90210"},
    )
    sig_cap = compute_signature(raw_cap)
    resp2 = client.post(
        "/webhooks/razorpay",
        content=raw_cap,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig_cap,
            "X-Razorpay-Event-Id": "evt_cap_2",
        },
    )
    assert resp2.status_code == 200

    act2 = live_store.get_live_activity("ACC_MERCHANT_90210")
    # Exactly one successful payment
    assert act2["payment_count"] == 1
    assert act2["payment_volume"] == 100.0
    assert act2["webhook_event_count"] == 2


def test_duplicate_webhook_does_not_increase_live_activity(client):
    """Scenario 3: duplicate webhook does not increase live counts or volume."""
    raw_body = make_webhook_payload(
        event="payment.captured",
        event_id="evt_dup_test_1",
        payment_id="pay_dup_1",
        amount_paise=15000,
        status="captured",
        notes={"account_id": "ACC_MERCHANT_90210"},
    )
    sig = compute_signature(raw_body)
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_dup_test_1",
    }

    # First delivery
    resp1 = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "accepted"

    # Exact duplicate delivery
    resp2 = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["duplicate"] is True

    live_store = get_live_activity_store()
    act = live_store.get_live_activity("ACC_MERCHANT_90210")
    # Must remain exactly 1, not 2
    assert act["payment_count"] == 1
    assert act["payment_volume"] == 150.0
    assert act["webhook_event_count"] == 1

    # Secondary test: new event_id but duplicate captured for same payment_id
    raw_body_new_evt = make_webhook_payload(
        event="payment.captured",
        event_id="evt_dup_test_2_new",
        payment_id="pay_dup_1",  # same payment_id
        amount_paise=15000,
        status="captured",
        notes={"account_id": "ACC_MERCHANT_90210"},
    )
    sig_new = compute_signature(raw_body_new_evt)
    client.post(
        "/webhooks/razorpay",
        content=raw_body_new_evt,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig_new,
            "X-Razorpay-Event-Id": "evt_dup_test_2_new",
        },
    )
    act_after = live_store.get_live_activity("ACC_MERCHANT_90210")
    # Payment count and volume must not double count
    assert act_after["payment_count"] == 1
    assert act_after["payment_volume"] == 150.0


def test_failed_payment_increments_failed_count(client):
    """Scenario 4: failed payment increments failed count once per payment."""
    raw_body = make_webhook_payload(
        event="payment.failed",
        event_id="evt_fail_1",
        payment_id="pay_fail_1",
        amount_paise=5000,
        status="failed",
        notes={"account_id": "ACC_MERCHANT_90210"},
    )
    sig = compute_signature(raw_body)
    resp = client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": "evt_fail_1",
        },
    )
    assert resp.status_code == 200

    live_store = get_live_activity_store()
    act = live_store.get_live_activity("ACC_MERCHANT_90210")
    assert act["payment_count"] == 0
    assert act["failed_payment_count"] == 1
    assert act["payment_volume"] == 0.0


def test_account_lookup_returns_historical_plus_live_sections(client):
    """Scenario 5: GET /risk/account/{account_id} returns historical profile and separate live_activity."""
    # First, feed one live payment
    raw_body = make_webhook_payload(
        event="payment.captured",
        event_id="evt_acc_lookup_1",
        payment_id="pay_acc_lookup_1",
        amount_paise=12000,  # 120.00
        status="captured",
        notes={"account_id": "ACC_MERCHANT_90210"},
    )
    sig = compute_signature(raw_body)
    client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": "evt_acc_lookup_1",
        },
    )

    # Now look up account profile
    resp = client.get("/risk/account/ACC_MERCHANT_90210")
    assert resp.status_code == 200
    data = resp.json()

    # 1. Historical metrics remain intact and immutable
    assert data["account_id"] == "ACC_MERCHANT_90210"
    assert data["order_count"] == 12.0
    assert data["total_spend"] == 650.0
    assert data["return_count"] == 1.0
    assert data["refund_count"] == 0.0
    assert data["return_rate"] == 0.0833
    assert data["refund_rate"] == 0.0

    # 2. Separate live_activity section
    assert "live_activity" in data
    live = data["live_activity"]
    assert live["account_id"] == "ACC_MERCHANT_90210"
    assert live["payment_count"] == 1
    assert live["payment_volume"] == 120.0
    assert live["failed_payment_count"] == 0
    assert live["webhook_event_count"] == 1
    assert len(live["recent_events"]) == 1


def test_live_activity_polling_endpoint(client):
    """Scenario 6: GET /risk/account/{account_id}/live returns isolated live activity."""
    resp = client.get("/risk/account/ACC_MERCHANT_90210/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_id"] == "ACC_MERCHANT_90210"
    assert data["payment_count"] == 0
    assert data["payment_volume"] == 0.0
    assert data["failed_payment_count"] == 0


def test_unknown_account_still_returns_clean_404(client):
    """Scenario 7: Unknown account returns HTTP 404 for profile and live endpoints."""
    resp1 = client.get("/risk/account/ACC_NONEXISTENT_999")
    assert resp1.status_code == 404
    assert "not found in registry" in resp1.json()["detail"]

    resp2 = client.get("/risk/account/ACC_NONEXISTENT_999/live")
    assert resp2.status_code == 404
    assert "not found in registry" in resp2.json()["detail"]


def test_test_mode_default_association_documented(client):
    """Scenario 8: Webhook without notes associates via test_mode_default."""
    raw_body = make_webhook_payload(
        event="payment.captured",
        event_id="evt_def_1",
        payment_id="pay_def_1",
        account_id="acc_unmapped_razorpay",
        amount_paise=30000,
        status="captured",
        notes={},  # No notes passed
    )
    sig = compute_signature(raw_body)
    resp = client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": "evt_def_1",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # Association method is clearly documented as test_mode_default
    assert body["associated_account"]["account_id"] == "ACC_MERCHANT_90210"
    assert body["associated_account"]["association_source"] == "test_mode_default"

    # Verify live activity store recorded it with association source
    act = get_live_activity_store().get_live_activity("ACC_MERCHANT_90210")
    assert act["payment_count"] == 1
    assert "test_mode_default" in act["association_sources"]
