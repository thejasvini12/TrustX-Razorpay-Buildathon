"""Comprehensive API tests for POST /risk/abuse-ring endpoint."""

import pytest
import pandas as pd
from fastapi.testclient import TestClient

from src.api import app, get_abuse_ring_sentinel
from src.train_abuse_ring import simulate_daisy_chain_ood_clusters


@pytest.fixture(scope="module")
def client():
    """Create a FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture(scope="module")
def frozen_raw_data():
    """Load frozen raw datasets for realistic payload construction."""
    df_acc = pd.read_csv("data/ring_accounts.csv")
    df_edg = pd.read_csv("data/ring_entity_edges.csv")
    df_cls = pd.read_csv("data/ring_clusters.csv")
    return df_acc, df_edg, df_cls


def get_cluster_payload(df_acc, df_edg, df_cls, cluster_id):
    """Construct JSON-serializable request payload for a specific cluster."""
    accs = df_acc[df_acc["cluster_id"] == cluster_id].to_dict(orient="records")
    acc_ids = {a["account_id"] for a in accs}
    edgs = df_edg[df_edg["account_id"].isin(acc_ids)].to_dict(orient="records")
    meta = df_cls[df_cls["cluster_id"] == cluster_id].to_dict(orient="records")[0]
    return {
        "accounts": accs,
        "edges": edgs,
        "cluster_metadata": meta,
    }


def test_api_1_valid_positive_abuse_ring(client, frozen_raw_data):
    """Test 1: POST /risk/abuse-ring on Synthetic Identity Ring."""
    df_acc, df_edg, df_cls = frozen_raw_data
    synth_cid = df_cls[df_cls["cluster_type"] == "SYNTHETIC_IDENTITY_RING"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, synth_cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is True
    assert data["raw_ml_probability"] > 0.70
    assert data["verdict"] == "HIGH_CONFIDENCE_RING"
    assert data["risk_level"] == "CRITICAL"
    assert data["recommended_action"] == "BLOCK_ENTIRE_RING"


def test_api_2_valid_benign_campus_shared_ip(client, frozen_raw_data):
    """Test 2: POST /risk/abuse-ring on Campus Shared IP."""
    df_acc, df_edg, df_cls = frozen_raw_data
    campus_cid = df_cls[df_cls["cluster_type"] == "CAMPUS_SHARED_IP"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, campus_cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is False
    assert data["verdict"] == "NO_RING"
    assert data["risk_level"] == "LOW"
    assert data["recommended_action"] == "NO_ACTION"


def test_api_3_apartment_address(client, frozen_raw_data):
    """Test 3: POST /risk/abuse-ring on Apartment Building Address."""
    df_acc, df_edg, df_cls = frozen_raw_data
    apt_cid = df_cls[df_cls["cluster_type"] == "APARTMENT_BUILDING_ADDR"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, apt_cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is False
    assert data["verdict"] == "NO_RING"


def test_api_4_family_shared_card(client, frozen_raw_data):
    """Test 4: POST /risk/abuse-ring on Family Household sharing card/address."""
    df_acc, df_edg, df_cls = frozen_raw_data
    fam_cid = df_cls[df_cls["cluster_type"] == "FAMILY_HOUSEHOLD"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, fam_cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is False
    assert data["verdict"] == "NO_RING"


def test_api_5_public_kiosk(client, frozen_raw_data):
    """Test 5: POST /risk/abuse-ring on Public Kiosk Device."""
    df_acc, df_edg, df_cls = frozen_raw_data
    kiosk_cid = df_cls[df_cls["cluster_type"] == "PUBLIC_KIOSK_DEVICE"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, kiosk_cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is False
    assert data["verdict"] == "NO_RING"


def test_api_6_partial_network_overlap(client, frozen_raw_data):
    """Test 6: POST /risk/abuse-ring on Partial Network Overlap."""
    df_acc, df_edg, df_cls = frozen_raw_data
    part_cid = df_cls[df_cls["cluster_type"] == "PARTIAL_NETWORK_OVERLAP"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, part_cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is False
    assert data["verdict"] == "NO_RING"


def test_api_7_slow_drip_ood_ring(client, frozen_raw_data):
    """Test 7: POST /risk/abuse-ring on Slow-Drip Coordinated Ring."""
    df_acc, df_edg, df_cls = frozen_raw_data
    slow_cid = df_cls[df_cls["cluster_type"] == "SLOW_DRIP_COORDINATED_RING"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, slow_cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is True
    assert data["raw_ml_probability"] > 0.70


def test_api_8_daisy_chain_ood_ring(client):
    """Test 8: POST /risk/abuse-ring on synthetic Daisy-Chain Mule Ring."""
    ood_accs, ood_edgs, ood_cls = simulate_daisy_chain_ood_clusters(num_clusters=1, chain_length=12, seed=888)
    payload = {
        "accounts": ood_accs.to_dict(orient="records"),
        "edges": ood_edgs.to_dict(orient="records"),
        "cluster_metadata": ood_cls.iloc[0].to_dict(),
    }

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is True
    assert data["raw_ml_probability"] > 0.70


def test_api_9_singleton(client):
    """Test 9: POST /risk/abuse-ring on single account returns NO_RING."""
    payload = {
        "accounts": [
            {
                "account_id": "ACC_SOLO_99",
                "created_at": "2026-01-01T00:00:00Z",
                "average_order_value": 85.0,
                "return_rate": 0.0,
                "suspicious_activity_score": 0.05,
            }
        ],
        "edges": [
            {"account_id": "ACC_SOLO_99", "entity_type": "DEVICE", "entity_id": "DEV_SOLO_99"}
        ],
    }
    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is False
    assert data["final_ring_score"] == 0.0
    assert data["cluster_size"] == 1
    assert data["recommended_action"] == "NO_ACTION"


def test_api_10_empty_accounts(client):
    """Test 10: POST /risk/abuse-ring with empty accounts returns safe empty response."""
    payload = {"accounts": [], "edges": []}
    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ring_detected"] is False
    assert data["final_ring_score"] == 0.0
    assert data["verdict"] == "NO_RING"


def test_api_11_zero_edges(client):
    """Test 11: POST /risk/abuse-ring with accounts but zero edges."""
    payload = {
        "accounts": [
            {"account_id": "ACC_1", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
            {"account_id": "ACC_2", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
        ],
        "edges": [],
    }
    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert data["confidence"] == "LOW"


def test_api_12_malformed_timestamp(client):
    """Test 12: POST /risk/abuse-ring with invalid timestamps does NOT trigger rapid burst."""
    payload = {
        "accounts": [
            {"account_id": "ACC_1", "created_at": "INVALID_DATE_ABC", "average_order_value": 100.0, "return_rate": 0.0, "suspicious_activity_score": 0.9},
            {"account_id": "ACC_2", "created_at": "NOT_A_VALID_DATE", "average_order_value": 100.0, "return_rate": 0.0, "suspicious_activity_score": 0.9},
            {"account_id": "ACC_3", "created_at": None, "average_order_value": 100.0, "return_rate": 0.0, "suspicious_activity_score": 0.9},
            {"account_id": "ACC_4", "created_at": "2026-99-99", "average_order_value": 100.0, "return_rate": 0.0, "suspicious_activity_score": 0.9},
        ],
        "edges": [
            {"account_id": f"ACC_{k+1}", "entity_type": "DEVICE", "entity_id": "DEV_BOT_1"} for k in range(4)
        ],
    }
    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Rapid burst must not trigger
    adj_codes = [a["code"] for a in data["evidence_adjustments"]["positive_adjustments"]]
    assert "CORROBORATE_RAPID_BURST" not in adj_codes


def test_api_13_missing_behavioral_data(client):
    """Test 13: POST /risk/abuse-ring handles missing behavioral fields gracefully."""
    payload = {
        "accounts": [
            {"account_id": "ACC_1"},
            {"account_id": "ACC_2"},
        ],
        "edges": [
            {"account_id": "ACC_1", "entity_type": "IP", "entity_id": "IP_SHARED"},
            {"account_id": "ACC_2", "entity_type": "IP", "entity_id": "IP_SHARED"},
        ],
    }
    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert data["confidence"] == "LOW"


def test_api_14_unknown_entity_type(client):
    """Test 14: Unknown entity types are safely ignored with diagnostic note."""
    payload = {
        "accounts": [
            {"account_id": "ACC_1", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
            {"account_id": "ACC_2", "created_at": "2026-01-01T01:00:00Z", "average_order_value": 60.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
        ],
        "edges": [
            {"account_id": "ACC_1", "entity_type": "UNKNOWN_BLUETOOTH_ID", "entity_id": "BT_999"},
            {"account_id": "ACC_1", "entity_type": "IP", "entity_id": "IP_1"},
            {"account_id": "ACC_2", "entity_type": "IP", "entity_id": "IP_1"},
        ],
    }
    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert any("UNKNOWN_ENTITY_TYPE: UNKNOWN_BLUETOOTH_ID ignored" in d for d in data.get("diagnostics", []))


def test_api_15_invalid_json_schema(client):
    """Test 15: Malformed JSON types (e.g. accounts as string) returns 422 validation error."""
    payload = {
        "accounts": "THIS_SHOULD_BE_A_LIST",
        "edges": [],
    }
    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 422


def test_api_16_probability_and_score_bounds(client, frozen_raw_data):
    """Test 16: Probability and final score are bounded in [0.0, 1.0]."""
    df_acc, df_edg, df_cls = frozen_raw_data
    for cid in df_cls["cluster_id"].head(5):
        payload = get_cluster_payload(df_acc, df_edg, df_cls, cid)
        response = client.post("/risk/abuse-ring", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["raw_ml_probability"] <= 1.0
        assert 0.0 <= data["final_ring_score"] <= 1.0


def test_api_17_response_schema_completeness(client, frozen_raw_data):
    """Test 17: Verify complete response schema."""
    df_acc, df_edg, df_cls = frozen_raw_data
    cid = df_cls.iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    required_keys = [
        "cluster_id", "ring_detected", "raw_ml_probability", "model_prediction",
        "model_threshold", "evidence_adjustments", "final_ring_score", "risk_level",
        "verdict", "evidence_quality", "confidence", "cluster_size", "ring_factors",
        "mitigating_factors", "evidence_summary", "decision_reasoning",
        "account_attribution", "recommended_action", "model_metadata",
    ]
    for k in required_keys:
        assert k in data, f"Missing key '{k}' in API response"


def test_api_18_model_threshold_remains_050(client, frozen_raw_data):
    """Test 18: Model threshold returned in response is exactly 0.50."""
    df_acc, df_edg, df_cls = frozen_raw_data
    cid = df_cls.iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["model_threshold"] == 0.50


def test_api_19_bystander_protection(client, frozen_raw_data):
    """Test 19: Presence of bystander prevents BLOCK_ENTIRE_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    synth_cid = df_cls[df_cls["cluster_type"] == "SYNTHETIC_IDENTITY_RING"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, synth_cid)

    # Add bystander account
    payload["accounts"].append({
        "account_id": "ACC_BYSTANDER_API",
        "created_at": "2025-06-01T00:00:00Z",
        "average_order_value": 35.0,
        "return_rate": 0.0,
        "suspicious_activity_score": 0.02,
    })
    shared_ip = [e["entity_id"] for e in payload["edges"] if e["entity_type"] == "IP"][0]
    payload["edges"].append({"account_id": "ACC_BYSTANDER_API", "entity_type": "IP", "entity_id": shared_ip})
    payload["edges"].append({"account_id": "ACC_BYSTANDER_API", "entity_type": "DEVICE", "entity_id": "DEV_CLEAN_1"})

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["recommended_action"] != "BLOCK_ENTIRE_RING"
    assert data["recommended_action"] in ["REVIEW_ACCOUNTS", "RESTRICT_SELECTED_ACCOUNT"]


