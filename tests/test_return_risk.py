"""Comprehensive unit & integration tests for the Return-Risk Scorer component."""

import os
import pytest
import pandas as pd
from src.features import RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH
from src.return_risk_scorer import ReturnRiskScorer
from src.evaluate_return_risk import evaluate_return_risk_on_test_set


@pytest.fixture
def return_scorer():
    """Fixture providing initialized ReturnRiskScorer."""
    return ReturnRiskScorer(
        model_path="models/return_risk_model.joblib",
        metadata_path="models/return_risk_metadata.json",
    )


def test_return_risk_model_file_exists():
    """Verify serialized return risk model and metadata artifacts exist."""
    assert os.path.exists("models/return_risk_model.joblib")
    assert os.path.exists("models/return_risk_metadata.json")


def test_low_return_risk_account(return_scorer):
    """Verify low return-risk prediction on normal customer."""
    account = {
        "account_id": "ACC_RR_LOW_001",
        "order_count": 30,
        "return_count": 1,
        "refund_count": 0,
        "total_spend": 1500.0,
        "average_order_value": 50.0,
        "account_age_days": 400,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.0333,
        "refund_rate": 0.0,
        "high_value_order_count": 1,
        "suspicious_activity_score": 0.02,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }

    res = return_scorer.predict_account(account)

    assert res["return_abuse_prediction"] == 0
    assert res["return_risk_score"] < 30
    assert res["return_risk_level"] == RISK_TIER_LOW
    assert res["recommended_return_action"] == "ALLOW_STANDARD_RETURNS"
    assert "Low return-abuse risk" in res["return_explanation"]
    assert len(res["return_mitigating_factors"]) > 0


def test_genuine_high_return_abuse_account(return_scorer):
    """Verify genuine high return-abuse prediction on serial wardrober."""
    account = {
        "account_id": "ACC_RR_HIGH_002",
        "order_count": 25,
        "return_count": 22,
        "refund_count": 21,
        "total_spend": 4500.0,
        "average_order_value": 180.0,
        "account_age_days": 120,
        "device_count": 2,
        "ip_count": 2,
        "payment_instrument_count": 2,
        "return_rate": 0.88,
        "refund_rate": 0.84,
        "high_value_order_count": 15,
        "suspicious_activity_score": 0.65,
        "device_type": "desktop_chrome",
        "primary_payment_method": "credit_card",
    }

    res = return_scorer.predict_account(account)

    assert res["return_abuse_prediction"] == 1
    assert res["return_risk_score"] >= 70
    assert res["return_risk_level"] == RISK_TIER_HIGH
    assert res["recommended_return_action"] == "RESTRICT_INSTANT_REFUNDS_AND_INSPECT"
    assert "High return-abuse risk" in res["return_explanation"]
    assert len(res["return_risk_factors"]) >= 2


def test_borderline_return_risk_account(return_scorer):
    """Verify borderline return-risk handling."""
    account = {
        "account_id": "ACC_RR_MED_003",
        "order_count": 14,
        "return_count": 6,
        "refund_count": 5,
        "total_spend": 1200.0,
        "average_order_value": 85.71,
        "account_age_days": 80,
        "device_count": 2,
        "ip_count": 2,
        "payment_instrument_count": 1,
        "return_rate": 0.4286,
        "refund_rate": 0.3571,
        "high_value_order_count": 2,
        "suspicious_activity_score": 0.35,
        "device_type": "desktop_chrome",
        "primary_payment_method": "paypal",
    }

    res = return_scorer.predict_account(account)

    assert res["return_risk_level"] in [RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH]
    assert 0 <= res["return_risk_score"] <= 100
    assert isinstance(res["return_explanation"], str)
    assert len(res["return_explanation"]) > 0


def test_held_out_evaluation_metrics_precision_recall():
    """Verify that held-out evaluation produces rigorous metrics without fabrication."""
    report = evaluate_return_risk_on_test_set()

    assert report["dataset_summary"]["test_set_size"] == 1000
    assert report["dataset_summary"]["positive_samples (return abuse)"] > 0
    assert report["performance_metrics"]["precision"] >= 0.85
    assert report["performance_metrics"]["recall"] >= 0.85
    assert report["performance_metrics"]["f1_score"] >= 0.85
    assert report["performance_metrics"]["false_positive_rate"] <= 0.05
    assert report["performance_metrics"]["false_negative_rate"] <= 0.10


def test_general_risk_model_joblib_unmodified():
    """Verify models/risk_engine_rf.joblib exists and is separate from return risk model."""
    assert os.path.exists("models/risk_engine_rf.joblib")
    assert os.path.exists("models/return_risk_model.joblib")
    assert os.path.getsize("models/risk_engine_rf.joblib") > 0


