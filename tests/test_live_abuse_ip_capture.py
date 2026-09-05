"""Comprehensive tests for Automatic Real Client IP Capture & Payment Correlation.

Verifies all 20 prompt-specified scenarios:
1. automatic IP extraction from a direct trusted application request
2. missing IP
3. malformed IP
4. IPv4 normalization
5. IPv6 normalization
6. untrusted X-Forwarded-For is ignored
7. trusted proxy IP extraction if explicitly configured
8. payment context creation
9. payment context correlation
10. expired payment context
11. authorized -> captured correlation
12. duplicate captured
13. failed payment correlation
14. IP hash determinism
15. raw IP never exposed to Live Abuse Graph UI response
16. same IP across two accounts creates one shared IP entity
17. same account does not duplicate IP edges
18. PAYMENT entity does not bridge accounts
19. existing device_id behavior remains unchanged
20. existing bystander protection remains unchanged
"""

import json
import time
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

from src.api import app, get_abuse_ring_sentinel
from src.payment_context import (
    normalize_ip,
    canonicalize_ip,
    extract_client_ip,
    get_payment_context_store,
    PaymentContextStore,
)
from src.live_abuse_graph import get_live_abuse_graph_store
from src.razorpay_webhook import get_webhook_manager, ENV_WEBHOOK_SECRET

TEST_SECRET = "test_live_graph_secret_998877"


def compute_signature(raw_body: bytes, secret: str = TEST_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def build_webhook_body(
    event: str = "payment.captured",
    payment_id: str = "pay_test_ip_001",
    amount: int = 5000,
    status: str = "captured",
    order_id: str = "order_test_ip_001",
    notes: dict = None,
) -> bytes:
    payload = {
        "entity": "event",
        "event": event,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "amount": amount,
                    "currency": "INR",
                    "status": status,
                    "order_id": order_id,
                    "method": "card",
                    "notes": notes or {},
                    "created_at": int(time.time()),
                }
            }
        },
    }
    return json.dumps(payload).encode("utf-8")


@pytest.fixture(autouse=True)
def setup_and_teardown(monkeypatch):
    """Ensure clean state before and after each test."""
    monkeypatch.setenv(ENV_WEBHOOK_SECRET, TEST_SECRET)
    monkeypatch.setenv("RAZORPAY_DEFAULT_MERCHANT_ID", "MERCH_TEST")
    manager = get_webhook_manager()
    manager.reset_metrics()
    graph_store = get_live_abuse_graph_store()
    graph_store.reset()
    ctx_store = get_payment_context_store()
    ctx_store.reset()
    yield
    manager.reset_metrics()
    graph_store.reset()
    ctx_store.reset()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# 1. Automatic IP extraction from a direct trusted application request
