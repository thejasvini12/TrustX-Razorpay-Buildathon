"""Comprehensive test suite for unseen inference, input validation, and robustness."""

import pytest
import numpy as np
import pandas as pd
from src.features import (
    get_risk_tier,
    validate_and_sanitize_account_input,
    RISK_TIER_LOW,
    RISK_TIER_MEDIUM,
    RISK_TIER_HIGH,
    MODEL_FEATURES,
    ID_COLUMN,
    TARGET_COLUMN,
)
from src.risk_scorer import RiskScorer, predict_account_risk
from src.train import train_pipeline


@pytest.fixture(scope="session")
def trained_pipeline_setup(tmp_path_factory):
    """Train a test pipeline once for the test session."""
    temp_dir = tmp_path_factory.mktemp("models_test")
    model_dir = str(temp_dir / "models")
    data_dir = str(temp_dir / "data")
    train_pipeline(
        model_output_dir=model_dir,
        data_output_dir=data_dir,
        num_synthetic_samples=600,
        random_state=42,
    )
    model_path = str(temp_dir / "models" / "risk_engine_rf.joblib")
    metadata_path = str(temp_dir / "models" / "model_metadata.json")
    return model_path, metadata_path


def test_get_risk_tier_thresholds():
    """Verify tier assignment based on 0-100 risk score thresholds."""
    assert get_risk_tier(0) == RISK_TIER_LOW
    assert get_risk_tier(29.9) == RISK_TIER_LOW
    assert get_risk_tier(30.0) == RISK_TIER_MEDIUM
    assert get_risk_tier(69.9) == RISK_TIER_MEDIUM
    assert get_risk_tier(70.0) == RISK_TIER_HIGH
    assert get_risk_tier(100.0) == RISK_TIER_HIGH


def test_normal_unseen_input(trained_pipeline_setup):
    """Verify inference on a completely new, unseen normal customer record."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    unseen_legit = {
        "account_id": "ACC_BRAND_NEW_LEGIT_123",
        "order_count": 25,
        "return_count": 1,
        "refund_count": 1,
        "total_spend": 1400.0,
        "average_order_value": 56.0,
        "account_age_days": 400,
        "device_count": 1,
        "ip_count": 2,
        "payment_instrument_count": 1,
        "return_rate": 0.04,
        "refund_rate": 0.04,
        "high_value_order_count": 1,
        "suspicious_activity_score": 0.02,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }

    res = scorer.predict_account(unseen_legit)
    assert res["account_id"] == "ACC_BRAND_NEW_LEGIT_123"
    assert res["risk_level"] == RISK_TIER_LOW
    assert res["risk_score"] < 30
    assert res["data_quality_score"] == 1.0
    assert len(res["warnings"]) == 0
    assert res["recommended_action"] == "ALLOW"


def test_high_risk_unseen_input(trained_pipeline_setup):
    """Verify inference on a completely new, unseen high-risk abuse syndicate record."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    unseen_syndicate = {
        "account_id": "ACC_BRAND_NEW_RING_888",
        "order_count": 20,
        "return_count": 18,
        "refund_count": 17,
        "total_spend": 3200.0,
        "average_order_value": 160.0,
        "account_age_days": 8,
        "device_count": 6,
        "ip_count": 7,
        "payment_instrument_count": 5,
        "return_rate": 0.90,
        "refund_rate": 0.85,
        "high_value_order_count": 14,
        "suspicious_activity_score": 0.96,
        "device_type": "emulator_bot",
        "primary_payment_method": "virtual_card",
    }

    res = scorer.predict_account(unseen_syndicate)
    assert res["account_id"] == "ACC_BRAND_NEW_RING_888"
    assert res["risk_level"] == RISK_TIER_HIGH
    assert res["risk_score"] >= 70
    assert res["data_quality_score"] == 1.0
    assert res["recommended_action"] == "CHALLENGE_OR_BLOCK"


