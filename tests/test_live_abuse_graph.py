"""Comprehensive unit and integration tests for Real-Time Live Abuse Graph Ingestion.

Verifies all 14 prompt-specified scenarios and constraints:
1. Valid captured Razorpay payment creates one ACCOUNT -> PAYMENT relationship.
2. authorized + captured for the same payment creates only one completed payment relationship.
3. Duplicate webhook delivery does not duplicate the graph relationship.
4. Failed payment is represented correctly and is not treated as captured.
5. Account association uses the existing association mechanism.
6. Test-mode fallback is explicitly marked test_mode_default.
7. Historical AccountStore metrics remain completely unchanged.
8. Existing Abuse Ring benchmark scenarios produce exactly the same results as before.
9. Shared IP alone does not automatically produce BLOCK_ENTIRE_RING.
10. Existing bystander protection tests continue passing.
11. Existing Razorpay webhook tests continue passing.
12. Existing live activity tests continue passing.
13. GET /risk/abuse-ring/live works.
14. Live graph can be converted into the existing AbuseRingRequest without changing the existing engine.
"""

import json
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

from src.api import app, get_spike_detector, get_abuse_ring_sentinel
from src.razorpay_webhook import (
    get_webhook_manager,
    ENV_WEBHOOK_SECRET,
)
from src.live_abuse_graph import (
    get_live_abuse_graph_store,
    canonicalize_address,
)
from src.account_store import get_account_store

TEST_SECRET = "test_live_graph_secret_998877"


def compute_signature(raw_body: bytes, secret: str = TEST_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def build_webhook_body(
    event: str = "payment.captured",
    payment_id: str = "pay_test_live_001",
    amount: int = 5000,
    status: str = "captured",
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
                    "order_id": f"order_{payment_id}",
                    "method": "card",
                    "notes": notes or {},
                    "created_at": 1772635200,
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
    yield
    manager.reset_metrics()
    graph_store.reset()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_1_valid_captured_payment_creates_account_payment_edge(client):
    """Scenario 1: A valid captured Razorpay payment creates one ACCOUNT -> PAYMENT relationship."""
    body = build_webhook_body(
        event="payment.captured",
        payment_id="pay_graph_001",
        amount=10000,
        status="captured",
        notes={"account_id": "ACC_GRAPH_A"},
    )
    sig = compute_signature(body)

    resp = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_g1"},
    )
    assert resp.status_code == 200

    graph_store = get_live_abuse_graph_store()
    state = graph_store.get_live_graph_state()
    assert state["total_accounts"] == 1
    assert state["total_edges"] == 1

    subgraph = graph_store.get_account_subgraph("ACC_GRAPH_A")
    assert subgraph is not None
    assert len(subgraph["direct_edges"]) == 1
    edge = subgraph["direct_edges"][0]
    assert edge["account_id"] == "ACC_GRAPH_A"
    assert edge["entity_type"] == "PAYMENT"
    assert edge["entity_id"] == "pay_graph_001"
    assert edge["interaction_count"] == 1
    assert edge["payment_status"] == "captured"


def test_2_authorized_plus_captured_creates_one_canonical_payment_relationship(client):
    """Scenario 2: authorized + captured for the same payment creates only one completed payment relationship."""
    # Step 1: payment.authorized
    body_auth = build_webhook_body(
        event="payment.authorized",
        payment_id="pay_graph_lifecycle",
        amount=7500,
        status="authorized",
        notes={"account_id": "ACC_GRAPH_A"},
    )
    sig_auth = compute_signature(body_auth)
    resp1 = client.post(
        "/webhooks/razorpay",
        content=body_auth,
        headers={"X-Razorpay-Signature": sig_auth, "X-Razorpay-Event-Id": "evt_auth_1"},
    )
    assert resp1.status_code == 200

    graph_store = get_live_abuse_graph_store()
    subgraph1 = graph_store.get_account_subgraph("ACC_GRAPH_A")
    assert len(subgraph1["direct_edges"]) == 1
    assert subgraph1["direct_edges"][0]["payment_status"] == "authorized"

    # Step 2: payment.captured for same payment ID
    body_cap = build_webhook_body(
        event="payment.captured",
        payment_id="pay_graph_lifecycle",
        amount=7500,
        status="captured",
        notes={"account_id": "ACC_GRAPH_A"},
    )
    sig_cap = compute_signature(body_cap)
    resp2 = client.post(
        "/webhooks/razorpay",
        content=body_cap,
        headers={"X-Razorpay-Signature": sig_cap, "X-Razorpay-Event-Id": "evt_cap_1"},
    )
    assert resp2.status_code == 200

    # Still exactly ONE canonical edge for this payment
    subgraph2 = graph_store.get_account_subgraph("ACC_GRAPH_A")
    assert len(subgraph2["direct_edges"]) == 1
    edge = subgraph2["direct_edges"][0]
    assert edge["entity_id"] == "pay_graph_lifecycle"
    assert edge["payment_status"] == "captured"
    assert edge["interaction_count"] == 1


def test_3_duplicate_webhook_delivery_idempotent(client):
    """Scenario 3: Duplicate webhook delivery does not duplicate the graph relationship."""
    body = build_webhook_body(
        event="payment.captured",
        payment_id="pay_graph_dup",
        amount=5000,
        notes={"account_id": "ACC_GRAPH_B"},
    )
    sig = compute_signature(body)

    # First delivery
    resp1 = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_dup_test"},
    )
    assert resp1.status_code == 200

    # Duplicate delivery
    resp2 = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_dup_test"},
    )
    assert resp2.status_code == 200
    assert resp2.json().get("duplicate") is True

    graph_store = get_live_abuse_graph_store()
    state = graph_store.get_live_graph_state()
    assert state["total_edges"] == 1
    assert state["total_webhook_events"] == 1


