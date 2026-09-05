"""Comprehensive tests for Automatic Real Application-Observed Address Capture & Payment Correlation.

Verifies all 23 prompt-specified scenarios:
1. address normalization
2. whitespace normalization
3. casing normalization
4. multiline address normalization
5. deterministic address hash
6. same normalized address -> same hash
7. different addresses -> different hashes
8. empty address
9. malformed/invalid address handling
10. raw address never stored in graph
11. raw address never returned by API
12. create-order stores address context
13. webhook retrieves address context
14. order_id correlation
15. correlation_id correlation
16. authorized + captured creates one canonical payment relationship
17. duplicate captured webhook does not duplicate address edge
18. two accounts sharing address create shared ADDRESS entity
19. account with unique address remains isolated
20. TTL expiration removes address context
21. bounded store behavior remains correct
22. bystander protection remains intact
23. shared address alone does not trigger automatic blocking
"""

import json
import time
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

from src.api import app, get_abuse_ring_sentinel
from src.payment_context import (
    normalize_address,
    canonicalize_address,
    get_payment_context_store,
    PaymentContextStore,
)
from src.live_abuse_graph import get_live_abuse_graph_store
from src.razorpay_webhook import get_webhook_manager, ENV_WEBHOOK_SECRET

TEST_SECRET = "test_live_graph_secret_addr_998877"


def compute_signature(raw_body: bytes, secret: str = TEST_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def build_webhook_body(
    event: str = "payment.captured",
    payment_id: str = "pay_test_addr_001",
    amount: int = 5000,
    status: str = "captured",
    order_id: str = "order_test_addr_001",
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
                    "notes": notes or {},
                    "created_at": int(time.time()),
                }
            }
        },
    }
    return json.dumps(payload).encode("utf-8")


@pytest.fixture(autouse=True)
def reset_stores(monkeypatch):
    """Ensure clean state before each test."""
    monkeypatch.setenv(ENV_WEBHOOK_SECRET, TEST_SECRET)
    monkeypatch.setenv("RAZORPAY_DEFAULT_MERCHANT_ID", "MERCH_TEST")
    wm = get_webhook_manager()
    wm.reset_metrics()
    graph_store = get_live_abuse_graph_store()
    graph_store.reset()
    ctx_store = get_payment_context_store()
    ctx_store.reset()
    yield
    wm.reset_metrics()
    graph_store.reset()
    ctx_store.reset()


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Unit Tests: Normalization & Hashing (Scenarios 1-9)
# ---------------------------------------------------------------------------

def test_01_address_normalization():
    """Scenario 1: Address normalization produces standard comma-separated format."""
    addr = "450 Industrial Parkway, Chicago, IL 60601"
    norm = normalize_address(addr)
    assert norm == "450 industrial parkway, chicago, il 60601"


def test_02_whitespace_normalization():
    """Scenario 2: Excessive and repeated whitespace, tabs, and padding are collapsed."""
    addr = "  450   Industrial   Parkway ,   Chicago ,  IL   60601   "
    norm = normalize_address(addr)
    assert norm == "450 industrial parkway, chicago, il 60601"


def test_03_casing_normalization():
    """Scenario 3: Uppercase, lowercase, and mixed-case addresses normalize identically."""
    upper = "450 INDUSTRIAL PARKWAY, CHICAGO, IL 60601"
    mixed = "450 Industrial Parkway, Chicago, IL 60601"
    lower = "450 industrial parkway, chicago, il 60601"
    assert normalize_address(upper) == normalize_address(mixed) == normalize_address(lower)


def test_04_multiline_address_normalization():
    """Scenario 4: Multi-line addresses with CRLF/LF line breaks normalize identically."""
    single_line = "450 Industrial Parkway, Chicago, IL 60601"
    multi_line_1 = " 450  INDUSTRIAL PARKWAY,\nChicago, IL 60601 "
    multi_line_2 = "450 Industrial Parkway\r\nChicago, IL 60601"
    norm_single = normalize_address(single_line)
    assert normalize_address(multi_line_1) == norm_single
    assert normalize_address(multi_line_2) == norm_single


def test_05_deterministic_address_hash():
    """Scenario 5: Canonical address hash produces ADDRESS_HASH_<12 uppercase hex> format deterministically."""
    addr = "450 Industrial Parkway, Chicago, IL 60601"
    h1 = canonicalize_address(addr)
    h2 = canonicalize_address(addr)
    assert h1 == h2
    assert h1.startswith("ADDRESS_HASH_")
    assert len(h1) == 25
    hex_part = h1[13:]
    assert len(hex_part) == 12
    assert hex_part.isupper()
    int(hex_part, 16)  # Must be valid hex