def test_api_20_block_entire_ring_gating(client, frozen_raw_data):
    """Test 20: Pure synthetic ring executes BLOCK_ENTIRE_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    synth_cid = df_cls[df_cls["cluster_type"] == "SYNTHETIC_IDENTITY_RING"].iloc[0]["cluster_id"]
    payload = get_cluster_payload(df_acc, df_edg, df_cls, synth_cid)

    response = client.post("/risk/abuse-ring", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["verdict"] == "HIGH_CONFIDENCE_RING"
    assert data["confidence"] == "HIGH"
    assert data["recommended_action"] == "BLOCK_ENTIRE_RING"


def test_api_21_end_to_end_parity(client, frozen_raw_data):
    """Test 21: Verify direct Sentinel output and API response are identical (zero decision drift)."""
    df_acc, df_edg, df_cls = frozen_raw_data
    sentinel = get_abuse_ring_sentinel()

    # 1. Positive Scenario
    synth_cid = df_cls[df_cls["cluster_type"] == "SYNTHETIC_IDENTITY_RING"].iloc[0]["cluster_id"]
    payload_pos = get_cluster_payload(df_acc, df_edg, df_cls, synth_cid)

    sentinel_res_pos = sentinel.detect(
        accounts=payload_pos["accounts"],
        edges=payload_pos["edges"],
        cluster_metadata=payload_pos["cluster_metadata"],
    )
    api_res_pos = client.post("/risk/abuse-ring", json=payload_pos).json()

    assert api_res_pos["raw_ml_probability"] == sentinel_res_pos["raw_ml_probability"]
    assert api_res_pos["final_ring_score"] == sentinel_res_pos["final_ring_score"]
    assert api_res_pos["verdict"] == sentinel_res_pos["verdict"]
    assert api_res_pos["recommended_action"] == sentinel_res_pos["recommended_action"]

    # 2. Benign Scenario
    campus_cid = df_cls[df_cls["cluster_type"] == "CAMPUS_SHARED_IP"].iloc[0]["cluster_id"]
    payload_benign = get_cluster_payload(df_acc, df_edg, df_cls, campus_cid)

    sentinel_res_benign = sentinel.detect(
        accounts=payload_benign["accounts"],
        edges=payload_benign["edges"],
        cluster_metadata=payload_benign["cluster_metadata"],
    )
    api_res_benign = client.post("/risk/abuse-ring", json=payload_benign).json()

    assert api_res_benign["raw_ml_probability"] == sentinel_res_benign["raw_ml_probability"]
    assert api_res_benign["final_ring_score"] == sentinel_res_benign["final_ring_score"]
    assert api_res_benign["verdict"] == sentinel_res_benign["verdict"]
    assert api_res_benign["recommended_action"] == sentinel_res_benign["recommended_action"]