def test_1_automatic_ip_extraction_from_direct_application_request(client):
    """Scenario 1: Extract IP from direct trusted application request."""
    ip = extract_client_ip("192.168.1.50")
    assert ip == "192.168.1.50"

    # Direct client request to checkout endpoint
    resp = client.post(
        "/payments/create-order",
        json={"account_id": "ACC_TEST_01", "amount": 10000},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_id"] == "ACC_TEST_01"
    assert data["ip_captured"] is True

    # Check store has connection host (TestClient defaults to testclient/127.0.0.1)
    ctx_store = get_payment_context_store()
    ctx = ctx_store.get_context(data["order_id"])
    assert ctx is not None
    assert ctx["observed_ip"] in ("testclient", "127.0.0.1", "localhost")


# 2. Missing IP
def test_2_missing_ip():
    """Scenario 2: Missing IP returns None safely."""
    assert extract_client_ip(None) is None
    assert extract_client_ip("") is None
    assert extract_client_ip("   ") is None


# 3. Malformed IP
def test_3_malformed_ip():
    """Scenario 3: Malformed IP strings are rejected safely without crashing."""
    assert extract_client_ip("not-an-ip") is None
    assert extract_client_ip("999.999.999.999") is None
    assert extract_client_ip("192.168.1.300") is None
    assert extract_client_ip("::gggg") is None
    assert normalize_ip("123.456.78.90") is None


# 4. IPv4 Normalization
def test_4_ipv4_normalization():
    """Scenario 4: IPv4 normalization handles whitespace and IPv4-mapped IPv6."""
    assert normalize_ip(" 192.168.1.1 ") == "192.168.1.1"
    # IPv4-mapped IPv6 (::ffff:192.0.2.1) -> 192.0.2.1
    assert normalize_ip("::ffff:192.0.2.1") == "192.0.2.1"


# 5. IPv6 Normalization
def test_5_ipv6_normalization():
    """Scenario 5: IPv6 normalization compresses according to RFC 5952."""
    raw = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    normalized = normalize_ip(raw)
    assert normalized == "2001:db8:85a3::8a2e:370:7334"


# 6. Untrusted X-Forwarded-For is ignored
def test_6_untrusted_x_forwarded_for_is_ignored():
    """Scenario 6: Untrusted X-Forwarded-For is ignored when no trusted proxy is configured."""
    headers = {"X-Forwarded-For": "203.0.113.195", "X-Real-IP": "203.0.113.200"}
    ip = extract_client_ip("127.0.0.1", headers=headers, trusted_proxies=[])
    # Must use connection peer 127.0.0.1, NOT the spoofed headers
    assert ip == "127.0.0.1"


# 7. Trusted proxy IP extraction if explicitly configured
def test_7_trusted_proxy_ip_extraction_if_explicitly_configured():
    """Scenario 7: When peer is in trusted proxy list, rightmost untrusted XFF hop is extracted."""
    trusted = ["10.0.0.1", "172.16.0.0/12"]
    # Peer is 10.0.0.1 (trusted proxy). XFF has: real_client, intermediate_proxy, terminating_proxy
    headers = {"X-Forwarded-For": "198.51.100.42, 172.16.0.99"}
    ip = extract_client_ip("10.0.0.1", headers=headers, trusted_proxies=trusted)
    assert ip == "198.51.100.42"

    # If peer is NOT in trusted list, XFF is ignored even if trusted list exists
    ip_untrusted_peer = extract_client_ip("192.168.1.10", headers=headers, trusted_proxies=trusted)
    assert ip_untrusted_peer == "192.168.1.10"


# 8. Payment context creation
def test_8_payment_context_creation():
    """Scenario 8: Context is recorded with TTL and retrievable by order_id and correlation_id."""
    ctx_store = get_payment_context_store()
    entry = ctx_store.record_context(
        correlation_id="corr_test_08",
        account_id="ACC_08",
        observed_ip="198.51.100.8",
        device_id="DEV_TEST_08",
        order_id="order_test_08",
        ttl_seconds=1800,
    )
    assert entry["account_id"] == "ACC_08"
    assert entry["observed_ip"] == "198.51.100.8"

    # Retrievable by both correlation_id and order_id
    assert ctx_store.get_context("corr_test_08") is not None
    assert ctx_store.get_context("order_test_08") is not None


# 9. Payment context correlation
def test_9_payment_context_correlation(client):
    """Scenario 9: Razorpay webhook correlates with payment context via order_id and extracts IP."""
    ctx_store = get_payment_context_store()
    order_id = "order_corr_test_09"
    ctx_store.record_context(
        correlation_id="corr_09",
        account_id="ACC_CORR_09",
        observed_ip="203.0.113.99",
        device_id="DEV_CORR_09",
        order_id=order_id,
    )

    body = build_webhook_body(
        payment_id="pay_corr_09",
        order_id=order_id,
        notes={"account_id": "ACC_CORR_09"},  # No IP in notes
    )
    sig = compute_signature(body)
    resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    assert resp.status_code == 200

    # Live abuse graph must have observed the IP via context
    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_CORR_09")
    assert subgraph is not None
    ip_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "IP"]
    assert len(ip_edges) == 1
    assert ip_edges[0]["entity_id"] == canonicalize_ip("203.0.113.99")