def test_06_same_normalized_address_same_hash():
    """Scenario 6: Different formatting of same physical address yields identical canonical hash."""
    addr_clean = "450 Industrial Parkway, Chicago, IL 60601"
    addr_messy = " 450   INDUSTRIAL  PARKWAY,\nChicago,  IL  60601  "
    h_clean = canonicalize_address(addr_clean)
    h_messy = canonicalize_address(addr_messy)
    assert h_clean == h_messy


def test_07_different_addresses_different_hashes():
    """Scenario 7: Distinct addresses yield distinct canonical hashes."""
    h1 = canonicalize_address("450 Industrial Parkway, Chicago, IL 60601")
    h2 = canonicalize_address("100 Main Street, New York, NY 10001")
    assert h1 != h2


def test_08_empty_address():
    """Scenario 8: Empty, whitespace-only, and None addresses return None without crashing."""
    assert normalize_address("") is None
    assert normalize_address("   ") is None
    assert normalize_address(None) is None
    assert canonicalize_address("") is None
    assert canonicalize_address("   ") is None
    assert canonicalize_address(None) is None


def test_09_malformed_invalid_address_handling():
    """Scenario 9: Malformed non-string/non-dict inputs and placeholder strings return None."""
    assert normalize_address(12345) is None
    assert normalize_address(True) is None
    assert normalize_address("none") is None
    assert normalize_address("n/a") is None
    assert normalize_address("null") is None
    assert canonicalize_address(12345) is None
    assert canonicalize_address("undefined") is None


# ---------------------------------------------------------------------------
# Privacy & Security Tests (Scenarios 10-11)
# ---------------------------------------------------------------------------

def test_10_raw_address_never_stored_in_graph(client):
    """Scenario 10: Raw address text is never persisted anywhere in the Live Abuse Graph."""
    raw_addr = "999 Secret Residential Avenue, Suite 12B, Atlanta, GA 30301"

    # Initiate order with raw address
    resp = client.post("/payments/create-order", json={
        "account_id": "ACC_ADDR_PRIVACY_01",
        "amount": 25000,
        "address": raw_addr,
        "device_id": "DEV_ADDR_PRIVACY_01",
    })
    assert resp.status_code == 200
    order_id = resp.json()["order_id"]

    # Deliver webhook
    body = build_webhook_body(
        payment_id="pay_addr_priv_001",
        order_id=order_id,
        notes={"account_id": "ACC_ADDR_PRIVACY_01"},
    )
    sig = compute_signature(body)
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

    graph_store = get_live_abuse_graph_store()
    state = graph_store.get_live_graph_state()
    raw_state_str = json.dumps(state)

    # Assert raw address parts never appear in state
    assert "Secret Residential" not in raw_state_str
    assert "999 Secret" not in raw_state_str
    assert "30301" not in raw_state_str


def test_11_raw_address_never_returned_by_api(client):
    """Scenario 11: Live Abuse Graph APIs return only ADDRESS_HASH_ and never raw address."""
    raw_addr = "742 Evergreen Terrace, Springfield, OR 97477"

    resp = client.post("/payments/create-order", json={
        "account_id": "ACC_ADDR_API_01",
        "amount": 10000,
        "address": raw_addr,
    })
    order_id = resp.json()["order_id"]

    body = build_webhook_body(
        payment_id="pay_api_addr_001",
        order_id=order_id,
        notes={"account_id": "ACC_ADDR_API_01"},
    )
    sig = compute_signature(body)
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

    # Test GET /risk/abuse-ring/live
    resp_graph = client.get("/risk/abuse-ring/live")
    assert resp_graph.status_code == 200
    graph_text = resp_graph.text
    assert "Evergreen Terrace" not in graph_text
    assert "97477" not in graph_text
    assert "ADDRESS_HASH_" in graph_text

    # Test GET /risk/abuse-ring/live/{account_id}
    resp_acc = client.get("/risk/abuse-ring/live/ACC_ADDR_API_01")
    assert resp_acc.status_code == 200
    acc_text = resp_acc.text
    assert "Evergreen Terrace" not in acc_text
    assert "ADDRESS_HASH_" in acc_text


# ---------------------------------------------------------------------------
# Create-Order & Webhook Correlation Tests (Scenarios 12-17)
# ---------------------------------------------------------------------------