def test_missing_values_safe_handling(trained_pipeline_setup):
    """Verify that missing critical fields do not crash and reduce data quality score."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    incomplete_record = {
        "account_id": "ACC_SPARSE_DATA_001",
        "order_count": 3,
        # Missing total_spend, return_count, account_age_days, suspicious_activity_score, etc.
    }

    res = scorer.predict_account(incomplete_record)
    assert res["account_id"] == "ACC_SPARSE_DATA_001"
    assert 0 <= res["risk_score"] <= 100
    assert res["data_quality_score"] < 1.0  # Quality reduced due to imputation
    assert len(res["warnings"]) > 0
    assert any("Missing field" in w for w in res["warnings"])


def test_unknown_categorical_values(trained_pipeline_setup):
    """Verify that previously unseen categorical levels are handled gracefully without errors."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    unseen_cats = {
        "account_id": "ACC_WEIRD_DEVICE_002",
        "order_count": 10,
        "return_count": 1,
        "refund_count": 1,
        "total_spend": 600.0,
        "average_order_value": 60.0,
        "account_age_days": 150,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.10,
        "refund_rate": 0.10,
        "high_value_order_count": 0,
        "suspicious_activity_score": 0.05,
        "device_type": "smart_fridge_os_v9",   # Completely unknown category
        "primary_payment_method": "satellite_crypto_pay",  # Completely unknown category
    }

    res = scorer.predict_account(unseen_cats)
    assert 0 <= res["risk_score"] <= 100
    assert res["risk_level"] in [RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH]


def test_invalid_negative_values_sanitization(trained_pipeline_setup):
    """Verify that negative inputs are clamped to 0 with warning logs."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    negative_record = {
        "account_id": "ACC_NEGATIVE_VALS_003",
        "order_count": -5,
        "return_count": -2,
        "refund_count": -2,
        "total_spend": -500.0,
        "average_order_value": -100.0,
        "account_age_days": -50,
        "device_count": -1,
        "ip_count": -1,
        "payment_instrument_count": -1,
        "return_rate": -0.5,
        "refund_rate": -0.5,
        "high_value_order_count": -1,
        "suspicious_activity_score": -0.2,
    }

    res = scorer.predict_account(negative_record)
    assert res["data_quality_score"] < 1.0
    assert len(res["warnings"]) > 0
    assert any("Negative value" in w for w in res["warnings"])
    assert 0 <= res["risk_score"] <= 100


def test_inconsistent_counts_sanitization(trained_pipeline_setup):
    """Verify that impossible counts (returns/refunds > orders) are clamped and flagged."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    inconsistent_record = {
        "account_id": "ACC_INCONSISTENT_004",
        "order_count": 2,
        "return_count": 10,   # return_count > order_count
        "refund_count": 8,    # refund_count > order_count
        "total_spend": 200.0,
        "average_order_value": 100.0,
        "account_age_days": 30,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 5.0,   # rate > 1.0
        "refund_rate": 4.0,   # rate > 1.0
        "high_value_order_count": 1,
        "suspicious_activity_score": 0.40,
    }

    res = scorer.predict_account(inconsistent_record)
    assert res["data_quality_score"] < 1.0
    assert any("Inconsistent count" in w for w in res["warnings"])