# 10. Expired payment context
def test_10_expired_payment_context(client):
    """Scenario 10: Expired payment context is not used."""
    ctx_store = get_payment_context_store()
    order_id = "order_expired_10"
    # Create with negative TTL to simulate expiration
    ctx_store.record_context(
        correlation_id="corr_10",
        account_id="ACC_EXP_10",
        observed_ip="203.0.113.10",
        order_id=order_id,
        ttl_seconds=-1,
    )

    assert ctx_store.get_context(order_id) is None

    body = build_webhook_body(payment_id="pay_exp_10", order_id=order_id, notes={"account_id": "ACC_EXP_10"})
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": compute_signature(body)})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_EXP_10")
    # No IP edge because context expired and no notes IP provided
    assert len([e for e in subgraph["direct_edges"] if e["entity_type"] == "IP"]) == 0


# 11. Authorized -> captured correlation
def test_11_authorized_then_captured_correlation(client):
    """Scenario 11: authorized + captured for correlated order produces one canonical IP edge with count 1."""
    ctx_store = get_payment_context_store()
    order_id = "order_lifecycle_11"
    ctx_store.record_context(
        correlation_id="corr_11",
        account_id="ACC_LC_11",
        observed_ip="198.51.100.11",
        order_id=order_id,
    )

    pay_id = "pay_lc_11"
    body_auth = build_webhook_body(event="payment.authorized", payment_id=pay_id, status="authorized", order_id=order_id, notes={"account_id": "ACC_LC_11"})
    body_cap = build_webhook_body(event="payment.captured", payment_id=pay_id, status="captured", order_id=order_id, notes={"account_id": "ACC_LC_11"})

    client.post("/webhooks/razorpay", content=body_auth, headers={"X-Razorpay-Signature": compute_signature(body_auth)})
    client.post("/webhooks/razorpay", content=body_cap, headers={"X-Razorpay-Signature": compute_signature(body_cap)})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_LC_11")
    ip_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "IP"]
    assert len(ip_edges) == 1
    assert ip_edges[0]["interaction_count"] == 1


# 12. Duplicate captured
def test_12_duplicate_captured(client):
    """Scenario 12: Duplicate captured webhook delivery drops duplicate without duplicating IP edge."""
    ctx_store = get_payment_context_store()
    order_id = "order_dup_12"
    ctx_store.record_context(
        correlation_id="corr_12",
        account_id="ACC_DUP_12",
        observed_ip="198.51.100.12",
        order_id=order_id,
    )

    body = build_webhook_body(payment_id="pay_dup_12", order_id=order_id, notes={"account_id": "ACC_DUP_12"})
    sig = compute_signature(body)

    # First delivery
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_dup_12_a"})
    # Duplicate delivery
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_dup_12_b"})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_DUP_12")
    ip_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "IP"]
    assert len(ip_edges) == 1
    assert ip_edges[0]["interaction_count"] == 1


# 13. Failed payment correlation
def test_13_failed_payment_correlation(client):
    """Scenario 13: Failed payment correlates context and records failure without marking captured."""
    ctx_store = get_payment_context_store()
    order_id = "order_fail_13"
    ctx_store.record_context(
        correlation_id="corr_13",
        account_id="ACC_FAIL_13",
        observed_ip="198.51.100.13",
        order_id=order_id,
    )

    body = build_webhook_body(
        event="payment.failed",
        payment_id="pay_fail_13",
        status="failed",
        order_id=order_id,
        notes={"account_id": "ACC_FAIL_13"},
    )
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": compute_signature(body)})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_FAIL_13")
    pay_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "PAYMENT"]
    assert len(pay_edges) == 1
    assert pay_edges[0]["payment_status"] == "failed"