def test_12_create_order_stores_address_context(client):
    """Scenario 12: POST /payments/create-order stores address context and returns address_captured=True."""
    raw_addr = "450 Industrial Parkway, Chicago, IL 60601"
    resp = client.post("/payments/create-order", json={
        "account_id": "ACC_ADDR_STORE_01",
        "amount": 15000,
        "address": raw_addr,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["address_captured"] is True
    order_id = data["order_id"]

    ctx_store = get_payment_context_store()
    ctx = ctx_store.get_context(order_id)
    assert ctx is not None
    assert ctx["observed_address_hash"] == canonicalize_address(raw_addr)


def test_13_webhook_retrieves_address_context(client):
    """Scenario 13: Verified webhook retrieves address context even without address in notes."""
    raw_addr = "450 Industrial Parkway, Chicago, IL 60601"
    expected_hash = canonicalize_address(raw_addr)

    resp = client.post("/payments/create-order", json={
        "account_id": "ACC_ADDR_CTX_01",
        "amount": 20000,
        "address": raw_addr,
    })
    order_id = resp.json()["order_id"]

    # Webhook contains NO address in notes
    body = build_webhook_body(
        payment_id="pay_addr_ctx_001",
        order_id=order_id,
        notes={"account_id": "ACC_ADDR_CTX_01"},
    )
    sig = compute_signature(body)
    w_resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    assert w_resp.status_code == 200

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_ADDR_CTX_01")
    addr_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "ADDRESS"]
    assert len(addr_edges) == 1
    assert addr_edges[0]["entity_id"] == expected_hash


def test_14_order_id_correlation(client):
    """Scenario 14: Payment context correlation successfully indexes and retrieves by order_id."""
    raw_addr = "800 West Peachtree St NW, Atlanta, GA 30308"
    ctx_store = get_payment_context_store()
    ctx_store.record_context(
        correlation_id="corr_custom_991",
        order_id="order_custom_991",
        account_id="ACC_ORD_ID_TEST",
        observed_address=raw_addr,
    )

    ctx = ctx_store.get_context("order_custom_991")
    assert ctx is not None
    assert ctx["account_id"] == "ACC_ORD_ID_TEST"
    assert ctx["observed_address_hash"] == canonicalize_address(raw_addr)


def test_15_correlation_id_correlation(client):
    """Scenario 15: Payment context correlation succeeds via correlation_id lookup."""
    raw_addr = "500 South Michigan Ave, Chicago, IL 60605"
    ctx_store = get_payment_context_store()
    ctx_store.record_context(
        correlation_id="corr_lookup_key_002",
        order_id="order_razorpay_9999",
        account_id="ACC_CORR_TEST",
        observed_address=raw_addr,
    )

    ctx = ctx_store.get_context("corr_lookup_key_002")
    assert ctx is not None
    assert ctx["account_id"] == "ACC_CORR_TEST"
    assert ctx["observed_address_hash"] == canonicalize_address(raw_addr)


def test_16_authorized_plus_captured_canonical_payment(client):
    """Scenario 16: payment.authorized + payment.captured creates exactly one canonical payment & address edge."""
    raw_addr = "450 Industrial Parkway, Chicago, IL 60601"
    expected_hash = canonicalize_address(raw_addr)

    resp = client.post("/payments/create-order", json={
        "account_id": "ACC_CANONICAL_01",
        "amount": 12000,
        "address": raw_addr,
    })
    order_id = resp.json()["order_id"]

    # 1. Authorized
    body_auth = build_webhook_body(
        event="payment.authorized",
        payment_id="pay_canonical_001",
        order_id=order_id,
        status="authorized",
        notes={"account_id": "ACC_CANONICAL_01"},
    )
    sig_auth = compute_signature(body_auth)
    client.post("/webhooks/razorpay", content=body_auth, headers={"X-Razorpay-Signature": sig_auth})

    # 2. Captured
    body_cap = build_webhook_body(
        event="payment.captured",
        payment_id="pay_canonical_001",
        order_id=order_id,
        status="captured",
        notes={"account_id": "ACC_CANONICAL_01"},
    )
    sig_cap = compute_signature(body_cap)
    client.post("/webhooks/razorpay", content=body_cap, headers={"X-Razorpay-Signature": sig_cap})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_CANONICAL_01")
    pay_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "PAYMENT"]
    addr_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "ADDRESS"]

    assert len(pay_edges) == 1
    assert pay_edges[0]["interaction_count"] == 1
    assert len(addr_edges) == 1
    assert addr_edges[0]["entity_id"] == expected_hash