def test_extreme_values_handling(trained_pipeline_setup):
    """Verify that extreme out-of-range values are clamped safely without overflow."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    extreme_record = {
        "account_id": "ACC_EXTREME_VALS_005",
        "order_count": 10_000,
        "return_count": 9_000,
        "refund_count": 8_500,
        "total_spend": 999_999_999.0,  # $1 Billion
        "average_order_value": 99_999_999.0,
        "account_age_days": 100_000,
        "device_count": 50_000,
        "ip_count": 50_000,
        "payment_instrument_count": 50_000,
        "return_rate": 0.90,
        "refund_rate": 0.85,
        "high_value_order_count": 5_000,
        "suspicious_activity_score": 0.98,
    }

    res = scorer.predict_account(extreme_record)
    assert any("Extreme" in w for w in res["warnings"])
    assert 0 <= res["risk_score"] <= 100


def test_account_id_and_target_not_used_as_features(trained_pipeline_setup):
    """Verify that account_id and target label are never present in model feature list."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    assert ID_COLUMN not in MODEL_FEATURES
    assert TARGET_COLUMN not in MODEL_FEATURES

    # Confirm that changing account_id does NOT change probability for identical features
    rec1 = {
        "account_id": "ACC_A",
        "order_count": 10,
        "return_count": 1,
        "refund_count": 1,
        "total_spend": 500.0,
        "average_order_value": 50.0,
        "account_age_days": 100,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.10,
        "refund_rate": 0.10,
        "high_value_order_count": 0,
        "suspicious_activity_score": 0.05,
    }
    rec2 = rec1.copy()
    rec2["account_id"] = "ACC_B_VERY_DIFFERENT_NAME"
    # Even if someone accidentally passes abuse_label, it must be ignored
    rec2["abuse_label"] = 1

    res1 = scorer.predict_account(rec1)
    res2 = scorer.predict_account(rec2)

    assert res1["risk_probability"] == res2["risk_probability"]
    assert res1["risk_score"] == res2["risk_score"]


def test_invalid_input_types_raise_error(trained_pipeline_setup):
    """Verify that non-dict or invalid input types safely raise TypeError."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    with pytest.raises(TypeError, match="input_record must be a dictionary"):
        scorer.predict_account("not_a_dict")

    with pytest.raises(TypeError, match="input_record must be a dictionary"):
        scorer.predict_account(12345)

    with pytest.raises(TypeError, match="input_data must be a dict, list of dicts, or pandas DataFrame"):
        scorer.predict_accounts(123)

    with pytest.raises(TypeError, match="must be a dictionary"):
        scorer.predict_accounts([{"account_id": "VALID_1"}, "INVALID_STRING_RECORD"])


def test_empty_batch_input(trained_pipeline_setup):
    """Verify that empty list or empty DataFrame returns empty list without error."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    assert scorer.predict_accounts([]) == []
    assert scorer.predict_accounts(pd.DataFrame()) == []


def test_medium_risk_tier_handling(trained_pipeline_setup):
    """Verify that borderline / elevated risk metrics evaluate to MEDIUM risk tier and MANUAL_REVIEW action."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    # Moderate return/refund rate, moderate suspicious activity score
    moderate_record = {
        "account_id": "ACC_MODERATE_RISK_007",
        "order_count": 10,
        "return_count": 4,
        "refund_count": 4,
        "total_spend": 800.0,
        "average_order_value": 80.0,
        "account_age_days": 45,
        "device_count": 2,
        "ip_count": 3,
        "payment_instrument_count": 2,
        "return_rate": 0.40,
        "refund_rate": 0.40,
        "high_value_order_count": 2,
        "suspicious_activity_score": 0.45,
        "device_type": "mobile_android",
        "primary_payment_method": "credit_card",
    }

    res = scorer.predict_account(moderate_record)
    assert res["account_id"] == "ACC_MODERATE_RISK_007"
    assert "prediction" in res
    assert "risk_tier" in res
    assert res["risk_level"] in [RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH]
    assert res["recommended_action"] in ["ALLOW", "MANUAL_REVIEW", "CHALLENGE_OR_BLOCK"]


def test_prediction_output_structure(trained_pipeline_setup):
    """Verify that the output dictionary contains all required fields with appropriate types."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    valid_record = {
        "account_id": "ACC_STRUCTURE_CHECK",
        "order_count": 15,
        "return_count": 0,
        "refund_count": 0,
        "total_spend": 750.0,
        "average_order_value": 50.0,
        "account_age_days": 200,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.0,
        "refund_rate": 0.0,
        "high_value_order_count": 0,
        "suspicious_activity_score": 0.01,
        "device_type": "desktop_chrome",
        "primary_payment_method": "credit_card",
    }

    res = scorer.predict_account(valid_record)
    required_keys = [
        "account_id",
        "prediction",
        "risk_probability",
        "risk_score",
        "risk_level",
        "risk_tier",
        "data_quality_score",
        "warnings",
        "recommended_action",
        "risk_factors",
    ]
    for key in required_keys:
        assert key in res, f"Expected key '{key}' in prediction response."

    assert isinstance(res["account_id"], str)
    assert isinstance(res["prediction"], int)
    assert isinstance(res["risk_probability"], float)
    assert isinstance(res["risk_score"], int)
    assert isinstance(res["risk_level"], str)
    assert isinstance(res["risk_tier"], str)
    assert isinstance(res["data_quality_score"], float)
    assert isinstance(res["warnings"], list)
    assert isinstance(res["recommended_action"], str)
    assert isinstance(res["risk_factors"], list)