# 14. IP hash determinism
def test_14_ip_hash_determinism():
    """Scenario 14: Canonical IP hash is deterministic and idempotent across representations."""
    h1 = canonicalize_ip("203.0.113.50")
    h2 = canonicalize_ip(" 203.0.113.50 ")
    assert h1 == h2
    assert h1.startswith("IP_HASH_")
    assert len(h1) == 20

    # IPv4-mapped IPv6 produces identical hash to raw IPv4
    assert canonicalize_ip("::ffff:203.0.113.50") == h1

    # Idempotent re-hashing
    assert canonicalize_ip(h1) == h1


# 15. Raw IP never exposed to Live Abuse Graph UI response
def test_15_raw_ip_never_exposed_to_live_abuse_graph_ui_response(client):
    """Scenario 15: Raw IP is hashed to IP_HASH_<sha256[:12]> and never exposed in JSON responses."""
    raw_ip = "198.51.100.15"
    ctx_store = get_payment_context_store()
    order_id = "order_priv_15"
    ctx_store.record_context(
        correlation_id="corr_15",
        account_id="ACC_PRIV_15",
        observed_ip=raw_ip,
        order_id=order_id,
    )

    body = build_webhook_body(payment_id="pay_priv_15", order_id=order_id, notes={"account_id": "ACC_PRIV_15"})
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": compute_signature(body)})

    # Query state
    resp = client.get("/risk/abuse-ring/live")
    assert resp.status_code == 200
    raw_text = resp.text
    assert raw_ip not in raw_text
    assert canonicalize_ip(raw_ip) in raw_text

    # Query account subgraph
    resp_acc = client.get("/risk/abuse-ring/live/ACC_PRIV_15")
    assert resp_acc.status_code == 200
    assert raw_ip not in resp_acc.text
    assert canonicalize_ip(raw_ip) in resp_acc.text


# 16. Same IP across two accounts creates one shared IP entity
def test_16_same_ip_across_two_accounts_creates_one_shared_ip_entity(client):
    """Scenario 16: Two accounts sharing the same observed IP produce 1 shared IP entity."""
    shared_ip = "203.0.113.160"
    ctx_store = get_payment_context_store()

    ctx_store.record_context("corr_16_a", "ACC_16_A", observed_ip=shared_ip, order_id="order_16_a")
    ctx_store.record_context("corr_16_b", "ACC_16_B", observed_ip=shared_ip, order_id="order_16_b")

    body_a = build_webhook_body(payment_id="pay_16_a", order_id="order_16_a", notes={"account_id": "ACC_16_A"})
    body_b = build_webhook_body(payment_id="pay_16_b", order_id="order_16_b", notes={"account_id": "ACC_16_B"})

    client.post("/webhooks/razorpay", content=body_a, headers={"X-Razorpay-Signature": compute_signature(body_a)})
    client.post("/webhooks/razorpay", content=body_b, headers={"X-Razorpay-Signature": compute_signature(body_b)})

    graph_store = get_live_abuse_graph_store()
    state = graph_store.get_live_graph_state()
    assert state["total_accounts"] == 2

    # Verify candidate cluster was formed
    clusters = state["candidate_clusters"]
    assert len(clusters) == 1
    c = clusters[0]
    assert c["is_multi_account"] is True
    assert set(c["account_ids"]) == {"ACC_16_A", "ACC_16_B"}

    shared = c["shared_entities"]
    assert len(shared) == 1
    assert shared[0]["entity_type"] == "IP"
    assert shared[0]["entity_id"] == canonicalize_ip(shared_ip)
    assert shared[0]["account_count"] == 2


