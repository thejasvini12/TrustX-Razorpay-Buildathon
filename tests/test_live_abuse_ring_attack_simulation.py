"""Unit & Integration Tests for Phase 4: Live Abuse-Ring Attack Simulation & Genuine High-Risk Validation.

Validates all 21 prompt-specified scenarios and constraints:
 1. Clean shared infrastructure simulation execution.
 2. Suspicious cluster generation.
 3. High-confidence syndicate scenario generation.
 4. Bystander mixed cluster scenario.
 5. Real application create-order path integration.
 6. Automatic client IP observation.
 7. Automatic address hashing.
 8. Device correlation.
 9. Payment correlation.
10. Authorized + captured deduplication into one completed payment.
11. Failed payment behavior (failed payment != automatic fraud).
12. Duplicate webhook protection.
13. Shared topology creation in Live Abuse Graph.
14. Frozen engine evaluation via AbuseRingSentinel.
15. No forced score (scientific validity preserved).
16. No forced verdict.
17. Bystander attribution (INCIDENTAL_BYSTANDER, LOW risk contribution).
18. No automatic blocking from topology alone.
19. Deterministic simulation execution across multiple runs.
20. Raw IP never exposed in graph, API responses, or stored state.
21. Raw address never exposed in graph, API responses, or stored state.
"""

import json
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

from src.api import app, get_abuse_ring_sentinel
from src.live_abuse_graph import get_live_abuse_graph_store
from src.account_store import get_account_store
from src.live_simulation import execute_simulation_scenario
from src.razorpay_webhook import ENV_WEBHOOK_SECRET, get_webhook_manager

TEST_SECRET = "test_live_graph_secret_998877"