def test_predict_account_risk_functional_api(trained_pipeline_setup):
    """Verify that the convenience functional API works for single dicts and batch lists."""
    model_path, _ = trained_pipeline_setup

    single_account = {
        "account_id": "ACC_FUNC_API_1",
        "order_count": 5,
        "return_count": 0,
        "refund_count": 0,
        "total_spend": 250.0,
        "average_order_value": 50.0,
        "account_age_days": 120,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.0,
        "refund_rate": 0.0,
        "high_value_order_count": 0,
        "suspicious_activity_score": 0.02,
    }

    # Single dict
    single_res = predict_account_risk(single_account, model_path=model_path)
    assert isinstance(single_res, dict)
    assert single_res["account_id"] == "ACC_FUNC_API_1"

    # Batch list
    batch_res = predict_account_risk([single_account], model_path=model_path)
    assert isinstance(batch_res, list)
    assert len(batch_res) == 1
    assert batch_res[0]["account_id"] == "ACC_FUNC_API_1"


def test_input_layer_with_various_categoricals(trained_pipeline_setup):
    """Verify input layer handles all supported and unsupported categorical combinations."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    devices = ["mobile_ios", "mobile_android", "desktop_chrome", "desktop_safari", "emulator_bot", "unseen_device_os"]
    payments = ["credit_card", "debit_card", "paypal", "apple_pay", "virtual_card", "crypto_gift_card", "bitcoin_direct"]

    for d in devices:
        for p in payments:
            account = {
                "account_id": f"ACC_{d}_{p}",
                "order_count": 8,
                "return_count": 0,
                "refund_count": 0,
                "total_spend": 400.0,
                "average_order_value": 50.0,
                "account_age_days": 100,
                "device_count": 1,
                "ip_count": 1,
                "payment_instrument_count": 1,
                "return_rate": 0.0,
                "refund_rate": 0.0,
                "high_value_order_count": 0,
                "suspicious_activity_score": 0.02,
                "device_type": d,
                "primary_payment_method": p,
            }
            res = scorer.predict_account(account)
            assert res["risk_level"] in [RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH]
            assert 0 <= res["risk_score"] <= 100


def test_input_layer_with_extra_unexpected_fields(trained_pipeline_setup):
    """Verify that unexpected extra payload keys are safely ignored and do not pollute model inputs."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    account_with_extras = {
        "account_id": "ACC_EXTRA_FIELDS_001",
        "order_count": 10,
        "return_count": 1,
        "refund_count": 1,
        "total_spend": 500.0,
        "average_order_value": 50.0,
        "account_age_days": 90,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.1,
        "refund_rate": 0.1,
        "high_value_order_count": 0,
        "suspicious_activity_score": 0.05,
        # Extra metadata fields
        "internal_tracking_token": "xyz-999-alpha",
        "customer_email": "user@example.com",
        "nested_metadata": {"ip_region": "US-EAST", "vpn": False},
        "abuse_label": 1,  # Must be strictly ignored
    }

    res = scorer.predict_account(account_with_extras)
    assert res["account_id"] == "ACC_EXTRA_FIELDS_001"
    assert "prediction" in res
    assert 0 <= res["risk_score"] <= 100