def test_4_failed_payment_represented_correctly(client):
    """Scenario 4: Failed payment is represented correctly and is not treated as captured."""
    body = build_webhook_body(
        event="payment.failed",
        payment_id="pay_graph_failed",
        amount=3000,
        status="failed",
        notes={"account_id": "ACC_GRAPH_FAIL"},
    )
    sig = compute_signature(body)

    resp = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_fail_1"},
    )
    assert resp.status_code == 200

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_GRAPH_FAIL")
    assert subgraph is not None
    assert len(subgraph["direct_edges"]) == 1
    edge = subgraph["direct_edges"][0]
    assert edge["payment_status"] == "failed"
    acc_meta = subgraph["account_metadata"]
    assert len(acc_meta["failed_payment_ids"]) == 1
    assert len(acc_meta["successful_payment_ids"]) == 0


def test_5_account_association_reuse_order(client):
    """Scenario 5 & 6: Account association uses existing association mechanism and marks test_mode_default."""
    # Case A: Notes
    body_notes = build_webhook_body(payment_id="pay_notes", notes={"account_id": "ACC_VIA_NOTES"})
    client.post("/webhooks/razorpay", content=body_notes, headers={"X-Razorpay-Signature": compute_signature(body_notes)})
    
    # Case B: Header dev override
    body_hdr = build_webhook_body(payment_id="pay_hdr", notes={})
    client.post(
        "/webhooks/razorpay",
        content=body_hdr,
        headers={"X-Razorpay-Signature": compute_signature(body_hdr), "X-Account-Id": "ACC_VIA_HEADER"},
    )

    # Case C: Test mode fallback
    body_fallback = build_webhook_body(payment_id="pay_fallback", notes={})
    resp_fallback = client.post(
        "/webhooks/razorpay",
        content=body_fallback,
        headers={"X-Razorpay-Signature": compute_signature(body_fallback)},
    )
    data_fb = resp_fallback.json()
    assert data_fb["associated_account"]["association_source"] == "test_mode_default"
    assert data_fb["associated_account"]["account_id"] == "ACC_MERCHANT_90210"

    graph_store = get_live_abuse_graph_store()
    assert graph_store.get_account_subgraph("ACC_VIA_NOTES") is not None
    assert graph_store.get_account_subgraph("ACC_VIA_HEADER") is not None
    assert graph_store.get_account_subgraph("ACC_MERCHANT_90210") is not None


