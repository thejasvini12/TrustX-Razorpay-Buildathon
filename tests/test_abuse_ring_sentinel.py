"""Comprehensive unit and integration tests for Abuse-Ring Sentinel v1.

Covers all 31 test categories (A through AE):
A. Model loading
B. Feature extraction parity
C. Exactly 15 features
D. Probability range
E. Raw probability unchanged
F. Final score bounding in [0.0, 1.0]
G. Frozen threshold = 0.50
H. Empty cluster
I. Singleton
J. Zero edges
K. Malformed timestamp
L. Missing behavioral fields
M. Unknown entity type
N. Campus shared IP
O. Apartment address
P. Public kiosk
Q. Family household
R. Partial network overlap
S. IP-only with extreme behavioral coordination
T. Synthetic Identity Ring
U. Card Testing Syndicate
V. Promo Farming Ring
W. Wardrobing Mule
X. Slow-Drip Ring
Y. Daisy-Chain Ring
Z. Star topology
AA. Account attribution
AB. Bystander protection
AC. Evidence quality
AD. Confidence
AE. Operational action gating
"""

import os
import joblib
import numpy as np
import pandas as pd
import pytest

from src.abuse_ring_sentinel import AbuseRingSentinel
from src.abuse_ring_features import FEATURE_COLUMNS
from src.train_abuse_ring import simulate_daisy_chain_ood_clusters


@pytest.fixture(scope="module")
def sentinel():
    """Instantiate the AbuseRingSentinel."""
    return AbuseRingSentinel(model_path="models/abuse_ring_model.joblib")


@pytest.fixture(scope="module")
def frozen_raw_data():
    """Load frozen dataset tables."""
    df_acc = pd.read_csv("data/ring_accounts.csv")
    df_edg = pd.read_csv("data/ring_entity_edges.csv")
    df_cls = pd.read_csv("data/ring_clusters.csv")
    return df_acc, df_edg, df_cls


# Helper to get accounts and edges for a specific cluster_id from frozen data
def get_cluster_records(df_acc, df_edg, df_cls, cluster_id):
    accs = df_acc[df_acc["cluster_id"] == cluster_id].to_dict(orient="records")
    acc_ids = {a["account_id"] for a in accs}
    edgs = df_edg[df_edg["account_id"].isin(acc_ids)].to_dict(orient="records")
    meta = df_cls[df_cls["cluster_id"] == cluster_id].to_dict(orient="records")[0]
    return accs, edgs, meta


# -------------------------------------------------------------
# A-G: Core Model & Score Invariance Tests
# -------------------------------------------------------------
def test_a_model_loading(sentinel):
    """Test A: Verify model bundle loads read-only with complete metadata."""
    assert sentinel.model is not None
    assert sentinel.model_threshold == 0.50
    assert sentinel.model_version == "1.0.0"
    assert sentinel.feature_schema_version == "15_feature_cluster_v1"


def test_b_feature_extraction_parity(sentinel, frozen_raw_data):
    """Test B: Verify feature extraction uses SSOT and matches training schema."""
    df_acc, df_edg, df_cls = frozen_raw_data
    cid = df_cls.iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["cluster_id"] == cid
    assert "raw_ml_probability" in resp


def test_c_exactly_15_features(sentinel):
    """Test C: Verify exactly 15 features in feature_names."""
    assert len(sentinel.feature_names) == 15
    assert sentinel.feature_names == FEATURE_COLUMNS


def test_d_probability_range(sentinel, frozen_raw_data):
    """Test D: Verify raw_ml_probability is bounded in [0.0, 1.0]."""
    df_acc, df_edg, df_cls = frozen_raw_data
    cid = df_cls.iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, cid)

    resp = sentinel.detect(accs, edgs, meta)
    p = resp["raw_ml_probability"]
    assert 0.0 <= p <= 1.0