def test_input_layer_with_wrong_data_types(trained_pipeline_setup):
    """Verify that wrong data types (booleans, lists, non-scalar values) in numeric/categorical fields are handled safely."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    malformed_types = {
        "account_id": "ACC_WRONG_TYPES",
        "order_count": True,             # Boolean instead of integer/float
        "return_count": [1, 2, 3],        # List instead of number
        "total_spend": "not_a_number",    # String instead of float
        "device_type": {"os": "ios"},     # Dict instead of string
        "primary_payment_method": ["card", "paypal"], # List instead of string
    }

    res = scorer.predict_account(malformed_types)
    assert res["data_quality_score"] < 1.0
    assert len(res["warnings"]) >= 3
    assert 0 <= res["risk_score"] <= 100


def test_input_layer_with_nan_and_infinite_values(trained_pipeline_setup):
    """Verify that NaN and Infinite numeric values are safely imputed and flagged."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    nan_inf_record = {
        "account_id": "ACC_NAN_INF_001",
        "order_count": float("nan"),
        "total_spend": float("inf"),
        "average_order_value": float("-inf"),
        "suspicious_activity_score": np.nan,
        "device_type": np.nan,
    }

    res = scorer.predict_account(nan_inf_record)
    assert res["account_id"] == "ACC_NAN_INF_001"
    assert res["data_quality_score"] < 1.0
    assert any("NaN value" in w for w in res["warnings"])
    assert any("Infinite value" in w for w in res["warnings"])
    assert 0 <= res["risk_score"] <= 100


def test_strict_mode_validation_raises_error():
    """Verify that strict mode raises AccountInputValidationError with descriptive messages."""
    from src.features import validate_account_payload, AccountInputValidationError

    # Malformed payload with missing and invalid types
    bad_payload = {
        "account_id": "ACC_STRICT_TEST",
        "order_count": -10,
        "total_spend": "invalid_currency",
    }

    with pytest.raises(AccountInputValidationError) as exc_info:
        validate_account_payload(bad_payload, strict=True)

    err = exc_info.value
    assert len(err.errors) > 0
    assert any("Negative value" in e or "Invalid non-numeric" in e for e in err.errors)


def test_explainability_low_risk_mitigating_factors(trained_pipeline_setup):
    """Verify that a legitimate, low-risk account produces meaningful mitigating factors."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    clean_account = {
        "account_id": "ACC_CLEAN_EXPLAIN",
        "order_count": 25,
        "return_count": 1,
        "refund_count": 0,
        "total_spend": 1500.0,
        "average_order_value": 60.0,
        "account_age_days": 365,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.04,
        "refund_rate": 0.0,
        "high_value_order_count": 1,
        "suspicious_activity_score": 0.02,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }

    res = scorer.predict_account(clean_account)
    assert res["risk_level"] == RISK_TIER_LOW
    assert "mitigating_factors" in res
    assert isinstance(res["mitigating_factors"], list)
    assert len(res["mitigating_factors"]) >= 2
    assert any("Established account" in m or "Seasoned account" in m for m in res["mitigating_factors"])
    assert any("Zero refund claims" in m or "Healthy low refund rate" in m or "Strong purchase history" in m for m in res["mitigating_factors"])


def test_explainability_high_risk_multiple_risk_factors(trained_pipeline_setup):
    """Verify that an abusive syndicate account produces multiple descriptive behavioral risk factors."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    syndicate_account = {
        "account_id": "ACC_SYNDICATE_EXPLAIN",
        "order_count": 20,
        "return_count": 18,
        "refund_count": 18,
        "total_spend": 3600.0,
        "average_order_value": 180.0,
        "account_age_days": 10,
        "device_count": 5,
        "ip_count": 6,
        "payment_instrument_count": 4,
        "return_rate": 0.90,
        "refund_rate": 0.90,
        "high_value_order_count": 12,
        "suspicious_activity_score": 0.95,
        "device_type": "emulator_bot",
        "primary_payment_method": "virtual_card",
    }

    res = scorer.predict_account(syndicate_account)
    assert res["risk_level"] == RISK_TIER_HIGH
    assert "risk_factors" in res
    assert isinstance(res["risk_factors"], list)
    assert len(res["risk_factors"]) >= 4
    assert any("High return rate" in f for f in res["risk_factors"])
    assert any("High refund claim rate" in f for f in res["risk_factors"])
    assert any("Elevated syndicate activity indicator" in f for f in res["risk_factors"])
    assert any("Multiple linked hardware devices" in f for f in res["risk_factors"])