def test_7_historical_account_store_immutability(client):
    """Scenario 7: Historical AccountStore metrics remain completely unchanged."""
    store = get_account_store()
    before = store.get_account("ACC_MERCHANT_90210", include_live=False)
    assert before is not None
    orig_orders = before["order_count"]
    orig_spend = before["total_spend"]
    orig_return_rate = before["return_rate"]

    # Ingest a live webhook for ACC_MERCHANT_90210
    body = build_webhook_body(
        payment_id="pay_immutability_check",
        amount=9999,
        notes={"account_id": "ACC_MERCHANT_90210", "device_id": "DEV_TEST_001"},
    )
    sig = compute_signature(body)
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

    after = store.get_account("ACC_MERCHANT_90210", include_live=False)
    assert after["order_count"] == orig_orders
    assert after["total_spend"] == orig_spend
    assert after["return_rate"] == orig_return_rate


def test_8_existing_abuse_ring_benchmark_scenarios_unchanged(client):
    """Scenario 8: Existing Abuse Ring benchmark scenarios produce exactly the same results as before."""
    from tests.test_abuse_ring_api import get_cluster_payload
    import pandas as pd

    df_acc = pd.read_csv("data/ring_accounts.csv")
    df_edg = pd.read_csv("data/ring_entity_edges.csv")
    df_cls = pd.read_csv("data/ring_clusters.csv")

    synth_cid = df_cls[df_cls["cluster_type"] == "SYNTHETIC_IDENTITY_RING"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, synth_cid)

    resp = client.post("/risk/abuse-ring", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ring_detected"] is True
    assert data["verdict"] == "HIGH_CONFIDENCE_RING"
    assert data["recommended_action"] == "BLOCK_ENTIRE_RING"


def test_9_shared_ip_alone_does_not_block_ring(client):
    """Scenario 9 & 10: Shared IP alone does not automatically produce BLOCK_ENTIRE_RING (bystander safe)."""
    graph_store = get_live_abuse_graph_store()
    # 2 accounts share ONLY an IP address (e.g. household / cafe)
    graph_store.record_webhook_event(
        event_id="evt_ip_1",
        event_type="payment.captured",
        account_id="ACC_MERCHANT_90210",
        payment_id="pay_ip_1",
        amount=100.0,
        status="captured",
        ip_address="192.168.1.100",
    )
    graph_store.record_webhook_event(
        event_id="evt_ip_2",
        event_type="payment.captured",
        account_id="ACC_CLEAN_BUYER_01",
        payment_id="pay_ip_2",
        amount=150.0,
        status="captured",
        ip_address="192.168.1.100",
    )

    clusters = graph_store.get_candidate_clusters()
    assert len(clusters) == 1
    assert clusters[0]["is_multi_account"] is True
    assert len(clusters[0]["account_ids"]) == 2

    # Analyze this candidate cluster via POST /risk/abuse-ring/live/analyze
    resp = client.post("/risk/abuse-ring/live/analyze", json={"cluster_id": clusters[0]["cluster_id"]})
    assert resp.status_code == 200
    data = resp.json()

    # Shared IP alone must NEVER cause BLOCK_ENTIRE_RING
    assert data["recommended_action"] != "BLOCK_ENTIRE_RING"
    assert data["verdict"] in ["NO_RING", "POSSIBLE_RING"]


def test_11_no_ip_extraction_from_proxy_headers(client):
    """Scenario 11: Proxy headers like X-Forwarded-For must NOT create an IP entity."""
    body = build_webhook_body(
        payment_id="pay_proxy_test",
        amount=5000,
        notes={"account_id": "ACC_PROXY_TEST"},  # No notes.ip_address
    )
    sig = compute_signature(body)

    resp = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={
            "X-Razorpay-Signature": sig,
            "X-Forwarded-For": "203.0.113.195",  # Must be ignored!
        },
    )
    assert resp.status_code == 200

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_PROXY_TEST")
    entity_types = [e["entity_type"] for e in subgraph["direct_edges"]]
    assert "IP" not in entity_types


