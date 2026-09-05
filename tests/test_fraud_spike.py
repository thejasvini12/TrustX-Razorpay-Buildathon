"""Unit and integration tests for Fraud-Spike Detector and POST /risk/fraud-spike endpoint."""

import os
import math
import numpy as np
import pytest
from fastapi.testclient import TestClient
from src.api import app
from src.fraud_spike_detector import FraudSpikeDetector
from src.evaluate_fraud_spike import evaluate_fraud_spike_on_test_set


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def detector():
    """FraudSpikeDetector fixture."""
    return FraudSpikeDetector(
        model_path="models/fraud_spike_model.joblib",
        metadata_path="models/fraud_spike_metadata.json",
    )


def test_fraud_spike_model_files_exist():
    """Verify serialized fraud spike model and metadata exist."""
    assert os.path.exists("models/fraud_spike_model.joblib")
    assert os.path.exists("models/fraud_spike_metadata.json")


def test_normal_stable_traffic(detector):
    """Scenario 1: Verify normal stable traffic produces spike_prediction = 0."""
    window = {
        "merchant_id": "MERCH_TEST_NORMAL",
        "baseline_tx_count": 2400,
        "current_tx_count": 100,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.02,
        "baseline_device_count": 2000,
        "current_device_count": 90,
        "baseline_suspicious_score": 0.04,
        "current_suspicious_score": 0.04,
    }
    res = detector.detect_spike(window)

    assert res["spike_prediction"] == 0
    assert res["spike_score"] < 30
    assert res["spike_level"] == "LOW"
    assert res["recommended_action"] == "ALLOW_STANDARD_OPERATIONS"
    assert "No significant fraud spike" in res["explanation"]
    assert len(res["mitigating_factors"]) > 0