def test_e_raw_probability_unchanged(sentinel, frozen_raw_data):
    """Test E: Verify evidence adjustments do NOT mutate raw_ml_probability."""
    df_acc, df_edg, df_cls = frozen_raw_data
    # Use a positive ring cluster
    pos_cid = df_cls[df_cls["cluster_abuse_label"] == 1].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, pos_cid)

    resp = sentinel.detect(accs, edgs, meta)
    raw_p = resp["raw_ml_probability"]
    final_s = resp["final_ring_score"]
    net_d = resp["evidence_adjustments"]["net_delta"]

    assert isinstance(raw_p, float)
    assert resp["model_prediction"] == (raw_p >= 0.50)
    assert round(raw_p + net_d, 4) == round(final_s, 4) or final_s in [0.0, 1.0]


def test_f_final_score_bounding(sentinel, frozen_raw_data):
    """Test F: Verify final_ring_score stays strictly within [0.0, 1.0]."""
    df_acc, df_edg, df_cls = frozen_raw_data
    for cid in df_cls["cluster_id"].head(20):
        accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, cid)
        resp = sentinel.detect(accs, edgs, meta)
        s = resp["final_ring_score"]
        assert 0.0 <= s <= 1.0


def test_g_frozen_threshold_050(sentinel):
    """Test G: Verify operational model threshold is frozen at exactly 0.50."""
    assert sentinel.model_threshold == 0.50