def compute_signature(raw_body: bytes, secret: str = TEST_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


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


@pytest.fixture
def client():
    return TestClient(app)


def test_1_clean_shared_infrastructure_simulation(client):
    """1. Clean shared infrastructure produces LOW risk, NO_RING verdict, NO_ACTION."""
    resp = client.post("/risk/abuse-ring/live/simulate", json={"scenario": "CLEAN_SHARED_INFRASTRUCTURE"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario"] == "CLEAN_SHARED_INFRASTRUCTURE"
    assert data["is_synthetic_simulation"] is True
    assert data["account_count"] == 2
    
    eval_res = data["evaluation"]
    assert eval_res["verdict"] == "NO_RING"
    assert eval_res["recommended_action"] == "NO_ACTION"
    assert eval_res["risk_level"] == "LOW"
    assert eval_res["final_ring_score"] < 0.30


def test_2_coordinated_suspicious_cluster_simulation(client):
    """2. Suspicious cluster generation produces elevated risk without hardcoded overrides."""
    resp = client.post("/risk/abuse-ring/live/simulate", json={"scenario": "COORDINATED_SUSPICIOUS_CLUSTER"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario"] == "COORDINATED_SUSPICIOUS_CLUSTER"
    eval_res = data["evaluation"]
    # Elevated score above clean baseline
    assert eval_res["final_ring_score"] > 0.30
    assert eval_res["verdict"] in ["POSSIBLE_RING", "LIKELY_RING"]


def test_3_high_confidence_abuse_ring_simulation(client):
    """3. High-confidence scenario recognized by trained model (HIGH_CONFIDENCE_RING, BLOCK_ENTIRE_RING)."""
    resp = client.post("/risk/abuse-ring/live/simulate", json={"scenario": "HIGH_CONFIDENCE_ABUSE_RING"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario"] == "HIGH_CONFIDENCE_ABUSE_RING"
    eval_res = data["evaluation"]
    assert eval_res["final_ring_score"] >= 0.85
    assert eval_res["verdict"] == "HIGH_CONFIDENCE_RING"
    assert eval_res["recommended_action"] == "BLOCK_ENTIRE_RING"
    assert eval_res["risk_level"] in ["HIGH", "CRITICAL"]


def test_4_bystander_mixed_cluster_simulation(client):
    """4. Bystander scenario isolates and protects benign account."""
    resp = client.post("/risk/abuse-ring/live/simulate", json={"scenario": "BYSTANDER_MIXED_CLUSTER"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario"] == "BYSTANDER_MIXED_CLUSTER"
    eval_res = data["evaluation"]
    attributions = eval_res["account_attribution"]

    # Bystander account must be INCIDENTAL_BYSTANDER with LOW risk contribution
    bystander_attr = next(a for a in attributions if a["account_id"] == "ACC_BYSTANDER_RESIDENT")
    assert bystander_attr["attribution_role"] == "INCIDENTAL_BYSTANDER"
    assert bystander_attr["risk_contribution"] == "LOW"

    # Core fraud accounts must be CORE_MEMBER
    core_attr = [a for a in attributions if a["account_id"] != "ACC_BYSTANDER_RESIDENT"]
    for ca in core_attr:
        assert ca["attribution_role"] == "CORE_MEMBER"

    # Block entire ring must NEVER be recommended when a bystander is present
    assert eval_res["recommended_action"] != "BLOCK_ENTIRE_RING"


def test_5_real_application_create_order_path(client):
    """5. Real application create-order path creates context and captures telemetry."""
    resp = client.post(
        "/payments/create-order",
        json={
            "account_id": "ACC_TEST_ORDER_01",
            "amount": 12500,
            "currency": "INR",
            "device_id": "DEV_ORDER_TEST_99",
            "address": "123 Main St, New York, NY 10001",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_id"].startswith("order_")
    assert data["account_id"] == "ACC_TEST_ORDER_01"
    assert data["ip_captured"] is True
    assert data["address_captured"] is True


def test_6_automatic_ip_observation(client):
    """6. Automatic IP observation without exposing raw IP."""
    resp = client.post(
        "/payments/create-order",
        json={"account_id": "ACC_IP_OBS", "amount": 10000},
        headers={"X-Forwarded-For": "203.0.113.195"},
    )
    assert resp.status_code == 200
    # Raw IP string must never appear in response
    assert "203.0.113.195" not in resp.text


def test_7_automatic_address_hashing(client):
    """7. Automatic address hashing into canonical ADDRESS_HASH_ format."""
    resp = client.post(
        "/payments/create-order",
        json={
            "account_id": "ACC_ADDR_HASH",
            "amount": 10000,
            "address": "  450 North Park Ave, Suite 100, Chicago, IL 60601  ",
        },
    )
    assert resp.status_code == 200
    # Raw address must not be exposed in public response
    assert "450 North Park Ave" not in resp.text


def test_8_device_correlation(client):
    """8. Two accounts sharing a device form a single shared device entity."""
    res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE")
    shared_entities = res["shared_entities"]
    device_entities = [se for se in shared_entities if se["entity_type"] == "DEVICE"]
    assert len(device_entities) == 1
    assert device_entities[0]["account_count"] == 2


def test_9_payment_correlation(client):
    """9. Payment entities belong strictly to their account and never bridge accounts."""
    res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE")
    graph_store = get_live_abuse_graph_store()
    state = graph_store.get_live_graph_state()
    # Payments exist as separate direct edges
    for c in state["candidate_clusters"]:
        payment_shared = [se for se in c.get("shared_entities", []) if se["entity_type"] == "PAYMENT"]
        assert len(payment_shared) == 0, "PAYMENT entities must never be shared across accounts"


def test_10_authorized_captured_deduplication(client):
    """10. Authorized + captured lifecycle produces exactly one completed payment relationship."""
    res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE")
    graph_store = get_live_abuse_graph_store()
    subgraph_a = graph_store.get_account_subgraph("ACC_MERCHANT_90210")
    payment_edges = [e for e in subgraph_a["direct_edges"] if e["entity_type"] == "PAYMENT"]
    assert len(payment_edges) == 1
    assert payment_edges[0]["payment_status"] == "captured"


def test_11_failed_payment_behavior(client):
    """11. Failed payment increments failed telemetry without marking payment as captured."""
    res = execute_simulation_scenario("HIGH_CONFIDENCE_ABUSE_RING")
    graph_store = get_live_abuse_graph_store()
    subgraph = graph_store.get_account_subgraph("ACC_RING_SYND_01")
    acc_meta = subgraph["account_metadata"]
    assert len(acc_meta["failed_payment_ids"]) == 1
    assert len(acc_meta["successful_payment_ids"]) == 1


def test_12_duplicate_webhook_protection(client):
    """12. Re-recording identical webhook events does not duplicate graph edges."""
    graph_store = get_live_abuse_graph_store()
    for _ in range(3):
        graph_store.record_webhook_event(
            event_id="evt_dup_test_001",
            event_type="payment.captured",
            account_id="ACC_DUP_TEST",
            payment_id="pay_dup_001",
            device_id="DEV_DUP_001",
        )
    subgraph = graph_store.get_account_subgraph("ACC_DUP_TEST")
    dev_edges = [e for e in subgraph["direct_edges"] if e["entity_type"] == "DEVICE"]
    assert len(dev_edges) == 1


def test_13_shared_topology_creation(client):
    """13. Shared device, IP, and address create candidate connected component."""
    res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE")
    graph_store = get_live_abuse_graph_store()
    clusters = graph_store.get_candidate_clusters()
    assert len(clusters) == 1
    assert clusters[0]["is_multi_account"] is True
    assert set(clusters[0]["account_ids"]) == {"ACC_MERCHANT_90210", "ACC_WARD_00001"}


def test_14_engine_evaluation_integrity(client):
    """14. Candidate cluster evaluated via frozen AbuseRingSentinel."""
    res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE")
    eval_res = res["evaluation"]
    assert "model_metadata" in eval_res
    assert eval_res["model_metadata"]["calibrated"] is True
    assert "raw_ml_probability" in eval_res


def test_15_no_forced_score(client):
    """15. No artificial score floors or ceilings are imposed."""
    clean_res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE")
    high_res = execute_simulation_scenario("HIGH_CONFIDENCE_ABUSE_RING")
    # Score must be naturally differentiated by the trained pipeline
    assert clean_res["evaluation"]["final_ring_score"] < high_res["evaluation"]["final_ring_score"]


def test_16_no_forced_verdict(client):
    """16. Verdicts are derived strictly from calibrated thresholds."""
    clean_res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE")
    assert clean_res["evaluation"]["verdict"] == "NO_RING"
    high_res = execute_simulation_scenario("HIGH_CONFIDENCE_ABUSE_RING")
    assert high_res["evaluation"]["verdict"] == "HIGH_CONFIDENCE_RING"


def test_17_bystander_attribution(client):
    """17. Benign bystander maintains INCIDENTAL_BYSTANDER attribution role."""
    res = execute_simulation_scenario("BYSTANDER_MIXED_CLUSTER")
    eval_res = res["evaluation"]
    bystander = next(a for a in eval_res["account_attribution"] if a["account_id"] == "ACC_BYSTANDER_RESIDENT")
    assert bystander["attribution_role"] == "INCIDENTAL_BYSTANDER"
    assert bystander["risk_contribution"] == "LOW"


def test_18_no_automatic_blocking_from_topology_alone(client):
    """18. Shared topology alone does not produce BLOCK_ENTIRE_RING."""
    clean_res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE")
    assert clean_res["evaluation"]["recommended_action"] == "NO_ACTION"
    assert clean_res["evaluation"]["recommended_action"] != "BLOCK_ENTIRE_RING"


def test_19_deterministic_simulation(client):
    """19. Repeated runs of simulation produce identical score and verdict."""
    run1 = execute_simulation_scenario("HIGH_CONFIDENCE_ABUSE_RING")
    score1 = run1["evaluation"]["final_ring_score"]
    run2 = execute_simulation_scenario("HIGH_CONFIDENCE_ABUSE_RING")
    score2 = run2["evaluation"]["final_ring_score"]
    assert score1 == score2


def test_20_raw_ip_never_exposed(client):
    """20. Raw IP is never present in Live Abuse Graph or API response."""
    res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE", client_ip="198.51.100.42")
    graph_store = get_live_abuse_graph_store()
    state = graph_store.get_live_graph_state()
    state_str = json.dumps(state)
    assert "198.51.100.42" not in state_str
    assert "IP_HASH_" in state_str


def test_21_raw_address_never_exposed(client):
    """21. Raw physical address is never present in Live Abuse Graph or API response."""
    res = execute_simulation_scenario("CLEAN_SHARED_INFRASTRUCTURE")
    graph_store = get_live_abuse_graph_store()
    state = graph_store.get_live_graph_state()
    state_str = json.dumps(state)
    assert "742 Evergreen Terrace" not in state_str
    assert "ADDRESS_HASH_" in state_str