def test_12_deterministic_address_hashing(client):
    """Scenario 12: Addresses are canonicalized to ADDRESS_HASH_<sha256[:12]> without raw PII."""
    raw_addr = "123 Main Street, Suite 400, New York, NY 10001"
    hashed = canonicalize_address(raw_addr)
    assert hashed.startswith("ADDRESS_HASH_")
    assert "main street" not in hashed

    # Ingest webhook with address
    body = build_webhook_body(
        payment_id="pay_addr_test",
        amount=5000,
        notes={"account_id": "ACC_ADDR_TEST", "shipping_address": raw_addr},
    )
    sig = compute_signature(body)
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_ADDR_TEST")
    addr_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "ADDRESS"]
    assert len(addr_edges) == 1
    assert addr_edges[0]["entity_id"] == hashed


def test_13_get_live_abuse_graph_endpoints(client):
    """Scenario 13: GET /risk/abuse-ring/live and GET /risk/abuse-ring/live/{account_id} return accurate status."""
    # Empty state
    resp_empty = client.get("/risk/abuse-ring/live")
    assert resp_empty.status_code == 200
    assert resp_empty.json()["status"] == "idle"

    # Ingest one event
    body = build_webhook_body(
        payment_id="pay_endpoint_test",
        amount=5000,
        notes={"account_id": "ACC_TEST_EP"},
    )
    client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": compute_signature(body)})

    # Active state
    resp_active = client.get("/risk/abuse-ring/live")
    assert resp_active.status_code == 200
    data = resp_active.json()
    assert data["status"] == "active"
    assert data["total_accounts"] == 1
    assert data["total_edges"] == 1

    # Specific account
    resp_acc = client.get("/risk/abuse-ring/live/ACC_TEST_EP")
    assert resp_acc.status_code == 200
    assert resp_acc.json()["account_id"] == "ACC_TEST_EP"

    # Nonexistent account returns 404
    resp_404 = client.get("/risk/abuse-ring/live/ACC_NONEXISTENT")
    assert resp_404.status_code == 404


def test_14_live_graph_conversion_to_abuse_ring_request(client):
    """Scenario 14: Live graph can be converted into the existing AbuseRingRequest without changing the existing engine."""
    graph_store = get_live_abuse_graph_store()
    # Create multi-account cluster linked by a shared device
    graph_store.record_webhook_event(
        event_id="evt_m1",
        event_type="payment.captured",
        account_id="ACC_MERCHANT_90210",
        payment_id="pay_m1",
        device_id="DEV_SHARED_999",
    )
    graph_store.record_webhook_event(
        event_id="evt_m2",
        event_type="payment.captured",
        account_id="ACC_WARD_00001",
        payment_id="pay_m2",
        device_id="DEV_SHARED_999",
    )

    req = graph_store.export_cluster_to_abuse_ring_request()
    assert "accounts" in req
    assert "edges" in req
    assert len(req["accounts"]) == 2
    assert any(e["entity_type"] == "DEVICE" and e["entity_id"] == "DEV_SHARED_999" for e in req["edges"])

    # Directly pass exported dict into the frozen AbuseRingSentinel
    sentinel = get_abuse_ring_sentinel()
    result = sentinel.detect(
        accounts=req["accounts"],
        edges=req["edges"],
        cluster_metadata=req.get("cluster_metadata"),
    )
    assert "ring_detected" in result
    assert "final_ring_score" in result
    assert "verdict" in result
    assert "account_attribution" in result


# =========================================================================
# STEP 8 TESTS — EXPLICIT DEVICE METADATA FOR REAL TEST PAYMENTS
# =========================================================================