def test_17_duplicate_captured_webhook_does_not_duplicate_address_edge(client):
    """Scenario 17: Duplicate payment.captured webhooks do not duplicate address edges or counts."""
    raw_addr = "450 Industrial Parkway, Chicago, IL 60601"
    resp = client.post("/payments/create-order", json={
        "account_id": "ACC_DEDUP_ADDR_01",
        "amount": 10000,
        "address": raw_addr,
    })
    order_id = resp.json()["order_id"]

    body = build_webhook_body(
        event="payment.captured",
        payment_id="pay_dedup_addr_001",
        order_id=order_id,
        status="captured",
        notes={"account_id": "ACC_DEDUP_ADDR_01"},
    )
    sig = compute_signature(body)

    # First delivery
    r1 = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    assert r1.status_code == 200

    # Second delivery (duplicate event)
    r2 = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    assert r2.status_code == 200

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_DEDUP_ADDR_01")
    addr_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "ADDRESS"]
    assert len(addr_edges) == 1


# ---------------------------------------------------------------------------
# Multi-Account Topology & Clustering Tests (Scenarios 18-19)
# ---------------------------------------------------------------------------

def test_18_two_accounts_sharing_address_create_shared_entity(client):
    """Scenario 18: Two distinct accounts using the same address share an ADDRESS entity and cluster."""
    shared_addr = "450 Industrial Parkway, Chicago, IL 60601"
    expected_addr_hash = canonicalize_address(shared_addr)

    # Account A
    resp_a = client.post("/payments/create-order", json={
        "account_id": "ACC_MERCHANT_90210",
        "amount": 15000,
        "address": shared_addr,
        "device_id": "DEV_SHARED_LAB_001",
    })
    ord_a = resp_a.json()["order_id"]

    body_a = build_webhook_body(
        payment_id="pay_shared_addr_A",
        order_id=ord_a,
        notes={"account_id": "ACC_MERCHANT_90210"},
    )
    client.post("/webhooks/razorpay", content=body_a, headers={"X-Razorpay-Signature": compute_signature(body_a)})

    # Account B
    resp_b = client.post("/payments/create-order", json={
        "account_id": "ACC_WARD_00001",
        "amount": 15000,
        "address": shared_addr,
        "device_id": "DEV_SHARED_LAB_001",
    })
    ord_b = resp_b.json()["order_id"]

    body_b = build_webhook_body(
        payment_id="pay_shared_addr_B",
        order_id=ord_b,
        notes={"account_id": "ACC_WARD_00001"},
    )
    client.post("/webhooks/razorpay", content=body_b, headers={"X-Razorpay-Signature": compute_signature(body_b)})

    graph_store = get_live_abuse_graph_store()
    clusters = graph_store.get_candidate_clusters()

    # Both accounts must belong to the same multi-account candidate cluster
    multi_clusters = [c for c in clusters if c["is_multi_account"]]
    assert len(multi_clusters) >= 1
    shared_cluster = multi_clusters[0]

    assert "ACC_MERCHANT_90210" in shared_cluster["account_ids"]
    assert "ACC_WARD_00001" in shared_cluster["account_ids"]

    shared_tokens = {se["entity_id"] for se in shared_cluster["shared_entities"]}
    assert expected_addr_hash in shared_tokens
    assert "DEV_SHARED_LAB_001" in shared_tokens


def test_19_account_with_unique_address_remains_isolated(client):
    """Scenario 19: An account with an independent unique address remains an isolated singleton cluster."""
    resp = client.post("/payments/create-order", json={
        "account_id": "ACC_ISOLATED_ADDR",
        "amount": 10000,
        "address": "999 Lone Road, Helena, MT 59601",
        "device_id": "DEV_LONE_001",
    })
    ord_id = resp.json()["order_id"]

    body = build_webhook_body(
        payment_id="pay_lone_001",
        order_id=ord_id,
        notes={"account_id": "ACC_ISOLATED_ADDR"},
    )
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": compute_signature(body)})

    graph_store = get_live_abuse_graph_store()
    clusters = graph_store.get_candidate_clusters()
    lone_cluster = next((c for c in clusters if "ACC_ISOLATED_ADDR" in c["account_ids"]), None)

    assert lone_cluster is not None
    assert lone_cluster["is_multi_account"] is False
    assert len(lone_cluster["account_ids"]) == 1
    assert len(lone_cluster["shared_entities"]) == 0


# ---------------------------------------------------------------------------
# Storage, Expiration & Bounded Capacity Tests (Scenarios 20-21)
# ---------------------------------------------------------------------------