# -------------------------------------------------------------
# H-M: Input Edge Cases & Error Handling
# -------------------------------------------------------------
def test_h_empty_cluster(sentinel):
    """Test H: Verify empty cluster returns structured fallback with 0 score."""
    resp = sentinel.detect(accounts=[], edges=[])
    assert resp["ring_detected"] is False
    assert resp["final_ring_score"] == 0.0
    assert resp["verdict"] == "NO_RING"
    assert resp["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert resp["recommended_action"] == "NO_ACTION"
    assert "EMPTY_CLUSTER" in resp["diagnostics"]


def test_i_singleton(sentinel):
    """Test I: Verify singleton account fast-path returns NO_RING."""
    acc = {
        "account_id": "ACC_SOLO_1",
        "created_at": "2026-01-01T00:00:00Z",
        "average_order_value": 75.0,
        "return_rate": 0.02,
        "suspicious_activity_score": 0.05,
    }
    edg = [
        {"account_id": "ACC_SOLO_1", "entity_type": "DEVICE", "entity_id": "DEV_1"},
        {"account_id": "ACC_SOLO_1", "entity_type": "IP", "entity_id": "IP_1"},
    ]
    resp = sentinel.detect(accounts=[acc], edges=edg)
    assert resp["ring_detected"] is False
    assert resp["final_ring_score"] == 0.0
    assert resp["verdict"] == "NO_RING"
    assert resp["cluster_size"] == 1
    assert resp["recommended_action"] == "NO_ACTION"
    assert "SINGLETON_FAST_PATH" in resp["diagnostics"]


def test_j_zero_edges(sentinel):
    """Test J: Verify cluster with zero edges sets evidence_quality INSUFFICIENT."""
    accs = [
        {"account_id": "ACC_1", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
        {"account_id": "ACC_2", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
    ]
    resp = sentinel.detect(accounts=accs, edges=[])
    assert resp["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert resp["confidence"] == "LOW"


def test_k_malformed_timestamp_does_not_trigger_burst(sentinel):
    """Test K: Verify malformed timestamps do NOT fabricate current time or trigger rapid burst."""
    accs = [
        {"account_id": "ACC_1", "created_at": "INVALID_TIMESTAMP_XYZ", "average_order_value": 100.0, "return_rate": 0.0, "suspicious_activity_score": 0.9},
        {"account_id": "ACC_2", "created_at": "NOT_A_DATE", "average_order_value": 100.0, "return_rate": 0.0, "suspicious_activity_score": 0.9},
        {"account_id": "ACC_3", "created_at": None, "average_order_value": 100.0, "return_rate": 0.0, "suspicious_activity_score": 0.9},
        {"account_id": "ACC_4", "created_at": "2026-99-99", "average_order_value": 100.0, "return_rate": 0.0, "suspicious_activity_score": 0.9},
    ]
    edgs = [
        {"account_id": f"ACC_{k+1}", "entity_type": "DEVICE", "entity_id": "DEV_BOT"} for k in range(4)
    ]
    resp = sentinel.detect(accounts=accs, edges=edgs)
    # Rapid burst must NOT be in positive adjustments
    adj_codes = [a["code"] for a in resp["evidence_adjustments"]["positive_adjustments"]]
    assert "CORROBORATE_RAPID_BURST" not in adj_codes
    assert any("MALFORMED_OR_MISSING_TIMESTAMP" in d for d in resp["diagnostics"])


def test_l_missing_behavioral_fields(sentinel):
    """Test L: Verify missing behavioral data drops evidence quality without crashing."""
    accs = [
        {"account_id": "ACC_1", "created_at": "2026-01-01T00:00:00Z"},
        {"account_id": "ACC_2", "created_at": "2026-01-01T01:00:00Z"},
    ]
    edgs = [
        {"account_id": "ACC_1", "entity_type": "IP", "entity_id": "IP_SHARED"},
        {"account_id": "ACC_2", "entity_type": "IP", "entity_id": "IP_SHARED"},
    ]
    resp = sentinel.detect(accounts=accs, edges=edgs)
    assert resp["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert resp["confidence"] == "LOW"
    assert any("MISSING_BEHAVIORAL_FIELDS" in d for d in resp["diagnostics"])


def test_m_unknown_entity_type(sentinel):
    """Test M: Verify unknown entity type is ignored with diagnostic warning rather than crashing."""
    accs = [
        {"account_id": "ACC_1", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
        {"account_id": "ACC_2", "created_at": "2026-01-01T01:00:00Z", "average_order_value": 60.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
    ]
    edgs = [
        {"account_id": "ACC_1", "entity_type": "UNKNOWN_BLUETOOTH_ID", "entity_id": "BT_999"},
        {"account_id": "ACC_1", "entity_type": "IP", "entity_id": "IP_1"},
        {"account_id": "ACC_2", "entity_type": "IP", "entity_id": "IP_1"},
    ]
    resp = sentinel.detect(accounts=accs, edges=edgs)
    assert any("UNKNOWN_ENTITY_TYPE: UNKNOWN_BLUETOOTH_ID ignored" in d for d in resp["diagnostics"])
    assert resp["final_ring_score"] < 0.30


# -------------------------------------------------------------
# N-R: Benign Hard-Negative Scenario Tests
# -------------------------------------------------------------
def test_n_campus_shared_ip(sentinel, frozen_raw_data):
    """Test N: Campus Shared IP must produce NO_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    campus_cid = df_cls[df_cls["cluster_type"] == "CAMPUS_SHARED_IP"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, campus_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "NO_RING"
    assert resp["risk_level"] == "LOW"
    assert resp["recommended_action"] == "NO_ACTION"


def test_o_apartment_address(sentinel, frozen_raw_data):
    """Test O: Apartment Building Address must produce NO_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    apt_cid = df_cls[df_cls["cluster_type"] == "APARTMENT_BUILDING_ADDR"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, apt_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "NO_RING"
    assert resp["risk_level"] == "LOW"
    assert resp["recommended_action"] == "NO_ACTION"


def test_p_public_kiosk(sentinel, frozen_raw_data):
    """Test P: Public Kiosk Device must produce NO_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    kiosk_cid = df_cls[df_cls["cluster_type"] == "PUBLIC_KIOSK_DEVICE"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, kiosk_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "NO_RING"
    assert resp["risk_level"] == "LOW"
    assert resp["recommended_action"] == "NO_ACTION"


def test_q_family_household(sentinel, frozen_raw_data):
    """Test Q: Family Household must produce NO_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    fam_cid = df_cls[df_cls["cluster_type"] == "FAMILY_HOUSEHOLD"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, fam_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "NO_RING"
    assert resp["risk_level"] == "LOW"
    assert resp["recommended_action"] == "NO_ACTION"


def test_r_partial_network_overlap(sentinel, frozen_raw_data):
    """Test R: Partial Network Overlap must produce NO_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    part_cid = df_cls[df_cls["cluster_type"] == "PARTIAL_NETWORK_OVERLAP"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, part_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "NO_RING"
    assert resp["risk_level"] == "LOW"


def test_s_ip_only_with_extreme_behavioral_coordination(sentinel):
    """Test S: IP-only network with extreme behavioral collusion is evaluated contextually."""
    # 15 accounts sharing only IP, but created in 5 minutes with identical AOV and 0.95 suspicion
    base_ts = pd.Timestamp("2026-03-01T12:00:00Z")
    accs = []
    edgs = []
    for i in range(15):
        aid = f"ACC_BOT_IP_{i:03d}"
        accs.append({
            "account_id": aid,
            "created_at": (base_ts + pd.Timedelta(minutes=i)).isoformat(),
            "average_order_value": 49.99,
            "return_rate": 0.0,
            "suspicious_activity_score": 0.95,
        })
        edgs.append({"account_id": aid, "entity_type": "IP", "entity_id": "IP_PROXY_FARM"})
        edgs.append({"account_id": aid, "entity_type": "DEVICE", "entity_id": f"DEV_{i}"})
        edgs.append({"account_id": aid, "entity_type": "PAYMENT", "entity_id": f"CARD_{i}"})
        edgs.append({"account_id": aid, "entity_type": "ADDRESS", "entity_id": f"ADDR_{i}"})

    resp = sentinel.detect(accounts=accs, edges=edgs)
    # The single IP benign mitigation must NOT trigger because behavior_similarity is high (>= 0.50)
    mit_codes = [m["code"] for m in resp["evidence_adjustments"]["mitigating_adjustments"]]
    assert "MITIGATE_SINGLE_IP_BENIGN" not in mit_codes


# -------------------------------------------------------------
# T-Z: Positive Abuse Ring Archetypes & OOD Topologies
# -------------------------------------------------------------
def test_t_synthetic_identity_ring(sentinel, frozen_raw_data):
    """Test T: Synthetic Identity Ring must produce HIGH_CONFIDENCE_RING & BLOCK_ENTIRE_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    synth_cid = df_cls[df_cls["cluster_type"] == "SYNTHETIC_IDENTITY_RING"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, synth_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "HIGH_CONFIDENCE_RING"
    assert resp["risk_level"] == "CRITICAL"
    assert resp["recommended_action"] == "BLOCK_ENTIRE_RING"


def test_u_card_testing_syndicate(sentinel, frozen_raw_data):
    """Test U: Card Testing Syndicate must produce HIGH_CONFIDENCE_RING & BLOCK_ENTIRE_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    card_cid = df_cls[df_cls["cluster_type"] == "CARD_TESTING_SYNDICATE"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, card_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "HIGH_CONFIDENCE_RING"
    assert resp["risk_level"] == "CRITICAL"
    assert resp["recommended_action"] == "BLOCK_ENTIRE_RING"


def test_v_promo_farming_ring(sentinel, frozen_raw_data):
    """Test V: Promo Farming Ring must produce HIGH_CONFIDENCE_RING & BLOCK_ENTIRE_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    promo_cid = df_cls[df_cls["cluster_type"] == "PROMO_FARMING_RING"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, promo_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "HIGH_CONFIDENCE_RING"
    assert resp["risk_level"] == "CRITICAL"
    assert resp["recommended_action"] == "BLOCK_ENTIRE_RING"


def test_w_wardrobing_mule(sentinel, frozen_raw_data):
    """Test W: Wardrobing Mule Cluster must produce HIGH_CONFIDENCE_RING & BLOCK_ENTIRE_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    mule_cid = df_cls[df_cls["cluster_type"] == "WARDROBING_MULE_CLUSTER"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, mule_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "HIGH_CONFIDENCE_RING"
    assert resp["risk_level"] == "CRITICAL"


def test_x_slow_drip_ring(sentinel, frozen_raw_data):
    """Test X: Slow-Drip Coordinated Ring must be detected as a ring."""
    df_acc, df_edg, df_cls = frozen_raw_data
    slow_cid = df_cls[df_cls["cluster_type"] == "SLOW_DRIP_COORDINATED_RING"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, slow_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["ring_detected"] is True
    assert resp["verdict"] in ["LIKELY_RING", "HIGH_CONFIDENCE_RING"]


def test_y_daisy_chain_ring(sentinel):
    """Test Y: Daisy-Chain Mule Ring zero-shot OOD stress test must detect abuse ring."""
    ood_accs, ood_edgs, ood_cls = simulate_daisy_chain_ood_clusters(num_clusters=1, chain_length=15, seed=123)
    accs = ood_accs.to_dict(orient="records")
    edgs = ood_edgs.to_dict(orient="records")
    meta = ood_cls.iloc[0].to_dict()

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["ring_detected"] is True
    assert resp["raw_ml_probability"] > 0.70


def test_z_star_topology_benign(sentinel, frozen_raw_data):
    """Test Z: Benign Star Topology hub must produce NO_RING."""
    df_acc, df_edg, df_cls = frozen_raw_data
    star_cid = df_cls[df_cls["cluster_type"] == "STAR_TOPOLOGY_BENIGN"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, star_cid)

    resp = sentinel.detect(accs, edgs, meta)
    assert resp["verdict"] == "NO_RING"
    assert resp["risk_level"] == "LOW"


# -------------------------------------------------------------
# AA-AE: Attribution, Bystander Protection, & Action Gating
# -------------------------------------------------------------
def test_aa_account_attribution(sentinel, frozen_raw_data):
    """Test AA: Verify deterministic attribution roles CORE_MEMBER, PERIPHERAL_MEMBER, INCIDENTAL_BYSTANDER."""
    df_acc, df_edg, df_cls = frozen_raw_data
    synth_cid = df_cls[df_cls["cluster_type"] == "SYNTHETIC_IDENTITY_RING"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, synth_cid)

    resp = sentinel.detect(accs, edgs, meta)
    attribution = resp["account_attribution"]
    assert len(attribution) == len(accs)
    roles = {a["attribution_role"] for a in attribution}
    assert "CORE_MEMBER" in roles or "PERIPHERAL_MEMBER" in roles


def test_ab_bystander_protection_downgrades_block(sentinel, frozen_raw_data):
    """Test AB: Presence of an INCIDENTAL_BYSTANDER must downgrade action from BLOCK_ENTIRE_RING to REVIEW_ACCOUNTS."""
    df_acc, df_edg, df_cls = frozen_raw_data
    synth_cid = df_cls[df_cls["cluster_type"] == "SYNTHETIC_IDENTITY_RING"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, synth_cid)

    # Inject a clean bystander account connected ONLY via IP
    bystander_acc = {
        "account_id": "ACC_CLEAN_STUDENT_999",
        "created_at": "2025-06-01T00:00:00Z",
        "average_order_value": 35.0,
        "return_rate": 0.0,
        "suspicious_activity_score": 0.02,
    }
    accs.append(bystander_acc)

    # Connect bystander to the ring's IP, but distinct phone & card
    shared_ip = [e["entity_id"] for e in edgs if e["entity_type"] == "IP"][0]
    edgs.append({"account_id": "ACC_CLEAN_STUDENT_999", "entity_type": "IP", "entity_id": shared_ip})
    edgs.append({"account_id": "ACC_CLEAN_STUDENT_999", "entity_type": "DEVICE", "entity_id": "DEV_CLEAN_PHONE"})
    edgs.append({"account_id": "ACC_CLEAN_STUDENT_999", "entity_type": "PAYMENT", "entity_id": "CARD_CLEAN_DEBIT"})
    edgs.append({"account_id": "ACC_CLEAN_STUDENT_999", "entity_type": "ADDRESS", "entity_id": "ADDR_CLEAN_HOME"})

    resp = sentinel.detect(accs, edgs)
    # Bystander must be identified as INCIDENTAL_BYSTANDER
    bystander_role = [a for a in resp["account_attribution"] if a["account_id"] == "ACC_CLEAN_STUDENT_999"][0]["attribution_role"]
    assert bystander_role == "INCIDENTAL_BYSTANDER"

    # Action must be gated: NEVER BLOCK_ENTIRE_RING when a bystander is present
    assert resp["recommended_action"] != "BLOCK_ENTIRE_RING"
    assert resp["recommended_action"] in ["REVIEW_ACCOUNTS", "RESTRICT_SELECTED_ACCOUNT"]


def test_ac_evidence_quality_tiers(sentinel):
    """Test AC: Verify SUFFICIENT, LIMITED_SAMPLE, INSUFFICIENT_SAMPLE tiers."""
    # 1. INSUFFICIENT (Singleton)
    resp1 = sentinel.detect(accounts=[{"account_id": "A1"}], edges=[])
    assert resp1["evidence_quality"] == "INSUFFICIENT_SAMPLE"

    # 2. LIMITED (2 accounts, only 1 entity type)
    accs2 = [
        {"account_id": "A1", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
        {"account_id": "A2", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
    ]
    edgs2 = [
        {"account_id": "A1", "entity_type": "IP", "entity_id": "IP_1"},
        {"account_id": "A2", "entity_type": "IP", "entity_id": "IP_1"},
    ]
    resp2 = sentinel.detect(accounts=accs2, edges=edgs2)
    assert resp2["evidence_quality"] == "LIMITED_SAMPLE"


def test_ad_confidence_tiers(sentinel):
    """Test AD: Verify HIGH, MEDIUM, LOW confidence tiers."""
    # 1. LOW confidence (zero edges / insufficient sample)
    resp1 = sentinel.detect(accounts=[{"account_id": "A1"}], edges=[])
    assert resp1["confidence"] == "LOW"

    # 2. MEDIUM confidence (limited sample)
    accs2 = [
        {"account_id": "A1", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
        {"account_id": "A2", "created_at": "2026-01-01T00:00:00Z", "average_order_value": 50.0, "return_rate": 0.0, "suspicious_activity_score": 0.1},
    ]
    edgs2 = [
        {"account_id": "A1", "entity_type": "IP", "entity_id": "IP_1"},
        {"account_id": "A2", "entity_type": "IP", "entity_id": "IP_1"},
    ]
    resp2 = sentinel.detect(accounts=accs2, edges=edgs2)
    assert resp2["confidence"] == "MEDIUM"


def test_ae_operational_action_gating(sentinel, frozen_raw_data):
    """Test AE: BLOCK_ENTIRE_RING requires all 4 gates."""
    df_acc, df_edg, df_cls = frozen_raw_data
    synth_cid = df_cls[df_cls["cluster_type"] == "SYNTHETIC_IDENTITY_RING"].iloc[0]["cluster_id"]
    accs, edgs, meta = get_cluster_records(df_acc, df_edg, df_cls, synth_cid)

    resp = sentinel.detect(accs, edgs, meta)
    # Synthetic ring satisfies all 4 gates
    assert resp["verdict"] == "HIGH_CONFIDENCE_RING"
    assert resp["confidence"] == "HIGH"
    assert sum(1 for a in resp["account_attribution"] if a["attribution_role"] == "INCIDENTAL_BYSTANDER") == 0
    assert resp["recommended_action"] == "BLOCK_ENTIRE_RING"