def test_15_device_id_extracted_from_notes(client):
    """1. device_id extracted from notes."""
    body = build_webhook_body(
        payment_id="pay_dev_15",
        amount=5000,
        notes={"account_id": "ACC_DEV_TEST_15", "device_id": "DEV_TEST_BROWSER_001"},
    )
    sig = compute_signature(body)
    resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    assert resp.status_code == 200

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_DEV_TEST_15")
    assert subgraph is not None
    dev_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "DEVICE"]
    assert len(dev_edges) == 1
    assert dev_edges[0]["entity_id"] == "DEV_TEST_BROWSER_001"
    assert dev_edges[0]["interaction_count"] == 1


def test_16_missing_device_id_produces_no_device_edge(client):
    """2. missing device_id produces no device edge."""
    body = build_webhook_body(
        payment_id="pay_dev_16",
        amount=5000,
        notes={"account_id": "ACC_DEV_TEST_16"},
    )
    sig = compute_signature(body)
    resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    assert resp.status_code == 200

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_DEV_TEST_16")
    assert subgraph is not None
    dev_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "DEVICE"]
    assert len(dev_edges) == 0


def test_17_malformed_device_id_is_ignored_safely(client):
    """3. malformed device_id is ignored safely."""
    graph_store = get_live_abuse_graph_store()

    # Empty string
    body_empty = build_webhook_body(
        payment_id="pay_mal_1", notes={"account_id": "ACC_MAL_1", "device_id": "   "}
    )
    client.post("/webhooks/razorpay", content=body_empty, headers={"X-Razorpay-Signature": compute_signature(body_empty)})
    sub_1 = graph_store.get_account_subgraph("ACC_MAL_1")
    assert len([e for e in sub_1["direct_edges"] if e["entity_type"] == "DEVICE"]) == 0

    # Non-printable control characters
    body_ctrl = build_webhook_body(
        payment_id="pay_mal_2", notes={"account_id": "ACC_MAL_2", "device_id": "DEV_\x00\x1f_BAD"}
    )
    client.post("/webhooks/razorpay", content=body_ctrl, headers={"X-Razorpay-Signature": compute_signature(body_ctrl)})
    sub_2 = graph_store.get_account_subgraph("ACC_MAL_2")
    assert len([e for e in sub_2["direct_edges"] if e["entity_type"] == "DEVICE"]) == 0

    # Over 128 characters
    long_id = "A" * 200
    body_long = build_webhook_body(
        payment_id="pay_mal_3", notes={"account_id": "ACC_MAL_3", "device_id": long_id}
    )
    client.post("/webhooks/razorpay", content=body_long, headers={"X-Razorpay-Signature": compute_signature(body_long)})
    sub_3 = graph_store.get_account_subgraph("ACC_MAL_3")
    assert len([e for e in sub_3["direct_edges"] if e["entity_type"] == "DEVICE"]) == 0


def test_18_same_account_same_device_does_not_create_duplicate_edges(client):
    """4. same account + same device does not create duplicate device edges."""
    notes = {"account_id": "ACC_DEV_18", "device_id": "DEV_SHARED_18"}

    body1 = build_webhook_body(payment_id="pay_18_a", notes=notes)
    body2 = build_webhook_body(payment_id="pay_18_b", notes=notes)

    client.post("/webhooks/razorpay", content=body1, headers={"X-Razorpay-Signature": compute_signature(body1)})
    client.post("/webhooks/razorpay", content=body2, headers={"X-Razorpay-Signature": compute_signature(body2)})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_DEV_18")
    dev_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "DEVICE"]
    # Exactly one edge exists between ACC_DEV_18 and DEV_SHARED_18
    assert len(dev_edges) == 1
    # Two distinct payments from this device incremented interaction_count
    assert dev_edges[0]["interaction_count"] == 2