def test_20_ttl_expiration_removes_address_context():
    """Scenario 20: Expired payment context purges address hash on lookup."""
    store = PaymentContextStore(default_ttl_seconds=1)
    store.record_context(
        correlation_id="corr_exp_addr_01",
        account_id="ACC_EXP_01",
        observed_address="450 Industrial Parkway, Chicago, IL 60601",
        ttl_seconds=1,
    )

    # Immediately active
    ctx = store.get_context("corr_exp_addr_01")
    assert ctx is not None
    assert ctx["observed_address_hash"] is not None

    # Wait for TTL to elapse
    time.sleep(1.1)

    # After expiry, returns None
    assert store.get_context("corr_exp_addr_01") is None


def test_21_bounded_store_behavior_remains_correct():
    """Scenario 21: PaymentContextStore enforces bounded capacity and LRU eviction with address contexts."""
    store = PaymentContextStore(max_capacity=3, default_ttl_seconds=3600)
    for i in range(5):
        store.record_context(
            correlation_id=f"corr_b_{i}",
            account_id=f"ACC_B_{i}",
            observed_address=f"{100 + i} Main Street, Suite {i}, City, ST {10000 + i}",
        )

    # Size must not exceed max_capacity
    assert store.size() <= 3
    # Earliest items must have been evicted
    assert store.get_context("corr_b_0") is None
    assert store.get_context("corr_b_1") is None
    # Latest item must still be present
    assert store.get_context("corr_b_4") is not None


# ---------------------------------------------------------------------------
# Abuse-Ring Sentinel Evaluation & Bystander Protection (Scenarios 22-23)
# ---------------------------------------------------------------------------

def test_22_bystander_protection_remains_intact():
    """Scenario 22: Bystander sharing an address with high-risk accounts is protected as INCIDENTAL_BYSTANDER."""
    sentinel = get_abuse_ring_sentinel()
    shared_addr = canonicalize_address("450 Industrial Parkway, Chicago, IL 60601")
    accounts = [
        {"account_id": "FRAUD_ADDR_1", "average_order_value": 450.0, "return_rate": 0.85, "suspicious_activity_score": 0.95},
        {"account_id": "FRAUD_ADDR_2", "average_order_value": 420.0, "return_rate": 0.80, "suspicious_activity_score": 0.90},
        {"account_id": "BYSTANDER_ADDR", "average_order_value": 35.0, "return_rate": 0.0, "suspicious_activity_score": 0.02},
    ]
    edges = [
        {"account_id": "FRAUD_ADDR_1", "entity_type": "ADDRESS", "entity_id": shared_addr, "event_type": "ORDER"},
        {"account_id": "FRAUD_ADDR_2", "entity_type": "ADDRESS", "entity_id": shared_addr, "event_type": "ORDER"},
        {"account_id": "BYSTANDER_ADDR", "entity_type": "ADDRESS", "entity_id": shared_addr, "event_type": "ORDER"},
    ]

    result = sentinel.detect(accounts=accounts, edges=edges)
    bystander = [a for a in result["account_attribution"] if a["account_id"] == "BYSTANDER_ADDR"][0]
    assert bystander["attribution_role"] == "INCIDENTAL_BYSTANDER"
    assert result["recommended_action"] != "BLOCK_ENTIRE_RING"


def test_23_shared_address_alone_does_not_trigger_automatic_blocking(client):
    """Scenario 23: Shared address alone MUST NOT trigger automatic BLOCK_ENTIRE_RING action."""
    shared_addr = "450 Industrial Parkway, Chicago, IL 60601"

    # Ingest 2 accounts sharing only address (different devices)
    for i, acc in enumerate(["ACC_MERCHANT_90210", "ACC_WARD_00001"]):
        resp = client.post("/payments/create-order", json={
            "account_id": acc,
            "amount": 15000,
            "address": shared_addr,
            "device_id": f"DEV_UNIQUE_{i:03d}",
        })
        body = build_webhook_body(
            payment_id=f"pay_shared_addr_only_{acc}",
            order_id=resp.json()["order_id"],
            notes={"account_id": acc},
        )
        client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": compute_signature(body)})

    # Evaluate candidate cluster
    analyze_resp = client.post("/risk/abuse-ring/live/analyze")
    assert analyze_resp.status_code == 200
    res = analyze_resp.json()

    # Shared address is graph evidence, but without malicious behavioral traits
    # it must NOT trigger aggressive blocking
    assert res["recommended_action"] != "BLOCK_ENTIRE_RING"
    assert res["final_ring_score"] < 0.70