def test_genuine_fraud_spike(detector):
    """Scenario 2: Verify sudden surge in fraud rate + velocity produces spike_prediction = 1."""
    window = {
        "merchant_id": "MERCH_TEST_SPIKE",
        "baseline_tx_count": 2400,
        "current_tx_count": 500,  # 5x hourly surge
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,  # Jump to 35% fraud
        "baseline_device_count": 2000,
        "current_device_count": 120,  # High device concentration
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.85,
    }
    res = detector.detect_spike(window)

    assert res["spike_prediction"] == 1
    assert res["spike_score"] >= 70
    assert res["spike_level"] == "HIGH"
    assert res["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"
    assert len(res["spike_factors"]) >= 2
    assert "exceeds validated spike thresholds" in res["explanation"]


def test_high_but_stable_fraud_rate_hard_negative(detector):
    """Scenario 3 (Hard Negative): Steady 12% fraud baseline with steady 12% current rate is NOT a spike."""
    window = {
        "merchant_id": "MERCH_TEST_HIGH_STABLE",
        "baseline_tx_count": 1200,
        "current_tx_count": 50,
        "baseline_fraud_rate": 0.12,
        "current_fraud_rate": 0.12,
        "baseline_device_count": 900,
        "current_device_count": 40,
        "baseline_suspicious_score": 0.30,
        "current_suspicious_score": 0.30,
    }
    res = detector.detect_spike(window)

    # Not a spike because fraud did NOT suddenly increase
    assert res["spike_prediction"] == 0
    assert res["spike_level"] in ["LOW", "MEDIUM"]
    assert res["fraud_rate_change"] == 0.0


def test_high_volume_flash_sale_hard_negative(detector):
    """Scenario 4 (Hard Negative): 6x volume surge during promotional sale with low fraud is NOT a spike."""
    window = {
        "merchant_id": "MERCH_TEST_FLASH_SALE",
        "baseline_tx_count": 1200,
        "current_tx_count": 300,  # 6x volume burst
        "baseline_fraud_rate": 0.015,
        "current_fraud_rate": 0.012,  # Clean low fraud rate
        "baseline_device_count": 1000,
        "current_device_count": 280,
        "baseline_suspicious_score": 0.04,
        "current_suspicious_score": 0.05,
    }
    res = detector.detect_spike(window)

    assert res["spike_prediction"] == 0
    assert res["spike_level"] == "LOW"
    assert res["recommended_action"] == "ALLOW_STANDARD_OPERATIONS"


def test_legitimate_organic_growth(detector):
    """Scenario 5: 30% organic traffic growth with stable fraud is NOT a spike."""
    window = {
        "merchant_id": "MERCH_TEST_ORGANIC",
        "baseline_tx_count": 960,
        "current_tx_count": 52,
        "baseline_fraud_rate": 0.025,
        "current_fraud_rate": 0.028,
        "baseline_device_count": 800,
        "current_device_count": 45,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.06,
    }
    res = detector.detect_spike(window)
    assert res["spike_prediction"] == 0


def test_low_volume_noise_hard_negative(detector):
    """Scenario 6 (Hard Negative): Very small sample size (2 transactions) with 1 disputed is NOT a validated spike."""
    window = {
        "merchant_id": "MERCH_TEST_NOISE",
        "baseline_tx_count": 48,
        "current_tx_count": 2,
        "baseline_fraud_count": 0,
        "current_fraud_count": 1,
        "baseline_device_count": 40,
        "current_device_count": 2,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.15,
    }
    res = detector.detect_spike(window)
    assert res["spike_prediction"] == 0


def test_boundary_borderline_spike(detector):
    """Scenario 7: Borderline velocity change produces valid structure and bounded score."""
    window = {
        "merchant_id": "MERCH_TEST_BORDERLINE",
        "baseline_tx_count": 1200,
        "current_tx_count": 80,
        "baseline_fraud_rate": 0.03,
        "current_fraud_rate": 0.10,
        "baseline_device_count": 1000,
        "current_device_count": 65,
        "baseline_suspicious_score": 0.08,
        "current_suspicious_score": 0.28,
    }
    res = detector.detect_spike(window)
    assert 0 <= res["spike_score"] <= 100
    assert res["spike_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert isinstance(res["explanation"], str)


def test_missing_input_defaults_handling(detector):
    """Scenario 8: Missing optional inputs are safely defaulted without crashing."""
    sparse_window = {
        "merchant_id": "MERCH_SPARSE_TEST",
        "current_tx_count": 15,
    }
    res = detector.detect_spike(sparse_window)
    assert res["merchant_id"] == "MERCH_SPARSE_TEST"
    assert 0 <= res["spike_score"] <= 100
    assert "spike_factors" in res


def test_api_fraud_spike_endpoint(client):
    """Scenario 9 & 10: Verify POST /risk/fraud-spike returns HTTP 200 with complete schema."""
    payload = {
        "merchant_id": "MERCH_API_SPIKE_CHECK",
        "baseline_window": "previous_24h",
        "current_window": "latest_1h",
        "baseline_tx_count": 2400,
        "current_tx_count": 450,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.38,
        "baseline_device_count": 2000,
        "current_device_count": 100,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.88,
    }
    response = client.post("/risk/fraud-spike", json=payload)
    assert response.status_code == 200
    data = response.json()

    expected_keys = [
        "merchant_id",
        "spike_prediction",
        "spike_probability",
        "spike_score",
        "spike_level",
        "baseline_window",
        "current_window",
        "baseline_fraud_rate",
        "current_fraud_rate",
        "fraud_rate_change",
        "spike_factors",
        "mitigating_factors",
        "explanation",
        "recommended_action",
    ]
    for k in expected_keys:
        assert k in data, f"Key '{k}' missing from /risk/fraud-spike response."

    assert data["merchant_id"] == "MERCH_API_SPIKE_CHECK"
    assert data["spike_prediction"] == 1
    assert data["spike_score"] >= 70
    assert data["spike_level"] == "HIGH"
    assert data["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"


def test_held_out_evaluation_metrics_precision_recall():
    """Verify that held-out test evaluation report passes rigor checks."""
    report = evaluate_fraud_spike_on_test_set()
    assert report["dataset_summary"]["total_test_windows"] == 600
    assert report["dataset_summary"]["positive_windows (genuine spike)"] > 0
    assert report["performance_metrics"]["precision"] >= 0.90
    assert report["performance_metrics"]["recall"] >= 0.90
    assert report["performance_metrics"]["f1_score"] >= 0.90
    assert report["performance_metrics"]["roc_auc"] >= 0.95


def test_all_models_coexist_unmodified():
    """Scenario 11: Confirm all 3 models coexist independently."""
    assert os.path.exists("models/risk_engine_rf.joblib")
    assert os.path.exists("models/return_risk_model.joblib")
    assert os.path.exists("models/fraud_spike_model.joblib")


def test_15_hard_unseen_stress_scenarios(detector):
    """Verify detector robustness across all 15 hard unseen stress combinations."""
    stress_cases = [
        ("Huge Volume + Stable Low Fraud", {
            "baseline_tx_count": 50000, "current_tx_count": 15000, "baseline_fraud_rate": 0.008, "current_fraud_rate": 0.007,
            "baseline_device_count": 40000, "current_device_count": 13000, "baseline_suspicious_score": 0.02, "current_suspicious_score": 0.03
        }, 0),
        ("Huge Volume + Slight Fraud Bump", {
            "baseline_tx_count": 50000, "current_tx_count": 12000, "baseline_fraud_rate": 0.008, "current_fraud_rate": 0.014,
            "baseline_device_count": 40000, "current_device_count": 10000, "baseline_suspicious_score": 0.02, "current_suspicious_score": 0.05
        }, 0),
        ("Tiny Volume Noise (3 tx, 1 dispute)", {
            "baseline_tx_count": 72, "current_tx_count": 3, "baseline_fraud_count": 1, "current_fraud_count": 1,
            "baseline_device_count": 60, "current_device_count": 3, "baseline_suspicious_score": 0.04, "current_suspicious_score": 0.10
        }, 0),
        ("High Stable Fraud (15% steady)", {
            "baseline_tx_count": 2400, "current_tx_count": 100, "baseline_fraud_rate": 0.15, "current_fraud_rate": 0.15,
            "baseline_device_count": 1800, "current_device_count": 75, "baseline_suspicious_score": 0.35, "current_suspicious_score": 0.35
        }, 0),
        ("High Fraud + Normal Velocity (ATO)", {
            "baseline_tx_count": 2400, "current_tx_count": 100, "baseline_fraud_rate": 0.02, "current_fraud_rate": 0.45,
            "baseline_device_count": 1800, "current_device_count": 30, "baseline_suspicious_score": 0.05, "current_suspicious_score": 0.75
        }, 1),
        ("High Velocity (5x) + Healthy Fraud (1%)", {
            "baseline_tx_count": 1200, "current_tx_count": 250, "baseline_fraud_rate": 0.01, "current_fraud_rate": 0.012,
            "baseline_device_count": 1000, "current_device_count": 220, "baseline_suspicious_score": 0.03, "current_suspicious_score": 0.04
        }, 0),
        ("High Device Conc + Healthy Fraud", {
            "baseline_tx_count": 2400, "current_tx_count": 120, "baseline_fraud_rate": 0.01, "current_fraud_rate": 0.015,
            "baseline_device_count": 2000, "current_device_count": 15, "baseline_suspicious_score": 0.03, "current_suspicious_score": 0.05
        }, 0),
        ("High Susp Score + Stable Low Fraud", {
            "baseline_tx_count": 2400, "current_tx_count": 100, "baseline_fraud_rate": 0.02, "current_fraud_rate": 0.025,
            "baseline_device_count": 2000, "current_device_count": 80, "baseline_suspicious_score": 0.50, "current_suspicious_score": 0.55
        }, 0),
        ("Moderate Changes Across Signals", {
            "baseline_tx_count": 2400, "current_tx_count": 160, "baseline_fraud_rate": 0.02, "current_fraud_rate": 0.08,
            "baseline_device_count": 2000, "current_device_count": 100, "baseline_suspicious_score": 0.05, "current_suspicious_score": 0.25
        }, 0),
        ("Extreme Simultaneous Attack", {
            "baseline_tx_count": 2400, "current_tx_count": 600, "baseline_fraud_rate": 0.01, "current_fraud_rate": 0.65,
            "baseline_device_count": 2000, "current_device_count": 50, "baseline_suspicious_score": 0.02, "current_suspicious_score": 0.95
        }, 1),
        ("Organic Growth (+40% volume)", {
            "baseline_tx_count": 2400, "current_tx_count": 140, "baseline_fraud_rate": 0.02, "current_fraud_rate": 0.022,
            "baseline_device_count": 2000, "current_device_count": 120, "baseline_suspicious_score": 0.04, "current_suspicious_score": 0.05
        }, 0),
        ("Promotional Flash Sale (8x vol)", {
            "baseline_tx_count": 2400, "current_tx_count": 800, "baseline_fraud_rate": 0.015, "current_fraud_rate": 0.012,
            "baseline_device_count": 2000, "current_device_count": 720, "baseline_suspicious_score": 0.03, "current_suspicious_score": 0.04
        }, 0),
        ("Genuine Sudden Attack (Syndicate)", {
            "baseline_tx_count": 2400, "current_tx_count": 450, "baseline_fraud_rate": 0.02, "current_fraud_rate": 0.40,
            "baseline_device_count": 2000, "current_device_count": 90, "baseline_suspicious_score": 0.05, "current_suspicious_score": 0.85
        }, 1),
        ("Sudden Fraud Jump without Volume Surge", {
            "baseline_tx_count": 2400, "current_tx_count": 100, "baseline_fraud_rate": 0.01, "current_fraud_rate": 0.38,
            "baseline_device_count": 2000, "current_device_count": 25, "baseline_suspicious_score": 0.04, "current_suspicious_score": 0.80
        }, 1),
        ("Volume Surge without Fraud Increase", {
            "baseline_tx_count": 1200, "current_tx_count": 350, "baseline_fraud_rate": 0.02, "current_fraud_rate": 0.018,
            "baseline_device_count": 1000, "current_device_count": 300, "baseline_suspicious_score": 0.05, "current_suspicious_score": 0.06
        }, 0),
    ]
    for name, data, expected_label in stress_cases:
        res = detector.detect_spike(data)
        assert res["spike_prediction"] == expected_label, f"Failed on scenario '{name}'"


def test_edge_cases_numerical_safety(detector):
    """Verify edge case inputs do not crash or produce NaNs."""
    edge_cases = [
        {"baseline_tx_count": 0, "current_tx_count": 10},
        {"baseline_tx_count": 100, "current_tx_count": 0},
        {"baseline_device_count": 0, "current_device_count": 0},
        {"baseline_fraud_count": 0, "current_fraud_count": 0, "baseline_fraud_rate": 0.0, "current_fraud_rate": 0.0},
        {"baseline_fraud_rate": 1.0, "current_fraud_rate": 1.0},
        {"baseline_tx_count": 10_000_000, "current_tx_count": 1_000_000},
        {"baseline_tx_count": None, "current_fraud_rate": None},
    ]
    for ec in edge_cases:
        res = detector.detect_spike(ec)
        assert 0 <= res["spike_score"] <= 100
        assert res["spike_level"] in ["LOW", "MEDIUM", "HIGH"]
        assert isinstance(res["explanation"], str)


def test_api_fraud_spike_validation_errors(client):
    """Verify that invalid inputs return HTTP 422 Unprocessable Entity."""
    # 1. Negative transaction count
    res_neg_tx = client.post("/risk/fraud-spike", json={"baseline_tx_count": -5})
    assert res_neg_tx.status_code == 422

    # 2. Fraud rate > 1.0
    res_high_rate = client.post("/risk/fraud-spike", json={"current_fraud_rate": 2.5})
    assert res_high_rate.status_code == 422

    # 3. Non-numeric count
    res_str = client.post("/risk/fraud-spike", json={"current_tx_count": "invalid_count"})
    assert res_str.status_code == 422


def test_evidence_quality_and_confidence_scenarios(detector):
    """Verify evidence quality and operational confidence layer across all volume tiers."""
    # A. Strong Evidence: Large sample genuine spike
    w_strong = {
        "merchant_id": "MERCH_STRONG_EV",
        "baseline_tx_count": 1000,
        "current_tx_count": 500,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "baseline_device_count": 800,
        "current_device_count": 100,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.85,
    }
    res_strong = detector.detect_spike(w_strong)
    assert res_strong["evidence_quality"] == "SUFFICIENT"
    assert res_strong["confidence"] == "HIGH"
    assert "large number of baseline and current transactions" in res_strong["evidence_summary"]

    # B. Medium Evidence: Moderate sample
    w_medium = {
        "merchant_id": "MERCH_MED_EV",
        "baseline_tx_count": 80,
        "current_tx_count": 10,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "baseline_device_count": 65,
        "current_device_count": 4,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.85,
    }
    res_medium = detector.detect_spike(w_medium)
    assert res_medium["evidence_quality"] == "LIMITED_SAMPLE"
    assert res_medium["confidence"] in ["MEDIUM", "LOW"]
    assert "relatively few transactions" in res_medium["evidence_summary"]

    # C. Insufficient Evidence: Tiny sample (1 baseline, 2 current)
    w_insufficient = {
        "merchant_id": "MERCH_INSUFF_EV",
        "baseline_tx_count": 1,
        "current_tx_count": 2,
        "baseline_fraud_count": 0,
        "current_fraud_count": 1,
        "baseline_device_count": 1,
        "current_device_count": 1,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.80,
    }
    res_insufficient = detector.detect_spike(w_insufficient)
    assert res_insufficient["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert res_insufficient["confidence"] == "LOW"
    assert "too few transactions" in res_insufficient["evidence_summary"]
    assert res_insufficient["recommended_action"] == "COLLECT_ADDITIONAL_DATA_BEFORE_ENFORCING"

    # D. Small but Legitimate Traffic: No spike
    w_small_clean = {
        "merchant_id": "MERCH_SMALL_CLEAN",
        "baseline_tx_count": 2,
        "current_tx_count": 2,
        "baseline_fraud_count": 0,
        "current_fraud_count": 0,
    }
    res_small_clean = detector.detect_spike(w_small_clean)
    assert res_small_clean["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert res_small_clean["confidence"] == "LOW"
    assert res_small_clean["spike_prediction"] == 0
    assert res_small_clean["spike_level"] == "LOW"

    # E. Huge Legitimate Volume: 50,000 baseline, 10,000 current, clean fraud
    w_huge_clean = {
        "merchant_id": "MERCH_HUGE_CLEAN",
        "baseline_tx_count": 50000,
        "current_tx_count": 10000,
        "baseline_fraud_rate": 0.008,
        "current_fraud_rate": 0.007,
    }
    res_huge_clean = detector.detect_spike(w_huge_clean)
    assert res_huge_clean["evidence_quality"] == "SUFFICIENT"
    assert res_huge_clean["confidence"] == "HIGH"
    assert res_huge_clean["spike_prediction"] == 0

    # F. Huge Genuine Spike: 50,000 baseline, 10,000 current, 35% fraud
    w_huge_spike = {
        "merchant_id": "MERCH_HUGE_SPIKE",
        "baseline_tx_count": 50000,
        "current_tx_count": 10000,
        "baseline_fraud_rate": 0.01,
        "current_fraud_rate": 0.35,
        "baseline_device_count": 40000,
        "current_device_count": 2000,
        "baseline_suspicious_score": 0.02,
        "current_suspicious_score": 0.90,
    }
    res_huge_spike = detector.detect_spike(w_huge_spike)
    assert res_huge_spike["evidence_quality"] == "SUFFICIENT"
    assert res_huge_spike["confidence"] == "HIGH"
    assert res_huge_spike["spike_prediction"] == 1


# =========================================================================
# P1 Policy Guardrail Tests: Deterministic Fraud Rate Delta Floor
# =========================================================================

def test_guardrail_1_severe_delta_low_raw_ml_escalates_to_medium(detector):
    """1. Severe delta (33%) + sufficient volume (30 tx) + low raw ML escalates to at least MEDIUM."""
    payload = {
        "merchant_id": "MERCH_GUARDRAIL_TEST_1",
        "baseline_tx_count": 2400,
        "current_tx_count": 30,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "baseline_device_count": 2000,
        "current_device_count": 30,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.05,  # Unpopulated / flat suspicious score
    }
    res = detector.detect_spike(payload)

    assert res["guardrail_triggered"] is True
    assert res["raw_spike_level"] == "LOW"
    assert res["spike_level"] == "MEDIUM"
    assert res["spike_score"] >= 45
    assert res["recommended_action"] == "FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR"
    assert any("Large increase in observed fraud rate" in f for f in res["spike_factors"])
    assert "policy-adjusted score" in res["explanation"]


def test_guardrail_2_severe_delta_already_medium_never_downgraded(detector):
    """2. Severe delta + sufficient volume + already MEDIUM is preserved and never downgraded."""
    payload = {
        "merchant_id": "MERCH_GUARDRAIL_TEST_2",
        "baseline_tx_count": 2400,
        "current_tx_count": 100,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.28,
        "baseline_device_count": 2000,
        "current_device_count": 75,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.50,
    }
    res = detector.detect_spike(payload)

    assert res["guardrail_triggered"] is True
    assert res["raw_spike_level"] == "MEDIUM"
    assert res["spike_level"] == "MEDIUM"
    assert res["spike_score"] == res["raw_spike_score"]
    assert res["spike_score"] >= 30


def test_guardrail_3_severe_delta_already_high_remains_high(detector):
    """3. Severe delta + sufficient volume + already HIGH remains HIGH (never downgraded)."""
    payload = {
        "merchant_id": "MERCH_GUARDRAIL_TEST_3",
        "baseline_tx_count": 2400,
        "current_tx_count": 500,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.40,
        "baseline_device_count": 2000,
        "current_device_count": 100,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.85,
    }
    res = detector.detect_spike(payload)

    assert res["guardrail_triggered"] is True
    assert res["raw_spike_level"] == "HIGH"
    assert res["spike_level"] == "HIGH"
    assert res["spike_score"] == res["raw_spike_score"]
    assert res["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"


def test_guardrail_4_sub_15_current_tx_does_not_trigger(detector):
    """4. Severe delta with current_tx_count = 14 does NOT trigger guardrail (small-sample safety)."""
    payload = {
        "merchant_id": "MERCH_GUARDRAIL_TEST_4",
        "baseline_tx_count": 2400,
        "current_tx_count": 14,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "baseline_device_count": 2000,
        "current_device_count": 14,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.05,
    }
    res = detector.detect_spike(payload)

    assert res["guardrail_triggered"] is False
    assert res["spike_level"] == res["raw_spike_level"]


def test_guardrail_5_exact_boundary_delta_025_and_15_tx_triggers(detector):
    """5. Delta exactly 0.25 with current_tx_count exactly 15 triggers guardrail."""
    payload = {
        "merchant_id": "MERCH_GUARDRAIL_TEST_5",
        "baseline_tx_count": 2400,
        "current_tx_count": 15,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.27,  # Exact delta = 0.25
        "baseline_device_count": 2000,
        "current_device_count": 15,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.05,
    }
    res = detector.detect_spike(payload)

    assert res["guardrail_triggered"] is True
    assert res["spike_level"] in ["MEDIUM", "HIGH"]
    assert res["spike_score"] >= 45


def test_guardrail_6_delta_below_025_does_not_trigger(detector):
    """6. Delta 0.249 with current_tx_count 15 does NOT trigger guardrail."""
    payload = {
        "merchant_id": "MERCH_GUARDRAIL_TEST_6",
        "baseline_tx_count": 2400,
        "current_tx_count": 15,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.269,  # Delta = 0.249
        "baseline_device_count": 2000,
        "current_device_count": 15,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.05,
    }
    res = detector.detect_spike(payload)

    assert res["guardrail_triggered"] is False
    assert res["spike_level"] == res["raw_spike_level"]


def test_guardrail_7_missing_suspicious_score_telemetry_protected(detector):
    """7. Missing/default suspicious_score with severe fraud delta is protected by guardrail."""
    payload = {
        "merchant_id": "MERCH_GUARDRAIL_TEST_7",
        "baseline_tx_count": 1200,
        "current_tx_count": 25,
        "baseline_fraud_rate": 0.01,
        "current_fraud_rate": 0.38,
        # baseline_suspicious_score and current_suspicious_score omitted -> default 0.05
    }
    res = detector.detect_spike(payload)

    assert res["guardrail_triggered"] is True
    assert res["spike_level"] in ["MEDIUM", "HIGH"]
    assert res["spike_score"] >= 45
    assert "Large increase in observed fraud rate relative to baseline" in res["spike_factors"][0]


def test_guardrail_8_flash_sale_low_fraud_delta_unaffected(detector):
    """8. Legitimate high-volume flash sale with low fraud delta does NOT trigger guardrail."""
    payload = {
        "merchant_id": "MERCH_GUARDRAIL_TEST_8",
        "baseline_tx_count": 2400,
        "current_tx_count": 1000,
        "baseline_fraud_rate": 0.015,
        "current_fraud_rate": 0.012,
        "baseline_device_count": 2000,
        "current_device_count": 900,
        "baseline_suspicious_score": 0.03,
        "current_suspicious_score": 0.04,
    }
    res = detector.detect_spike(payload)

    assert res["guardrail_triggered"] is False
    assert res["spike_level"] == "LOW"
    assert res["recommended_action"] == "ALLOW_STANDARD_OPERATIONS"


def test_guardrail_9_api_response_transparency_fields(client):
    """9. Verify POST /risk/fraud-spike exposes raw ML and guardrail transparency fields."""
    payload = {
        "merchant_id": "MERCH_API_GUARDRAIL_CHECK",
        "baseline_tx_count": 2400,
        "current_tx_count": 30,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.05,
    }
    response = client.post("/risk/fraud-spike", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "raw_spike_probability" in data
    assert "raw_spike_score" in data
    assert "raw_spike_level" in data
    assert "guardrail_triggered" in data
    assert data["guardrail_triggered"] is True
    assert data["raw_spike_level"] == "LOW"
    assert data["spike_level"] == "MEDIUM"
    assert data["spike_score"] >= 45


# =========================================================================
# P2 Policy Guardrail Tests: Zero-Count & Edge-Case Factor Guardrails
# =========================================================================

def test_p2_1_zero_baseline_zero_current(detector):
    """P2.1: baseline_tx_count=0, current_tx_count=0 produces no fabricated surge or promo mitigations."""
    payload = {
        "merchant_id": "MERCH_ZERO_ZERO",
        "baseline_tx_count": 0,
        "current_tx_count": 0,
    }
    res = detector.detect_spike(payload)

    assert res["spike_score"] == 0
    assert res["spike_level"] == "LOW"
    assert res["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert "0 current, 0 baseline" in res["evidence_summary"]

    # Verify no fabricated 10x volume surge factors
    assert not any("Hourly transaction volume surged" in f for f in res["spike_factors"])
    assert not any("10.0x" in f for f in res["spike_factors"])

    # Verify no fabricated marketing promotional surge mitigating factors
    assert not any("legitimate marketing/promotional surge" in m for m in res["mitigating_factors"])
    assert not any("1-to-1 device-to-transaction ratio" in m for m in res["mitigating_factors"])
    assert "No transaction activity observed in current window" in res["mitigating_factors"]


def test_p2_2_zero_baseline_positive_current(detector):
    """P2.2: baseline_tx_count=0, current_tx_count > 0 produces no fabricated surge ratio."""
    payload = {
        "merchant_id": "MERCH_ZERO_BASE_POS_CURR",
        "baseline_tx_count": 0,
        "current_tx_count": 20,
        "baseline_fraud_rate": 0.0,
        "current_fraud_rate": 0.0,
    }
    res = detector.detect_spike(payload)

    assert 0 <= res["spike_score"] <= 100
    assert res["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert "20 current, 0 baseline" in res["evidence_summary"]

    # Verify no fabricated 200x volume surge factor against 0 baseline
    assert not any("Hourly transaction volume surged" in f for f in res["spike_factors"])
    assert not any("legitimate marketing/promotional surge" in m for m in res["mitigating_factors"])


def test_p2_3_positive_baseline_zero_current(detector):
    """P2.3: baseline_tx_count > 0, current_tx_count=0 produces no surge or device mitigations."""
    payload = {
        "merchant_id": "MERCH_POS_BASE_ZERO_CURR",
        "baseline_tx_count": 240,
        "current_tx_count": 0,
    }
    res = detector.detect_spike(payload)

    assert res["spike_score"] == 0
    assert res["spike_level"] == "LOW"
    assert res["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert "0 current, 240 baseline" in res["evidence_summary"]

    assert not any("Hourly transaction volume surged" in f for f in res["spike_factors"])
    assert not any("legitimate marketing/promotional surge" in m for m in res["mitigating_factors"])
    assert "No transaction activity observed in current window" in res["mitigating_factors"]


def test_p2_4_legitimate_nonzero_flash_sale_surge_intact(detector):
    """P2.4: Genuine non-zero flash sale continues to produce legitimate volume surge factors."""
    payload = {
        "merchant_id": "MERCH_GENUINE_FLASH_SALE",
        "baseline_tx_count": 100,
        "current_tx_count": 1000,  # 240x hourly surge
        "baseline_fraud_rate": 0.015,
        "current_fraud_rate": 0.012,
    }
    res = detector.detect_spike(payload)

    assert res["spike_prediction"] == 0
    assert res["spike_level"] == "LOW"
    assert any("Hourly transaction volume surged" in f for f in res["spike_factors"])
    assert any("legitimate marketing/promotional surge" in m for m in res["mitigating_factors"])


def test_p2_5_numerical_safety_no_nan_or_inf(detector):
    """P2.5: Zero, negative, and infinite inputs evaluate cleanly without numerical failure."""
    edge_cases = [
        {"baseline_tx_count": 0, "current_tx_count": 0},
        {"baseline_tx_count": -100, "current_tx_count": -50},
        {"baseline_tx_count": 0, "current_tx_count": 500, "current_fraud_rate": 0.40},
    ]
    for ec in edge_cases:
        res = detector.detect_spike(ec)
        assert 0 <= res["spike_score"] <= 100
        assert res["spike_level"] in ["LOW", "MEDIUM", "HIGH"]
        assert not any(math.isnan(x) for x in [res["spike_probability"], res["spike_score"], res["fraud_rate_change"]])


# =========================================================================
# P3 Policy Guardrail Tests: Stateful Incident Escalation Tracker
# =========================================================================

def _get_medium_spike_payload(merchant_id: str = "MERCH_P3_TEST") -> dict:
    """Helper returning a valid payload that evaluates to MEDIUM operational tier."""
    return {
        "merchant_id": merchant_id,
        "baseline_tx_count": 1000,
        "current_tx_count": 50,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.15,
        "baseline_suspicious_score": 0.10,
        "current_suspicious_score": 0.60,
    }


def _get_low_spike_payload(merchant_id: str = "MERCH_P3_TEST") -> dict:
    """Helper returning a valid payload that evaluates to LOW tier."""
    return {
        "merchant_id": merchant_id,
        "baseline_tx_count": 1000,
        "current_tx_count": 100,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.02,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.05,
    }


def test_p3_1_single_medium_remains_medium(detector):
    """P3.1: Single MEDIUM event sets counter=1 and remains MEDIUM."""
    payload = _get_medium_spike_payload("MERCH_SINGLE_MED")
    res = detector.detect_spike(payload)

    assert res["raw_spike_level"] == "MEDIUM"
    assert res["spike_level"] == "MEDIUM"
    assert res["consecutive_anomaly_windows"] == 1
    assert res["persistence_escalation_triggered"] is False
    assert res["recommended_action"] == "FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR"


def test_p3_2_two_consecutive_medium_remains_medium(detector):
    """P3.2: Two consecutive MEDIUM events set counter=2 and remain MEDIUM."""
    payload = _get_medium_spike_payload("MERCH_TWO_MED")

    res1 = detector.detect_spike(payload)
    assert res1["consecutive_anomaly_windows"] == 1
    assert res1["spike_level"] == "MEDIUM"

    res2 = detector.detect_spike(payload)
    assert res2["consecutive_anomaly_windows"] == 2
    assert res2["spike_level"] == "MEDIUM"
    assert res2["persistence_escalation_triggered"] is False
    assert res2["recommended_action"] == "FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR"


def test_p3_3_three_consecutive_medium_escalates_to_high(detector):
    """P3.3: Three consecutive MEDIUM events escalate to HIGH with 2FA enforcement."""
    payload = _get_medium_spike_payload("MERCH_THREE_MED")

    detector.detect_spike(payload)
    detector.detect_spike(payload)
    res3 = detector.detect_spike(payload)

    assert res3["raw_spike_level"] == "MEDIUM"
    assert res3["spike_level"] == "HIGH"
    assert res3["spike_score"] >= 75
    assert res3["consecutive_anomaly_windows"] == 3
    assert res3["persistence_escalation_triggered"] is True
    assert res3["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"
    assert any("Persistent anomaly pattern" in f for f in res3["spike_factors"])
    assert "High operational risk escalated by persistence policy" in res3["explanation"]


def test_p3_4_four_consecutive_medium_remains_escalated(detector):
    """P3.4: Four consecutive MEDIUM events remain escalated and do not oscillate."""
    payload = _get_medium_spike_payload("MERCH_FOUR_MED")

    for _ in range(3):
        detector.detect_spike(payload)

    res4 = detector.detect_spike(payload)
    assert res4["consecutive_anomaly_windows"] == 4
    assert res4["persistence_escalation_triggered"] is True
    assert res4["spike_level"] == "HIGH"
    assert res4["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"


def test_p3_5_low_event_resets_counter(detector):
    """P3.5: A LOW event breaks the sequence and resets counter to 0."""
    med_payload = _get_medium_spike_payload("MERCH_RESET_TEST")
    low_payload = _get_low_spike_payload("MERCH_RESET_TEST")

    detector.detect_spike(med_payload)
    detector.detect_spike(med_payload)
    assert detector.tracker.get_count("MERCH_RESET_TEST") == 2

    res_low = detector.detect_spike(low_payload)
    assert res_low["spike_level"] == "LOW"
    assert res_low["consecutive_anomaly_windows"] == 0
    assert res_low["persistence_escalation_triggered"] is False
    assert detector.tracker.get_count("MERCH_RESET_TEST") == 0


def test_p3_6_medium_after_low_starts_new_sequence(detector):
    """P3.6: MEDIUM after LOW starts fresh counter at 1 and does not escalate."""
    med_payload = _get_medium_spike_payload("MERCH_RESTART_TEST")
    low_payload = _get_low_spike_payload("MERCH_RESTART_TEST")

    detector.detect_spike(med_payload)
    detector.detect_spike(med_payload)
    detector.detect_spike(low_payload)

    res = detector.detect_spike(med_payload)
    assert res["consecutive_anomaly_windows"] == 1
    assert res["spike_level"] == "MEDIUM"
    assert res["persistence_escalation_triggered"] is False


def test_p3_7_existing_ml_high_never_downgraded(detector):
    """P3.7: Genuine ML HIGH is never downgraded and preserves HIGH enforcement."""
    high_payload = {
        "merchant_id": "MERCH_GENUINE_HIGH",
        "baseline_tx_count": 2400,
        "current_tx_count": 500,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "current_suspicious_score": 0.85,
        "current_device_count": 100,
    }
    res = detector.detect_spike(high_payload)

    assert res["raw_spike_level"] == "HIGH"
    assert res["spike_level"] == "HIGH"
    assert res["persistence_escalation_triggered"] is False
    assert res["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"


def test_p3_8_p1_guardrail_compatibility(detector):
    """P3.8: P1 fraud-rate delta floor escalates to MEDIUM and integrates with P3 tracking."""
    p1_payload = {
        "merchant_id": "MERCH_P1_P3_INTEGRATION",
        "baseline_tx_count": 2400,
        "current_tx_count": 30,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.05,
    }

    # Eval 1: P1 triggers -> MEDIUM, counter=1
    r1 = detector.detect_spike(p1_payload)
    assert r1["guardrail_triggered"] is True
    assert r1["raw_spike_level"] == "LOW"
    assert r1["spike_level"] == "MEDIUM"
    assert r1["consecutive_anomaly_windows"] == 1

    # Eval 2
    r2 = detector.detect_spike(p1_payload)
    assert r2["consecutive_anomaly_windows"] == 2
    assert r2["spike_level"] == "MEDIUM"

    # Eval 3: P3 triggers persistence escalation -> HIGH
    r3 = detector.detect_spike(p1_payload)
    assert r3["consecutive_anomaly_windows"] == 3
    assert r3["persistence_escalation_triggered"] is True
    assert r3["spike_level"] == "HIGH"
    assert r3["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"


def test_p3_9_merchant_isolation_no_cross_contamination(detector):
    """P3.9: Anomaly counters are strictly isolated per merchant."""
    med_a = _get_medium_spike_payload("MERCH_ISOLATED_A")
    med_b = _get_medium_spike_payload("MERCH_ISOLATED_B")

    detector.detect_spike(med_a)
    detector.detect_spike(med_a)
    assert detector.tracker.get_count("MERCH_ISOLATED_A") == 2

    detector.detect_spike(med_b)
    assert detector.tracker.get_count("MERCH_ISOLATED_B") == 1

    res_a3 = detector.detect_spike(med_a)
    assert res_a3["consecutive_anomaly_windows"] == 3
    assert res_a3["persistence_escalation_triggered"] is True
    assert res_a3["spike_level"] == "HIGH"

    assert detector.tracker.get_count("MERCH_ISOLATED_B") == 1


def test_p3_10_anonymous_merchants_remain_stateless(detector):
    """P3.10: Unidentified / MERCH_UNKNOWN requests evaluate statelessly without counter accumulation."""
    anon_payload = _get_medium_spike_payload("MERCH_UNKNOWN")

    for _ in range(5):
        res = detector.detect_spike(anon_payload)
        assert res["consecutive_anomaly_windows"] == 0
        assert res["persistence_escalation_triggered"] is False
        assert res["spike_level"] == "MEDIUM"


def test_p3_11_api_endpoint_persistence_escalation(client):
    """P3.11: POST /risk/fraud-spike tracks consecutive anomalies across API requests for a merchant."""
    payload = _get_medium_spike_payload("MERCH_API_P3_TRACK")

    # Call 1
    resp1 = client.post("/risk/fraud-spike", json=payload)
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert d1["consecutive_anomaly_windows"] == 1
    assert d1["persistence_escalation_triggered"] is False
    assert d1["spike_level"] == "MEDIUM"

    # Call 2
    resp2 = client.post("/risk/fraud-spike", json=payload)
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["consecutive_anomaly_windows"] == 2
    assert d2["persistence_escalation_triggered"] is False
    assert d2["spike_level"] == "MEDIUM"

    # Call 3 -> Escalates
    resp3 = client.post("/risk/fraud-spike", json=payload)
    assert resp3.status_code == 200
    d3 = resp3.json()
    assert d3["consecutive_anomaly_windows"] == 3
    assert d3["persistence_escalation_triggered"] is True
    assert d3["spike_level"] == "HIGH"
    assert d3["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"


# =========================================================================
# P4 Policy Guardrail Tests: Prediction-vs-Policy Tier Alignment & Transparency
# =========================================================================

def test_p4_1_raw_low_final_low_alignment(detector):
    """P4.1: When neither ML nor policy escalates, raw and final tiers are both LOW."""
    payload = _get_low_spike_payload("MERCH_P4_LOW")
    res = detector.detect_spike(payload)

    assert res["raw_spike_level"] == "LOW"
    assert res["spike_level"] == "LOW"
    assert res["raw_spike_score"] == res["spike_score"]
    assert res["guardrail_triggered"] is False
    assert res["persistence_escalation_triggered"] is False
    assert res["consecutive_anomaly_windows"] == 0
    assert res["recommended_action"] == "ALLOW_STANDARD_OPERATIONS"


def test_p4_2_p1_guardrail_raw_low_final_medium_transparency(detector):
    """P4.2: P1 escalation clearly separates raw LOW ML from final MEDIUM policy tier."""
    payload = {
        "merchant_id": "MERCH_P4_P1",
        "baseline_tx_count": 2400,
        "current_tx_count": 30,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.05,
    }
    res = detector.detect_spike(payload)

    # Raw model remains LOW
    assert res["raw_spike_level"] == "LOW"
    assert res["raw_spike_score"] < 30
    assert 0.0 <= res["raw_spike_probability"] < 0.30

    # Policy adjusts to MEDIUM
    assert res["spike_level"] == "MEDIUM"
    assert res["spike_score"] >= 45
    assert res["guardrail_triggered"] is True
    assert res["persistence_escalation_triggered"] is False
    assert res["recommended_action"] == "FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR"

    # Explanation distinguishes policy score from raw ML score
    assert "policy-adjusted score" in res["explanation"]
    assert "raw ML:" in res["explanation"]


def test_p4_3_p3_persistence_raw_medium_final_high_transparency(detector):
    """P4.3: P3 persistence escalation clearly reports raw ML as MEDIUM and final tier as HIGH."""
    payload = _get_medium_spike_payload("MERCH_P4_P3")

    detector.detect_spike(payload)
    detector.detect_spike(payload)
    res = detector.detect_spike(payload)

    # Raw model remains exactly MEDIUM
    assert res["raw_spike_level"] == "MEDIUM"
    assert res["raw_spike_score"] == 59
    assert res["raw_spike_probability"] == 0.5949

    # Final policy tier is escalated to HIGH
    assert res["spike_level"] == "HIGH"
    assert res["spike_score"] == 75
    assert res["persistence_escalation_triggered"] is True
    assert res["consecutive_anomaly_windows"] == 3
    assert res["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"

    # Explanation attributes HIGH strictly to persistence policy
    assert "High operational risk escalated by persistence policy" in res["explanation"]
    assert f"raw ML: {res['raw_spike_score']}/100" in res["explanation"]


def test_p4_4_genuine_ml_high_no_false_persistence_attribution(detector):
    """P4.4: Genuine ML HIGH is never attributed to persistence policy."""
    payload = {
        "merchant_id": "MERCH_P4_ML_HIGH",
        "baseline_tx_count": 2400,
        "current_tx_count": 500,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "current_suspicious_score": 0.85,
        "current_device_count": 100,
    }
    res = detector.detect_spike(payload)

    assert res["raw_spike_level"] == "HIGH"
    assert res["raw_spike_score"] >= 70
    assert res["spike_level"] == "HIGH"
    assert res["persistence_escalation_triggered"] is False
    assert "escalated by persistence policy" not in res["explanation"]
    assert res["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"


def test_p4_5_raw_probability_and_score_immutability(detector):
    """P4.5: Policy layers never mutate raw_spike_probability or raw_spike_score."""
    scenarios = [
        _get_low_spike_payload("MERCH_P4_IMM_1"),
        _get_medium_spike_payload("MERCH_P4_IMM_2"),
        {
            "merchant_id": "MERCH_P4_IMM_3",
            "baseline_tx_count": 2400,
            "current_tx_count": 30,
            "baseline_fraud_rate": 0.02,
            "current_fraud_rate": 0.35,
            "baseline_suspicious_score": 0.05,
            "current_suspicious_score": 0.05,
        },
    ]
    for s in scenarios:
        res = detector.detect_spike(s)
        # Verify raw score is exact mathematical derivation from raw probability
        expected_raw_score = int(np.clip(np.round(res["raw_spike_probability"] * 100), 0, 100))
        assert res["raw_spike_score"] == expected_raw_score

        if res["raw_spike_score"] >= 70:
            assert res["raw_spike_level"] == "HIGH"
        elif res["raw_spike_score"] >= 30:
            assert res["raw_spike_level"] == "MEDIUM"
        else:
            assert res["raw_spike_level"] == "LOW"


def test_p4_6_action_strictly_aligns_with_final_operational_tier(detector):
    """P4.6: recommended_action always aligns with the final operational spike_level."""
    # Final LOW -> ALLOW_STANDARD_OPERATIONS
    r_low = detector.detect_spike(_get_low_spike_payload("MERCH_ACTION_LOW"))
    assert r_low["spike_level"] == "LOW"
    assert r_low["recommended_action"] == "ALLOW_STANDARD_OPERATIONS"

    # Final MEDIUM -> FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR
    r_med = detector.detect_spike(_get_medium_spike_payload("MERCH_ACTION_MED"))
    assert r_med["spike_level"] == "MEDIUM"
    assert r_med["recommended_action"] == "FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR"

    # Final HIGH (persistence escalated) -> ENABLE_STRICT_RATE_LIMITS_AND_2FA
    detector.detect_spike(_get_medium_spike_payload("MERCH_ACTION_P3"))
    detector.detect_spike(_get_medium_spike_payload("MERCH_ACTION_P3"))
    r_p3 = detector.detect_spike(_get_medium_spike_payload("MERCH_ACTION_P3"))
    assert r_p3["spike_level"] == "HIGH"
    assert r_p3["persistence_escalation_triggered"] is True
    assert r_p3["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"


def test_p4_7_api_contract_field_completeness(client):
    """P4.7: POST /risk/fraud-spike API schema contains all raw and policy transparency fields."""
    payload = _get_medium_spike_payload("MERCH_API_P4_SCHEMA")
    resp = client.post("/risk/fraud-spike", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Raw model fields
    assert "raw_spike_probability" in data
    assert "raw_spike_score" in data
    assert "raw_spike_level" in data
    assert isinstance(data["raw_spike_probability"], float)
    assert isinstance(data["raw_spike_score"], int)
    assert data["raw_spike_level"] in ("LOW", "MEDIUM", "HIGH")

    # Policy operational fields
    assert "spike_score" in data
    assert "spike_level" in data
    assert "spike_prediction" in data
    assert "recommended_action" in data

    # Guardrail & persistence context
    assert "guardrail_triggered" in data
    assert "consecutive_anomaly_windows" in data
    assert "persistence_escalation_triggered" in data
    assert isinstance(data["guardrail_triggered"], bool)
    assert isinstance(data["consecutive_anomaly_windows"], int)
    assert isinstance(data["persistence_escalation_triggered"], bool)


# =========================================================================
# P5 Policy Guardrail Tests: 5-Minute Sub-Window Telemetry
# =========================================================================

def _get_base_low_payload(merchant_id: str = "MERCH_P5_TEST") -> dict:
    """Helper returning a standard low-risk hourly observation."""
    return {
        "merchant_id": merchant_id,
        "baseline_tx_count": 2400,
        "current_tx_count": 20,
        "baseline_fraud_rate": 0.01,
        "current_fraud_rate": 0.01,
        "baseline_suspicious_score": 0.04,
        "current_suspicious_score": 0.04,
    }


def test_p5_1_no_five_minute_telemetry(detector):
    """P5.1: When no 5-minute telemetry is provided, availability is False and defaults are clean."""
    payload = _get_base_low_payload("MERCH_P5_NO_TEL")
    res = detector.detect_spike(payload)

    assert res["five_minute_telemetry_available"] is False
    assert res["five_minute_observation_count"] == 0
    assert res["five_minute_current_tx_count"] is None
    assert res["five_minute_velocity_ratio"] is None
    assert res["five_minute_guardrail_triggered"] is False
    assert res["spike_level"] == "LOW"


def test_p5_2_single_observation_insufficient_baseline(detector):
    """P5.2: A single 5-minute observation has insufficient baseline and does not escalate."""
    payload = _get_base_low_payload("MERCH_P5_SINGLE_OBS")
    payload["five_minute_telemetry"] = [
        {"timestamp": "2026-09-01T12:00:00Z", "tx_count": 50, "fraud_count": 20, "fraud_rate": 0.40}
    ]
    res = detector.detect_spike(payload)

    assert res["five_minute_telemetry_available"] is True
    assert res["five_minute_observation_count"] == 1
    assert res["five_minute_current_tx_count"] == 50
    assert res["five_minute_velocity_ratio"] is None
    assert res["five_minute_guardrail_triggered"] is False
    assert any("Insufficient 5-minute telemetry" in m for m in res["mitigating_factors"])


def test_p5_3_zero_current_activity_safe(detector):
    """P5.3: Zero transactions in the current 5-minute sub-window produces 0.0 velocity ratio and no surge."""
    payload = _get_base_low_payload("MERCH_P5_ZERO_CURR")
    payload["five_minute_telemetry"] = [
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 12, "fraud_count": 0},
        {"tx_count": 0, "fraud_count": 0},
    ]
    res = detector.detect_spike(payload)

    assert res["five_minute_telemetry_available"] is True
    assert res["five_minute_current_tx_count"] == 0
    assert res["five_minute_velocity_ratio"] == 0.0
    assert res["five_minute_guardrail_triggered"] is False
    assert any("No transaction activity observed in latest 5-minute sub-window" in m for m in res["mitigating_factors"])


def test_p5_4_zero_baseline_safe_no_infinite_surge(detector):
    """P5.4: Zero baseline sub-windows do not produce an infinite or manufactured surge."""
    payload = _get_base_low_payload("MERCH_P5_ZERO_BASE")
    payload["five_minute_telemetry"] = [
        {"tx_count": 0, "fraud_count": 0},
        {"tx_count": 0, "fraud_count": 0},
        {"tx_count": 25, "fraud_count": 0},
    ]
    res = detector.detect_spike(payload)

    assert res["five_minute_telemetry_available"] is True
    assert res["five_minute_velocity_ratio"] == 1.0  # Neutral baseline
    assert res["five_minute_guardrail_triggered"] is False


def test_p5_5_stable_normal_five_minute_traffic(detector):
    """P5.5: Normal stable 5-minute traffic maintains velocity ratio ~1.0 and does not trigger guardrail."""
    payload = _get_base_low_payload("MERCH_P5_STABLE")
    payload["five_minute_telemetry"] = [
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 11, "fraud_count": 0},
        {"tx_count": 9, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
    ]
    res = detector.detect_spike(payload)

    assert res["five_minute_telemetry_available"] is True
    assert res["five_minute_observation_count"] == 5
    assert 0.8 <= res["five_minute_velocity_ratio"] <= 1.2
    assert res["five_minute_guardrail_triggered"] is False
    assert res["spike_level"] == "LOW"


def test_p5_6_genuine_short_window_surge_with_sufficient_baseline(detector):
    """P5.6: Rapid intra-hour burst with severe fraud rate escalates LOW to MEDIUM with explicit explanation."""
    payload = _get_base_low_payload("MERCH_P5_BURST")
    payload["five_minute_telemetry"] = [
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 50, "fraud_count": 18, "fraud_rate": 0.36},  # 5x surge with 36% fraud
    ]
    res = detector.detect_spike(payload)

    assert res["five_minute_telemetry_available"] is True
    assert res["five_minute_observation_count"] == 5
    assert res["five_minute_current_tx_count"] == 50
    assert res["five_minute_velocity_ratio"] == 5.0
    assert res["five_minute_guardrail_triggered"] is True

    # Raw model remains LOW, policy escalates to MEDIUM
    assert res["raw_spike_level"] == "LOW"
    assert res["spike_level"] == "MEDIUM"
    assert res["spike_score"] >= 45
    assert res["recommended_action"] == "FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR"
    assert any("Rapid 5-minute transaction burst detected" in f for f in res["spike_factors"])
    assert "Rapid transaction activity was observed across recent 5-minute windows" in res["explanation"]


def test_p5_7_legitimate_promotional_surge_low_fraud(detector):
    """P5.7: High velocity short-window promotional surge with low fraud rate does NOT trigger guardrail."""
    payload = _get_base_low_payload("MERCH_P5_PROMO")
    payload["five_minute_telemetry"] = [
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 80, "fraud_count": 1, "fraud_rate": 0.0125},  # 8x volume, 1.25% fraud
    ]
    res = detector.detect_spike(payload)

    assert res["five_minute_telemetry_available"] is True
    assert res["five_minute_velocity_ratio"] == 8.0
    assert res["five_minute_guardrail_triggered"] is False
    assert res["spike_level"] == "LOW"
    assert any("Recent 5-minute volume surge (8.0x) corresponds to legitimate promotional traffic" in m for m in res["mitigating_factors"])


def test_p5_8_rapid_fraud_rate_increase(detector):
    """P5.8: Rapid fraud rate increase across recent 5-minute windows activates short-window guardrail."""
    payload = _get_base_low_payload("MERCH_P5_RAPID_FR")
    payload["five_minute_telemetry"] = [
        {"tx_count": 15, "fraud_count": 0},
        {"tx_count": 15, "fraud_count": 0},
        {"tx_count": 15, "fraud_count": 0},
        {"tx_count": 45, "fraud_count": 15, "fraud_rate": 0.333},  # 3x volume, 33.3% fraud
    ]
    res = detector.detect_spike(payload)

    assert res["five_minute_guardrail_triggered"] is True
    assert res["spike_level"] in ["MEDIUM", "HIGH"]
    assert res["recommended_action"] == "FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR"


def test_p5_9_merchant_isolation(detector):
    """P5.9: Telemetry store strictly isolates short-window observations by merchant_id."""
    detector.reset_tracker()

    # Merchant A gets a burst
    obs_a = [
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 50, "fraud_count": 20, "fraud_rate": 0.40},
    ]
    # Merchant B gets normal traffic
    obs_b = [
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
    ]

    p_a = _get_base_low_payload("MERCH_5MIN_ISO_A")
    p_a["five_minute_telemetry"] = obs_a
    res_a = detector.detect_spike(p_a)

    p_b = _get_base_low_payload("MERCH_5MIN_ISO_B")
    p_b["five_minute_telemetry"] = obs_b
    res_b = detector.detect_spike(p_b)

    assert res_a["five_minute_guardrail_triggered"] is True
    assert res_a["spike_level"] == "MEDIUM"

    assert res_b["five_minute_guardrail_triggered"] is False
    assert res_b["spike_level"] == "LOW"

    # Anonymous merchant stays stateless
    p_anon = _get_base_low_payload("MERCH_UNKNOWN")
    detector.detect_spike(p_anon)
    assert len(detector.telemetry_store.get_observations("MERCH_UNKNOWN")) == 0


def test_p5_10_bounded_state_eviction(detector):
    """P5.10: Telemetry store caps observations per merchant and evicts oldest merchants at capacity."""
    detector.reset_tracker()

    # Verify per-merchant window bound (max 12)
    for i in range(20):
        detector.record_five_minute_observation("MERCH_BOUNDED_WIN", {"tx_count": i, "fraud_count": 0})

    history = detector.telemetry_store.get_observations("MERCH_BOUNDED_WIN")
    assert len(history) == 12
    assert history[0]["tx_count"] == 8
    assert history[-1]["tx_count"] == 19

    # Verify max merchant capacity eviction
    from src.fraud_spike_detector import FiveMinuteTelemetryStore
    small_store = FiveMinuteTelemetryStore(max_merchants=3, max_windows_per_merchant=5)
    for m in range(5):
        small_store.record_observation(f"MERCH_{m}", {"tx_count": 10, "fraud_count": 0})

    # Oldest merchants (MERCH_0, MERCH_1) should be evicted
    assert len(small_store.get_observations("MERCH_0")) == 0
    assert len(small_store.get_observations("MERCH_1")) == 0
    assert len(small_store.get_observations("MERCH_4")) == 1


def test_p5_11_thread_safety_concurrent_recording(detector):
    """P5.11: Concurrent multi-threaded observation recording executes safely without race conditions."""
    import concurrent.futures

    detector.reset_tracker()
    merchant_id = "MERCH_CONCURRENT_P5"

    def record_chunk(val: int):
        for _ in range(5):
            detector.record_five_minute_observation(merchant_id, {"tx_count": val, "fraud_count": 0})

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(record_chunk, i) for i in range(8)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    obs = detector.telemetry_store.get_observations(merchant_id)
    assert len(obs) <= 12


def test_p5_12_raw_ml_probability_score_level_immutability(detector):
    """P5.12: P5 short-window adjustments never alter raw ML probability, score, or level."""
    payload = _get_base_low_payload("MERCH_P5_IMMUTABLE")
    payload["five_minute_telemetry"] = [
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 60, "fraud_count": 25, "fraud_rate": 0.416},
    ]
    res = detector.detect_spike(payload)

    # Raw model remains untouched
    assert res["raw_spike_level"] == "LOW"
    assert res["raw_spike_score"] < 30
    assert 0.0 <= res["raw_spike_probability"] < 0.30

    # Policy adjusts operational level
    assert res["spike_level"] == "MEDIUM"
    assert res["spike_score"] >= 45
    assert res["five_minute_guardrail_triggered"] is True


def test_p5_13_p1_guardrail_behavior_remains_intact(detector):
    """P5.13: Existing P1 hourly fraud rate delta floor operates seamlessly alongside P5."""
    payload_p1 = {
        "merchant_id": "MERCH_P1_STILL_INTACT",
        "baseline_tx_count": 2400,
        "current_tx_count": 30,
        "baseline_fraud_rate": 0.02,
        "current_fraud_rate": 0.35,
        "baseline_suspicious_score": 0.05,
        "current_suspicious_score": 0.05,
    }
    res = detector.detect_spike(payload_p1)

    assert res["guardrail_triggered"] is True
    assert res["five_minute_telemetry_available"] is False
    assert res["raw_spike_level"] == "LOW"
    assert res["spike_level"] == "MEDIUM"
    assert res["spike_score"] >= 45


def test_p5_14_p2_zero_count_behavior_remains_intact(detector):
    """P5.14: Existing P2 zero-count edge case handling remains safe and clean."""
    payload_p2 = {
        "merchant_id": "MERCH_P2_STILL_INTACT",
        "baseline_tx_count": 0,
        "current_tx_count": 0,
    }
    res = detector.detect_spike(payload_p2)

    assert res["spike_score"] == 0
    assert res["spike_level"] == "LOW"
    assert res["evidence_quality"] == "INSUFFICIENT_SAMPLE"
    assert not any("Hourly transaction volume surged" in f for f in res["spike_factors"])


def test_p5_15_p3_persistence_escalation_integration(detector):
    """P5.15: P5 short-window burst escalation integrates with P3 persistence to escalate 3x MEDIUM -> HIGH."""
    detector.reset_tracker()
    burst_payload = _get_base_low_payload("MERCH_P5_P3_INTEG")
    burst_payload["five_minute_telemetry"] = [
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 10, "fraud_count": 0},
        {"tx_count": 60, "fraud_count": 25, "fraud_rate": 0.416},
    ]

    # Eval 1
    r1 = detector.detect_spike(burst_payload)
    assert r1["five_minute_guardrail_triggered"] is True
    assert r1["spike_level"] == "MEDIUM"
    assert r1["consecutive_anomaly_windows"] == 1

    # Eval 2
    r2 = detector.detect_spike(burst_payload)
    assert r2["consecutive_anomaly_windows"] == 2
    assert r2["spike_level"] == "MEDIUM"

    # Eval 3: P3 persistence escalates to HIGH
    r3 = detector.detect_spike(burst_payload)
    assert r3["consecutive_anomaly_windows"] == 3
    assert r3["persistence_escalation_triggered"] is True
    assert r3["spike_level"] == "HIGH"
    assert r3["recommended_action"] == "ENABLE_STRICT_RATE_LIMITS_AND_2FA"

    # Subsequent LOW resets counter
    low_payload = _get_base_low_payload("MERCH_P5_P3_INTEG")
    r_low = detector.detect_spike(low_payload)
    assert r_low["spike_level"] == "LOW"
    assert r_low["consecutive_anomaly_windows"] == 0


def test_p5_16_api_endpoint_five_minute_telemetry(client):
    """P5.16: POST /risk/fraud-spike API endpoint accepts and evaluates five_minute_telemetry payload."""
    payload = {
        "merchant_id": "MERCH_API_P5_ENDPOINT",
        "baseline_window": "previous_24h",
        "current_window": "latest_1h",
        "baseline_tx_count": 2400,
        "current_tx_count": 20,
        "baseline_fraud_rate": 0.01,
        "current_fraud_rate": 0.01,
        "five_minute_telemetry": [
            {"timestamp": "2026-09-01T12:00:00Z", "tx_count": 10, "fraud_count": 0},
            {"timestamp": "2026-09-01T12:05:00Z", "tx_count": 10, "fraud_count": 0},
            {"timestamp": "2026-09-01T12:10:00Z", "tx_count": 10, "fraud_count": 0},
            {"timestamp": "2026-09-01T12:15:00Z", "tx_count": 50, "fraud_count": 20, "fraud_rate": 0.40},
        ],
    }
    resp = client.post("/risk/fraud-spike", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["five_minute_telemetry_available"] is True
    assert data["five_minute_observation_count"] == 4
    assert data["five_minute_current_tx_count"] == 50
    assert data["five_minute_velocity_ratio"] == 5.0
    assert data["five_minute_guardrail_triggered"] is True
    assert data["raw_spike_level"] == "LOW"
    assert data["spike_level"] == "MEDIUM"
    assert data["recommended_action"] == "FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR"