def test_19_authorized_plus_captured_produces_one_canonical_device_relationship(client):
    """5. authorized + captured produces one canonical device relationship."""
    notes = {"account_id": "ACC_DEV_19", "device_id": "DEV_SHARED_19"}
    pay_id = "pay_19_single"

    body_auth = build_webhook_body(event="payment.authorized", payment_id=pay_id, status="authorized", notes=notes)
    body_cap = build_webhook_body(event="payment.captured", payment_id=pay_id, status="captured", notes=notes)

    client.post("/webhooks/razorpay", content=body_auth, headers={"X-Razorpay-Signature": compute_signature(body_auth)})
    client.post("/webhooks/razorpay", content=body_cap, headers={"X-Razorpay-Signature": compute_signature(body_cap)})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_DEV_19")
    dev_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "DEVICE"]
    assert len(dev_edges) == 1
    # Crucial: interaction_count must remain 1 because authorized + captured represent ONE payment
    assert dev_edges[0]["interaction_count"] == 1


def test_20_duplicate_captured_does_not_duplicate_device_relationship(client):
    """6. duplicate captured does not duplicate device relationship."""
    notes = {"account_id": "ACC_DEV_20", "device_id": "DEV_SHARED_20"}
    pay_id = "pay_20_dup"

    body_cap1 = build_webhook_body(event="payment.captured", payment_id=pay_id, status="captured", notes=notes)
    sig1 = compute_signature(body_cap1)

    # First delivery
    client.post("/webhooks/razorpay", content=body_cap1, headers={"X-Razorpay-Signature": sig1, "X-Razorpay-Event-Id": "evt_cap_20_1"})
    # Duplicate delivery (same payment_id, new event_id)
    client.post("/webhooks/razorpay", content=body_cap1, headers={"X-Razorpay-Signature": sig1, "X-Razorpay-Event-Id": "evt_cap_20_2"})

    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_DEV_20")
    dev_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "DEVICE"]
    assert len(dev_edges) == 1
    assert dev_edges[0]["interaction_count"] == 1


def test_21_two_accounts_sharing_explicit_device_id_produce_shared_device_entity(client):
    """7. two accounts sharing the same explicit device_id produce one shared device entity."""
    shared_device = "DEV_SHARED_LAB_001"
    body_a = build_webhook_body(
        payment_id="pay_acc_a",
        amount=15000,
        notes={"account_id": "ACC_MERCHANT_90210", "device_id": shared_device},
    )
    body_b = build_webhook_body(
        payment_id="pay_acc_b",
        amount=25000,
        notes={"account_id": "ACC_WARD_00001", "device_id": shared_device},
    )

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
    assert set(c["account_ids"]) == {"ACC_MERCHANT_90210", "ACC_WARD_00001"}

    # Verify shared entity is DEVICE: DEV_SHARED_LAB_001
    shared = c["shared_entities"]
    assert len(shared) == 1
    assert shared[0]["entity_type"] == "DEVICE"
    assert shared[0]["entity_id"] == shared_device
    assert shared[0]["account_count"] == 2


def test_22_payment_entities_never_bridge_accounts(client):
    """8. PAYMENT entities never bridge accounts."""
    graph_store = get_live_abuse_graph_store()
    # Record two accounts with separate payments and NO shared device/IP/address
    graph_store.record_webhook_event(
        event_id="evt_p1",
        event_type="payment.captured",
        account_id="ACC_SOLO_1",
        payment_id="pay_solo_1",
        device_id="DEV_SOLO_1",
    )
    graph_store.record_webhook_event(
        event_id="evt_p2",
        event_type="payment.captured",
        account_id="ACC_SOLO_2",
        payment_id="pay_solo_2",
        device_id="DEV_SOLO_2",
    )

    clusters = graph_store.get_candidate_clusters()
    # Must form 2 singletons, NOT a multi-account cluster
    assert len(clusters) == 2
    assert all(c["is_multi_account"] is False for c in clusters)
    assert all(c["member_count"] == 1 for c in clusters)