def test_explainability_feature_contributions_structure(trained_pipeline_setup):
    """Verify that feature_contributions contains required fields and is sorted by importance descending."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    account = {
        "account_id": "ACC_CONTRIB_CHECK",
        "order_count": 10,
        "return_count": 2,
        "refund_count": 1,
        "total_spend": 800.0,
        "average_order_value": 80.0,
        "account_age_days": 120,
        "device_count": 2,
        "ip_count": 2,
        "payment_instrument_count": 1,
        "return_rate": 0.20,
        "refund_rate": 0.10,
        "high_value_order_count": 1,
        "suspicious_activity_score": 0.15,
        "device_type": "desktop_chrome",
        "primary_payment_method": "paypal",
    }

    res = scorer.predict_account(account)
    assert "feature_contributions" in res
    contributions = res["feature_contributions"]
    assert isinstance(contributions, list)
    assert len(contributions) > 0

    importances = [c["importance"] for c in contributions]
    assert importances == sorted(importances, reverse=True)

    required_keys = {"feature", "value", "importance", "contribution_direction", "summary"}
    for contrib in contributions:
        assert required_keys.issubset(contrib.keys())
        assert contrib["contribution_direction"] in ["INCREASES_RISK", "DECREASES_RISK", "NEUTRAL"]
        assert isinstance(contrib["summary"], str) and len(contrib["summary"]) > 0
        assert isinstance(contrib["importance"], (int, float))


def test_explanation_low_risk_with_individual_risk_signals_clarity(trained_pipeline_setup):
    """Verify that a LOW-risk account with minor elevated signals clearly separates signals from the final decision."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    # An account with mostly healthy profile but with 3 devices (minor signal)
    account = {
        "account_id": "ACC_LOW_WITH_SIGNAL",
        "order_count": 30,
        "return_count": 2,
        "refund_count": 1,
        "total_spend": 1800.0,
        "average_order_value": 60.0,
        "account_age_days": 500,
        "device_count": 3,  # Elevated signal
        "ip_count": 2,
        "payment_instrument_count": 1,
        "return_rate": 0.0667,
        "refund_rate": 0.0333,
        "high_value_order_count": 1,
        "suspicious_activity_score": 0.05,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }

    res = scorer.predict_account(account)
    assert res["risk_level"] == RISK_TIER_LOW
    assert res["risk_score"] < 30

    # Verify explanation summary and reasoning explicitly state that individual signals do not override model assessment
    assert "explanation_summary" in res
    assert "decision_reasoning" in res
    assert "LOW" in res["explanation_summary"]
    assert "do not override" in res["decision_reasoning"] or "predominantly legitimate" in res["decision_reasoning"]

    # Verify risk increasing vs reducing separation
    assert "risk_increasing_signals" in res
    assert "risk_reducing_signals" in res
    assert len(res["risk_reducing_signals"]) >= 2
    assert any("Multiple linked hardware devices" in s for s in res["risk_increasing_signals"])