# 17. Same account does not duplicate IP edges
def test_17_same_account_does_not_duplicate_ip_edges(client):
    """Scenario 17: Multiple payments from same account on same IP increment count on single edge."""
    ip = "203.0.113.170"
    ctx_store = get_payment_context_store()

    ctx_store.record_context("corr_17_1", "ACC_17", observed_ip=ip, order_id="order_17_1")
    ctx_store.record_context("corr_17_2", "ACC_17", observed_ip=ip, order_id="order_17_2")

    body1 = build_webhook_body(payment_id="pay_17_1", order_id="order_17_1", notes={"account_id": "ACC_17"})
    body2 = build_webhook_body(payment_id="pay_17_2", order_id="order_17_2", notes={"account_id": "ACC_17"})

    client.post("/webhooks/razorpay", content=body1, headers={"X-Razorpay-Signature": compute_signature(body1)})
    client.post("/webhooks/razorpay", content=body2, headers={"X-Razorpay-Signature": compute_signature(body2)})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_17")
    ip_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "IP"]
    assert len(ip_edges) == 1
    assert ip_edges[0]["interaction_count"] == 2


# 18. PAYMENT entity does not bridge accounts
def test_18_payment_entity_does_not_bridge_accounts(client):
    """Scenario 18: PAYMENT entities remain account observations and never bridge accounts."""
    graph_store = get_live_abuse_graph_store()
    graph_store.record_webhook_event(
        event_id="evt_p18_1",
        event_type="payment.captured",
        account_id="ACC_18_A",
        payment_id="pay_18_1",
    )
    graph_store.record_webhook_event(
        event_id="evt_p18_2",
        event_type="payment.captured",
        account_id="ACC_18_B",
        payment_id="pay_18_2",
    )

    clusters = graph_store.get_candidate_clusters()
    # No shared infrastructure -> 2 singletons, 0 multi-account clusters
    assert len(clusters) == 2
    assert all(not c["is_multi_account"] for c in clusters)


# 19. Existing device_id behavior remains unchanged
def test_19_existing_device_id_behavior_remains_unchanged(client):
    """Scenario 19: device_id in notes or context produces ACCOUNT -> DEVICE edge."""
    ctx_store = get_payment_context_store()
    ctx_store.record_context(
        "corr_19",
        "ACC_19",
        observed_ip="198.51.100.19",
        device_id="DEV_SHARED_LAB_001",
        order_id="order_19",
    )

    body = build_webhook_body(payment_id="pay_19", order_id="order_19", notes={"account_id": "ACC_19"})
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": compute_signature(body)})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_19")
    dev_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "DEVICE"]
    ip_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "IP"]
    assert len(dev_edges) == 1
    assert dev_edges[0]["entity_id"] == "DEV_SHARED_LAB_001"
    assert len(ip_edges) == 1
    assert ip_edges[0]["entity_id"] == canonicalize_ip("198.51.100.19")


# 20. Existing bystander protection remains unchanged
def test_20_existing_bystander_protection_remains_unchanged(client):
    """Scenario 20: Bystander sharing an IP with high-risk fraudsters is protected."""
    sentinel = get_abuse_ring_sentinel()
    shared_ip = canonicalize_ip("203.0.113.20")
    accounts = [
        {"account_id": "FRAUD_1", "average_order_value": 450.0, "return_rate": 0.85, "suspicious_activity_score": 0.95},
        {"account_id": "FRAUD_2", "average_order_value": 420.0, "return_rate": 0.80, "suspicious_activity_score": 0.90},
        {"account_id": "BYSTANDER", "average_order_value": 35.0, "return_rate": 0.0, "suspicious_activity_score": 0.02},
    ]
    edges = [
        {"account_id": "FRAUD_1", "entity_type": "IP", "entity_id": shared_ip, "event_type": "ORDER"},
        {"account_id": "FRAUD_2", "entity_type": "IP", "entity_id": shared_ip, "event_type": "ORDER"},
        {"account_id": "BYSTANDER", "entity_type": "IP", "entity_id": shared_ip, "event_type": "ORDER"},
    ]

    result = sentinel.detect(accounts=accounts, edges=edges)
    bystander_role = [a for a in result["account_attribution"] if a["account_id"] == "BYSTANDER"][0]["attribution_role"]
    assert bystander_role == "INCIDENTAL_BYSTANDER"
    assert result["recommended_action"] != "BLOCK_ENTIRE_RING"