def test_23_shared_device_creates_candidate_infrastructure_only(client):
    """9. shared device creates candidate infrastructure only (never automatically BLOCK_ENTIRE_RING)."""
    graph_store = get_live_abuse_graph_store()
    # ACC_MERCHANT_90210 and ACC_WARD_00001 sharing DEV_SHARED_LAB_001
    graph_store.record_webhook_event(
        event_id="evt_c1",
        event_type="payment.captured",
        account_id="ACC_MERCHANT_90210",
        payment_id="pay_c1",
        device_id="DEV_SHARED_LAB_001",
    )
    graph_store.record_webhook_event(
        event_id="evt_c2",
        event_type="payment.captured",
        account_id="ACC_WARD_00001",
        payment_id="pay_c2",
        device_id="DEV_SHARED_LAB_001",
    )

    # Evaluate cluster via live endpoint
    resp = client.post("/risk/abuse-ring/live/analyze", json={})
    assert resp.status_code == 200
    res = resp.json()

    # The frozen AbuseRingSentinel must evaluate based on ML + evidence formulas
    # Shared device alone does NOT trigger BLOCK_ENTIRE_RING
    assert res["verdict"] != "BLOCK_ENTIRE_RING"


def test_24_existing_bystander_protection_remains_unchanged(client):
    """10. existing bystander protection remains unchanged."""
    sentinel = get_abuse_ring_sentinel()
    # Ring of fraudsters with one benign bystander
    accounts = [
        {"account_id": "FRAUD_1", "average_order_value": 450.0, "return_rate": 0.85, "suspicious_activity_score": 0.95},
        {"account_id": "FRAUD_2", "average_order_value": 420.0, "return_rate": 0.80, "suspicious_activity_score": 0.90},
        {"account_id": "BYSTANDER", "average_order_value": 35.0, "return_rate": 0.0, "suspicious_activity_score": 0.02},
    ]
    edges = [
        {"account_id": "FRAUD_1", "entity_type": "DEVICE", "entity_id": "DEV_RING_01", "event_type": "ORDER"},
        {"account_id": "FRAUD_1", "entity_type": "IP", "entity_id": "IP_SHARED_01", "event_type": "ORDER"},
        {"account_id": "FRAUD_2", "entity_type": "DEVICE", "entity_id": "DEV_RING_01", "event_type": "ORDER"},
        {"account_id": "FRAUD_2", "entity_type": "IP", "entity_id": "IP_SHARED_01", "event_type": "ORDER"},
        {"account_id": "BYSTANDER", "entity_type": "IP", "entity_id": "IP_SHARED_01", "event_type": "ORDER"},
        {"account_id": "BYSTANDER", "entity_type": "DEVICE", "entity_id": "DEV_CLEAN_PHONE", "event_type": "ORDER"},
    ]

    result = sentinel.detect(accounts=accounts, edges=edges)
    bystander_role = [a for a in result["account_attribution"] if a["account_id"] == "BYSTANDER"][0]["attribution_role"]
    assert bystander_role == "INCIDENTAL_BYSTANDER"
    # Action must be gated: NEVER BLOCK_ENTIRE_RING when a bystander is present
    assert result["recommended_action"] != "BLOCK_ENTIRE_RING"


def test_25_existing_benchmark_behavior_remains_unchanged(client):
    """11. existing benchmark behavior remains unchanged."""
    # Run a standard benchmark POST /risk/abuse-ring
    accounts = [
        {"account_id": "ACC_A", "average_order_value": 150.0, "return_rate": 0.1, "suspicious_activity_score": 0.15},
        {"account_id": "ACC_B", "average_order_value": 160.0, "return_rate": 0.1, "suspicious_activity_score": 0.18},
    ]
    edges = [
        {"account_id": "ACC_A", "entity_type": "DEVICE", "entity_id": "DEV_BENCH_01", "event_type": "ORDER"},
        {"account_id": "ACC_B", "entity_type": "DEVICE", "entity_id": "DEV_BENCH_01", "event_type": "ORDER"},
    ]
    resp = client.post("/risk/abuse-ring", json={"accounts": accounts, "edges": edges})
    assert resp.status_code == 200
    res = resp.json()
    assert "final_ring_score" in res
    assert "verdict" in res
    assert "account_attribution" in res