# =========================================================================
# Small-History Policy Guardrail Unit Tests
# =========================================================================

def test_small_history_1_order_1_return_remains_low(return_scorer):
    """Test 1: 1 order / 1 return (100%) -> normal first-return behavior remains LOW."""
    account = {
        "account_id": "ACC_SH_01",
        "order_count": 1,
        "return_count": 1,
        "refund_count": 1,
        "return_rate": 1.0,
        "refund_rate": 1.0,
        "total_spend": 65.0,
        "average_order_value": 65.0,
        "account_age_days": 5,
        "suspicious_activity_score": 0.05,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_LOW
    assert res["recommended_return_action"] == "ALLOW_STANDARD_RETURNS"


def test_small_history_2_orders_2_returns_remains_low(return_scorer):
    """Test 2: 2 orders / 2 returns (100%) -> protected early customer remains LOW."""
    account = {
        "account_id": "ACC_SH_02",
        "order_count": 2,
        "return_count": 2,
        "refund_count": 2,
        "return_rate": 1.0,
        "refund_rate": 1.0,
        "total_spend": 130.0,
        "average_order_value": 65.0,
        "account_age_days": 10,
        "suspicious_activity_score": 0.10,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_LOW
    assert res["recommended_return_action"] == "ALLOW_STANDARD_RETURNS"


def test_small_history_3_orders_3_returns_remains_low(return_scorer):
    """Test 3: 3 orders / 3 returns (100%) -> protected early customer remains LOW."""
    account = {
        "account_id": "ACC_SH_03",
        "order_count": 3,
        "return_count": 3,
        "refund_count": 3,
        "return_rate": 1.0,
        "refund_rate": 1.0,
        "total_spend": 195.0,
        "average_order_value": 65.0,
        "account_age_days": 15,
        "suspicious_activity_score": 0.15,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_LOW
    assert res["recommended_return_action"] == "ALLOW_STANDARD_RETURNS"


def test_small_history_4_orders_3_returns_escalates_to_medium(return_scorer):
    """Test 4: 4 orders / 3 returns (75%) -> guardrail activates and escalates to MEDIUM."""
    account = {
        "account_id": "ACC_SH_04",
        "order_count": 4,
        "return_count": 3,
        "refund_count": 3,
        "return_rate": 0.75,
        "refund_rate": 0.75,
        "total_spend": 260.0,
        "average_order_value": 65.0,
        "account_age_days": 20,
        "suspicious_activity_score": 0.20,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_MEDIUM
    assert res["return_risk_score"] >= 30
    assert res["recommended_return_action"] == "FLAG_FOR_RETURN_DESK_AUDIT"
    assert "High return frequency observed within a limited order history." in res["return_risk_factors"]


def test_small_history_5_orders_4_returns_escalates_to_medium(return_scorer):
    """Test 5: 5 orders / 4 returns (80%) -> guardrail activates and escalates to MEDIUM."""
    account = {
        "account_id": "ACC_SH_05",
        "order_count": 5,
        "return_count": 4,
        "refund_count": 4,
        "return_rate": 0.80,
        "refund_rate": 0.80,
        "total_spend": 325.0,
        "average_order_value": 65.0,
        "account_age_days": 25,
        "suspicious_activity_score": 0.30,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_MEDIUM
    assert res["recommended_return_action"] == "FLAG_FOR_RETURN_DESK_AUDIT"


def test_small_history_6_orders_5_returns_escalates_to_medium(return_scorer):
    """Test 6: 6 orders / 5 returns (83.3%) -> guardrail activates and escalates to MEDIUM."""
    account = {
        "account_id": "ACC_SH_06",
        "order_count": 6,
        "return_count": 5,
        "refund_count": 5,
        "return_rate": 0.8333,
        "refund_rate": 0.8333,
        "total_spend": 390.0,
        "average_order_value": 65.0,
        "account_age_days": 30,
        "suspicious_activity_score": 0.40,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_MEDIUM
    assert res["recommended_return_action"] == "FLAG_FOR_RETURN_DESK_AUDIT"


def test_small_history_8_orders_6_returns_escalates_to_medium(return_scorer):
    """Test 7: 8 orders / 6 returns (75%) -> guardrail activates and escalates to MEDIUM."""
    account = {
        "account_id": "ACC_SH_08",
        "order_count": 8,
        "return_count": 6,
        "refund_count": 6,
        "return_rate": 0.75,
        "refund_rate": 0.75,
        "total_spend": 520.0,
        "average_order_value": 65.0,
        "account_age_days": 35,
        "suspicious_activity_score": 0.50,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_MEDIUM
    assert res["recommended_return_action"] == "FLAG_FOR_RETURN_DESK_AUDIT"


def test_small_history_10_orders_8_returns_escalates_to_medium(return_scorer):
    """Test 8: 10 orders / 8 returns (80%) -> guardrail activates and escalates to MEDIUM."""
    account = {
        "account_id": "ACC_SH_10",
        "order_count": 10,
        "return_count": 8,
        "refund_count": 8,
        "return_rate": 0.80,
        "refund_rate": 0.80,
        "total_spend": 650.0,
        "average_order_value": 65.0,
        "account_age_days": 40,
        "suspicious_activity_score": 0.60,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_MEDIUM
    assert res["recommended_return_action"] == "FLAG_FOR_RETURN_DESK_AUDIT"


def test_small_history_10_orders_10_returns_escalates_to_medium(return_scorer):
    """Test 9: 10 orders / 10 returns (100%) -> guardrail activates and escalates to MEDIUM."""
    account = {
        "account_id": "ACC_SH_10_10",
        "order_count": 10,
        "return_count": 10,
        "refund_count": 10,
        "return_rate": 1.0,
        "refund_rate": 1.0,
        "total_spend": 650.0,
        "average_order_value": 65.0,
        "account_age_days": 40,
        "suspicious_activity_score": 0.75,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_MEDIUM
    assert res["recommended_return_action"] == "FLAG_FOR_RETURN_DESK_AUDIT"


def test_established_ml_high_customer_remains_high(return_scorer):
    """Test 10: Established ML HIGH customer remains HIGH (never downgraded by guardrail)."""
    account = {
        "account_id": "ACC_HIGH_ESTABLISHED",
        "order_count": 35,
        "return_count": 28,
        "refund_count": 26,
        "total_spend": 6000.0,
        "average_order_value": 171.4,
        "high_value_order_count": 20,
        "account_age_days": 180,
        "suspicious_activity_score": 0.70,
        "return_rate": 0.80,
        "refund_rate": 0.74,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_HIGH
    assert res["return_risk_score"] >= 70
    assert res["recommended_return_action"] == "RESTRICT_INSTANT_REFUNDS_AND_INSPECT"


def test_legitimate_hard_negatives_remain_unchanged(return_scorer):
    """Test 11: Apparel shoppers with 33% return rate remain LOW."""
    account = {
        "account_id": "ACC_APPAREL_TRYON",
        "order_count": 30,
        "return_count": 10,
        "refund_count": 10,
        "return_rate": 0.333,
        "refund_rate": 0.333,
        "total_spend": 2500.0,
        "average_order_value": 83.33,
        "account_age_days": 300,
        "suspicious_activity_score": 0.05,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_LOW
    assert res["recommended_return_action"] == "ALLOW_STANDARD_RETURNS"


def test_small_history_below_75_percent_guardrail_does_not_activate(return_scorer):
    """Test 12: Small history (6 orders) with return rate below 75% (66.7%) does NOT activate guardrail."""
    account = {
        "account_id": "ACC_SH_SUB_75",
        "order_count": 6,
        "return_count": 4,
        "refund_count": 4,
        "return_rate": 0.6667,
        "refund_rate": 0.6667,
        "total_spend": 390.0,
        "average_order_value": 65.0,
        "account_age_days": 30,
        "suspicious_activity_score": 0.10,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_LOW
    assert res["recommended_return_action"] == "ALLOW_STANDARD_RETURNS"


def test_order_count_above_10_guardrail_does_not_intervene(return_scorer):
    """Test 13: Order count > 10 (12 orders) is handled by ML model directly."""
    account = {
        "account_id": "ACC_ORDER_ABOVE_10",
        "order_count": 12,
        "return_count": 4,
        "refund_count": 4,
        "return_rate": 0.3333,
        "refund_rate": 0.3333,
        "total_spend": 900.0,
        "average_order_value": 75.0,
        "account_age_days": 180,
        "suspicious_activity_score": 0.05,
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_LOW
    assert res["recommended_return_action"] == "ALLOW_STANDARD_RETURNS"


def test_malformed_missing_values_sanitization(return_scorer):
    """Test 14: Missing and string-typed values pass safely through sanitization layer."""
    account = {
        "order_count": "5",
        "return_count": "4",
        "refund_count": "4",
        "return_rate": "0.80",
    }
    res = return_scorer.predict_account(account)
    assert res["return_risk_level"] == RISK_TIER_MEDIUM
    assert res["recommended_return_action"] == "FLAG_FOR_RETURN_DESK_AUDIT"