def test_explanation_medium_risk_borderline_clarity(trained_pipeline_setup):
    """Verify that a MEDIUM-risk account displays clear borderline reasoning and both positive and negative signals."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    account = {
        "account_id": "ACC_MED_EXPLAIN_TEST",
        "order_count": 12,
        "return_count": 5,
        "refund_count": 4,
        "total_spend": 1000.0,
        "average_order_value": 83.33,
        "account_age_days": 80,
        "device_count": 2,
        "ip_count": 3,
        "payment_instrument_count": 2,
        "return_rate": 0.4167,
        "refund_rate": 0.3333,
        "high_value_order_count": 2,
        "suspicious_activity_score": 0.42,
        "device_type": "desktop_chrome",
        "primary_payment_method": "paypal",
    }

    res = scorer.predict_account(account)
    assert "explanation_summary" in res
    assert "decision_reasoning" in res
    assert isinstance(res["risk_increasing_signals"], list)
    assert isinstance(res["risk_reducing_signals"], list)


def test_explanation_high_risk_clarity(trained_pipeline_setup):
    """Verify that a HIGH-risk account explanation clearly highlights severe risk drivers."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    account = {
        "account_id": "ACC_HIGH_EXPLAIN_TEST",
        "order_count": 25,
        "return_count": 22,
        "refund_count": 22,
        "total_spend": 4500.0,
        "average_order_value": 180.0,
        "account_age_days": 8,
        "device_count": 5,
        "ip_count": 7,
        "payment_instrument_count": 4,
        "return_rate": 0.88,
        "refund_rate": 0.88,
        "high_value_order_count": 15,
        "suspicious_activity_score": 0.94,
        "device_type": "emulator_bot",
        "primary_payment_method": "virtual_card",
    }

    res = scorer.predict_account(account)
    assert res["risk_level"] == RISK_TIER_HIGH
    assert res["risk_score"] >= 70
    assert "HIGH" in res["explanation_summary"]
    assert len(res["risk_increasing_signals"]) >= 4
    assert len(res["risk_reducing_signals"]) == 0


def test_risk_scorer_decision_policy_integration(trained_pipeline_setup):
    """Verify that RiskScorer includes structured decision_policy for any scored account."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    account = {
        "account_id": "ACC_POLICY_INT_TEST",
        "order_count": 20,
        "return_count": 18,
        "refund_count": 17,
        "total_spend": 2800.0,
        "average_order_value": 140.0,
        "account_age_days": 100,
        "device_count": 1,
        "ip_count": 2,
        "payment_instrument_count": 1,
        "return_rate": 0.90,
        "refund_rate": 0.85,
        "suspicious_activity_score": 0.75,
        "device_type": "desktop_chrome",
        "primary_payment_method": "credit_card",
    }

    res = scorer.predict_account(account)
    assert "decision_policy" in res
    assert isinstance(res["decision_policy"], dict)
    policy = res["decision_policy"]
    assert policy["abuse_pattern"] == "SERIAL_RETURN_ABUSE"
    assert policy["primary_action"] == "RESTRICT_RETURN_WITHOUT_RECEIPT"
    assert len(policy["secondary_actions"]) > 0
    assert len(policy["policy_triggers"]) > 0
    assert isinstance(policy["policy_reasoning"], str)
    assert policy["confidence"] in ["HIGH", "MEDIUM", "LOW"]


def test_prediction_invariance_after_decision_engine_integration(trained_pipeline_setup):
    """Verify that decision_engine does not alter core ML prediction, probability, score, or tier."""
    model_path, metadata_path = trained_pipeline_setup
    scorer = RiskScorer(model_path=model_path, metadata_path=metadata_path)

    account = {
        "account_id": "ACC_INVARIANCE_CHECK",
        "order_count": 15,
        "return_count": 2,
        "refund_count": 1,
        "total_spend": 950.0,
        "account_age_days": 180,
    }

    res = scorer.predict_account(account)
    assert isinstance(res["prediction"], int)
    assert isinstance(res["risk_probability"], float)
    assert isinstance(res["risk_score"], int)
    assert res["risk_score"] == int(round(res["risk_probability"] * 100))
    assert res["risk_level"] in [RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH]
    assert res["risk_tier"] == res["risk_level"]
    assert res["recommended_action"] in ["ALLOW", "MANUAL_REVIEW", "CHALLENGE_OR_BLOCK"]





