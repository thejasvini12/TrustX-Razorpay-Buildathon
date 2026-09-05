"""Comprehensive API test suite for FastAPI backend endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api import app, get_scorer
from src.features import RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH


@pytest.fixture
def client():
    """Create a FastAPI TestClient."""
    return TestClient(app)


def test_health_endpoint(client):
    """Verify that GET /health returns 200, healthy status, and confirms ML model is loaded."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "AI-RISK Abuse Detection Engine"
    assert data["model_loaded"] is True
    assert "version" in data


def test_score_valid_low_risk_account(client):
    """Verify POST /risk/score on a legitimate normal merchant account."""
    payload = {
        "account_id": "ACC_API_LEGIT_001",
        "order_count": 30,
        "return_count": 1,
        "refund_count": 0,
        "total_spend": 2500.0,
        "average_order_value": 83.33,
        "account_age_days": 500,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.033,
        "refund_rate": 0.0,
        "high_value_order_count": 2,
        "suspicious_activity_score": 0.01,
        "device_type": "desktop_chrome",
        "primary_payment_method": "credit_card",
    }
    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["account_id"] == "ACC_API_LEGIT_001"
    assert data["prediction"] == 0
    assert data["risk_score"] < 30
    assert data["risk_level"] == RISK_TIER_LOW
    assert data["risk_tier"] == RISK_TIER_LOW
    assert data["recommended_action"] == "ALLOW"
    assert data["data_quality_score"] == 1.0
    assert isinstance(data["risk_factors"], list)


def test_score_valid_high_risk_account(client):
    """Verify POST /risk/score on an abusive coordinated fraud syndicate account."""
    payload = {
        "account_id": "ACC_API_SYNDICATE_999",
        "order_count": 25,
        "return_count": 22,
        "refund_count": 20,
        "total_spend": 4500.0,
        "average_order_value": 180.0,
        "account_age_days": 7,
        "device_count": 6,
        "ip_count": 8,
        "payment_instrument_count": 5,
        "return_rate": 0.88,
        "refund_rate": 0.80,
        "high_value_order_count": 15,
        "suspicious_activity_score": 0.95,
        "device_type": "emulator_bot",
        "primary_payment_method": "virtual_card",
    }
    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["account_id"] == "ACC_API_SYNDICATE_999"
    assert data["prediction"] == 1
    assert data["risk_score"] >= 70
    assert data["risk_level"] == RISK_TIER_HIGH
    assert data["risk_tier"] == RISK_TIER_HIGH
    assert data["recommended_action"] == "CHALLENGE_OR_BLOCK"
    assert len(data["risk_factors"]) > 0


def test_score_valid_medium_risk_account(client):
    """Verify POST /risk/score on an elevated/borderline merchant account."""
    payload = {
        "account_id": "ACC_API_MEDIUM_002",
        "order_count": 10,
        "return_count": 4,
        "refund_count": 3,
        "total_spend": 800.0,
        "average_order_value": 80.0,
        "account_age_days": 40,
        "device_count": 3,
        "ip_count": 4,
        "payment_instrument_count": 2,
        "return_rate": 0.40,
        "refund_rate": 0.30,
        "high_value_order_count": 1,
        "suspicious_activity_score": 0.45,
        "device_type": "mobile_android",
        "primary_payment_method": "paypal",
    }
    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["account_id"] == "ACC_API_MEDIUM_002"
    assert data["risk_level"] in [RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH]
    assert data["recommended_action"] in ["ALLOW", "MANUAL_REVIEW", "CHALLENGE_OR_BLOCK"]


def test_score_missing_fields_safe_handling(client):
    """Verify POST /risk/score safely handles missing fields by imputing defaults."""
    payload = {
        "account_id": "ACC_API_SPARSE_003",
        "order_count": 5,
        # Missing total_spend, return_count, account_age_days, etc.
    }
    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["account_id"] == "ACC_API_SPARSE_003"
    assert 0 <= data["risk_score"] <= 100
    assert data["data_quality_score"] < 1.0
    assert len(data["warnings"]) > 0


def test_score_extra_unexpected_fields(client):
    """Verify POST /risk/score safely accepts and ignores extra metadata fields."""
    payload = {
        "account_id": "ACC_API_EXTRAS_004",
        "order_count": 12,
        "total_spend": 600.0,
        "extra_custom_metadata": "ignored_field",
        "internal_user_notes": "vip merchant",
    }
    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "ACC_API_EXTRAS_004"


def test_score_response_schema_completeness(client):
    """Verify all expected keys and types exist in the API response."""
    payload = {
        "account_id": "ACC_SCHEMA_CHECK",
        "order_count": 10,
    }
    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    expected_keys = [
        "account_id",
        "prediction",
        "risk_probability",
        "risk_score",
        "risk_level",
        "risk_tier",
        "data_quality_score",
        "warnings",
        "recommended_action",
        "explanation_summary",
        "decision_reasoning",
        "risk_increasing_signals",
        "risk_reducing_signals",
        "risk_factors",
        "mitigating_factors",
        "feature_contributions",
        "decision_policy",
        "return_risk",
    ]
    for key in expected_keys:
        assert key in data, f"Key '{key}' missing from API response."

    assert isinstance(data["account_id"], str)
    assert isinstance(data["prediction"], int)
    assert isinstance(data["risk_probability"], float)
    assert isinstance(data["risk_score"], int)
    assert isinstance(data["risk_level"], str)
    assert isinstance(data["risk_tier"], str)
    assert isinstance(data["data_quality_score"], float)
    assert isinstance(data["warnings"], list)
    assert isinstance(data["recommended_action"], str)
    assert isinstance(data["explanation_summary"], str)
    assert isinstance(data["decision_reasoning"], str)
    assert isinstance(data["risk_increasing_signals"], list)
    assert isinstance(data["risk_reducing_signals"], list)
    assert isinstance(data["risk_factors"], list)
    assert isinstance(data["mitigating_factors"], list)
    assert isinstance(data["feature_contributions"], list)
    assert isinstance(data["decision_policy"], dict)
    assert isinstance(data["return_risk"], dict)

    policy = data["decision_policy"]
    policy_required_keys = ["abuse_pattern", "primary_action", "secondary_actions", "policy_triggers", "policy_reasoning", "confidence"]
    for pkey in policy_required_keys:
        assert pkey in policy, f"Key '{pkey}' missing from decision_policy."

    rr = data["return_risk"]
    rr_required_keys = [
        "return_abuse_prediction",
        "return_risk_probability",
        "return_risk_score",
        "return_risk_level",
        "return_risk_factors",
        "return_mitigating_factors",
        "return_explanation",
        "recommended_return_action",
    ]
    for rrkey in rr_required_keys:
        assert rrkey in rr, f"Key '{rrkey}' missing from return_risk."


def test_invalid_json_body(client):
    """Verify unparseable / malformed request bodies return 422."""
    response = client.post(
        "/risk/score",
        content="not_valid_json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_api_uses_existing_risk_scorer(client):
    """Verify the API endpoint utilizes the singleton RiskScorer instance."""
    scorer = get_scorer()
    assert scorer is not None
    assert scorer.pipeline is not None

    payload = {"account_id": "ACC_DIRECT_VS_API", "order_count": 15, "total_spend": 900.0}
    direct_res = scorer.predict_account(payload)
    api_res = client.post("/risk/score", json=payload).json()

    assert direct_res["risk_score"] == api_res["risk_score"]
    assert direct_res["risk_level"] == api_res["risk_level"]
    assert direct_res["risk_probability"] == api_res["risk_probability"]
    assert direct_res["risk_factors"] == api_res["risk_factors"]
    assert direct_res["mitigating_factors"] == api_res["mitigating_factors"]
    assert direct_res["decision_policy"] == api_res["decision_policy"]


def test_api_explainability_feature_contributions(client):
    """Verify API returns sorted feature contributions with required keys for low and high risk accounts."""
    low_payload = {
        "account_id": "ACC_API_LOW_EXPLAIN",
        "order_count": 20,
        "return_count": 0,
        "refund_count": 0,
        "total_spend": 1200.0,
        "account_age_days": 300,
        "suspicious_activity_score": 0.01,
    }
    low_resp = client.post("/risk/score", json=low_payload)
    assert low_resp.status_code == 200
    low_data = low_resp.json()

    assert len(low_data["mitigating_factors"]) > 0
    assert len(low_data["feature_contributions"]) > 0

    first_contrib = low_data["feature_contributions"][0]
    assert "feature" in first_contrib
    assert "value" in first_contrib
    assert "importance" in first_contrib
    assert "contribution_direction" in first_contrib
    assert "summary" in first_contrib

    # Check importance ranking
    imps = [c["importance"] for c in low_data["feature_contributions"]]
    assert imps == sorted(imps, reverse=True)


def test_api_decision_policy_low_risk_account(client):
    """Verify API decision_policy for LOW-risk account maps to LOW_RISK_STANDARD and ALLOW_STANDARD."""
    payload = {
        "account_id": "ACC_API_LOW_POLICY",
        "order_count": 20,
        "return_count": 1,
        "refund_count": 0,
        "total_spend": 1000.0,
        "account_age_days": 200,
        "suspicious_activity_score": 0.02,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }
    resp = client.post("/risk/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["risk_level"] == RISK_TIER_LOW
    assert data["recommended_action"] == "ALLOW"
    assert data["decision_policy"]["abuse_pattern"] == "LOW_RISK_STANDARD"
    assert data["decision_policy"]["primary_action"] == "ALLOW_STANDARD"
    assert len(data["decision_policy"]["secondary_actions"]) > 0
    assert len(data["decision_policy"]["policy_triggers"]) > 0


def test_api_decision_policy_serial_return_account(client):
    """Verify API decision_policy for serial return account produces SERIAL_RETURN_ABUSE."""
    payload = {
        "account_id": "ACC_API_WARDROBE_POLICY",
        "order_count": 20,
        "return_count": 17,
        "refund_count": 16,
        "total_spend": 3200.0,
        "average_order_value": 160.0,
        "account_age_days": 150,
        "device_count": 1,
        "ip_count": 2,
        "payment_instrument_count": 1,
        "return_rate": 0.85,
        "refund_rate": 0.80,
        "suspicious_activity_score": 0.70,
        "device_type": "desktop_chrome",
        "primary_payment_method": "credit_card",
    }
    resp = client.post("/risk/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["risk_level"] == RISK_TIER_HIGH
    assert data["recommended_action"] == "CHALLENGE_OR_BLOCK"
    assert data["decision_policy"]["abuse_pattern"] == "SERIAL_RETURN_ABUSE"
    assert data["decision_policy"]["primary_action"] == "RESTRICT_RETURN_WITHOUT_RECEIPT"


def test_api_decision_policy_bot_automation_account(client):
    """Verify API decision_policy for bot/emulator account produces BOT_OR_AUTOMATION."""
    payload = {
        "account_id": "ACC_API_BOT_POLICY",
        "order_count": 20,
        "return_count": 16,
        "refund_count": 16,
        "total_spend": 1000.0,
        "account_age_days": 5,
        "device_count": 4,
        "ip_count": 5,
        "payment_instrument_count": 3,
        "return_rate": 0.80,
        "refund_rate": 0.80,
        "suspicious_activity_score": 0.95,
        "device_type": "emulator_bot",
        "primary_payment_method": "virtual_card",
    }
    resp = client.post("/risk/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["risk_level"] == RISK_TIER_HIGH
    assert data["decision_policy"]["abuse_pattern"] == "BOT_OR_AUTOMATION"
    assert data["decision_policy"]["primary_action"] == "CHALLENGE_OR_BLOCK"


def test_api_decision_policy_coordinated_syndicate_account(client):
    """Verify API decision_policy for multi-device/card account produces COORDINATED_SYNDICATE."""
    payload = {
        "account_id": "ACC_API_SYND_POLICY",
        "order_count": 22,
        "return_count": 16,
        "refund_count": 15,
        "total_spend": 1800.0,
        "account_age_days": 30,
        "device_count": 6,
        "ip_count": 7,
        "payment_instrument_count": 5,
        "return_rate": 0.72,
        "refund_rate": 0.68,
        "suspicious_activity_score": 0.92,
        "device_type": "desktop_chrome",
        "primary_payment_method": "virtual_card",
    }
    resp = client.post("/risk/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["risk_level"] == RISK_TIER_HIGH
    assert data["decision_policy"]["abuse_pattern"] == "COORDINATED_SYNDICATE"
    assert data["decision_policy"]["primary_action"] == "REQUIRE_2FA_VERIFICATION"


def test_api_decision_policy_high_value_risk_account(client):
    """Verify API decision_policy for high-value suspicious account produces HIGH_VALUE_RISK."""
    payload = {
        "account_id": "ACC_API_HIGH_VAL_POLICY",
        "order_count": 20,
        "return_count": 9,
        "refund_count": 8,
        "total_spend": 6500.0,
        "average_order_value": 325.0,
        "account_age_days": 40,
        "device_count": 2,
        "ip_count": 3,
        "payment_instrument_count": 2,
        "return_rate": 0.45,
        "refund_rate": 0.40,
        "high_value_order_count": 12,
        "suspicious_activity_score": 0.78,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }
    resp = client.post("/risk/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["risk_level"] == RISK_TIER_HIGH
    assert data["decision_policy"]["abuse_pattern"] == "HIGH_VALUE_RISK"
    assert data["decision_policy"]["primary_action"] == "HOLD_HIGH_VALUE_DISPATCH"


# =============================================================================
# PRIORITY 1: OPERATIONAL DOMAIN SEPARATION CONTRACT TESTS
# =============================================================================

def test_p1_domain_separation_general_low_return_medium(client):
    """TEST 1: Verify General LOW + Return MEDIUM preserves domain separation.
    
    Account/Checkout authorization must remain ALLOW.
    Return/Refund authorization must remain FLAG_FOR_RETURN_DESK_AUDIT.
    """
    payload = {
        "account_id": "ACC_DOMAIN_LOW_GEN_MED_RET",
        "order_count": 5,
        "return_count": 4,
        "refund_count": 4,
        "total_spend": 400.0,
        "average_order_value": 80.0,
        "account_age_days": 30,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.80,
        "refund_rate": 0.80,
        "high_value_order_count": 0,
        "suspicious_activity_score": 0.02,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }
    resp = client.post("/risk/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # 1. Account / Transactional authorization
    assert data["risk_level"] == RISK_TIER_LOW
    assert data["recommended_action"] == "ALLOW"

    # 2. Return / Refund authorization
    assert data["return_risk"] is not None
    assert data["return_risk"]["return_risk_level"] == RISK_TIER_MEDIUM
    assert data["return_risk"]["recommended_return_action"] == "FLAG_FOR_RETURN_DESK_AUDIT"


def test_p1_domain_separation_general_high_return_low(client):
    """TEST 2: Verify General HIGH + Return LOW preserves domain separation.
    
    Account/Checkout authorization must remain restrictive (CHALLENGE_OR_BLOCK).
    Return/Refund authorization must remain ALLOW_STANDARD_RETURNS (not downgrade account action).
    """
    payload = {
        "account_id": "ACC_DOMAIN_HIGH_GEN_LOW_RET",
        "order_count": 11,
        "return_count": 9,
        "refund_count": 7,
        "total_spend": 948.09,
        "average_order_value": 86.19,
        "account_age_days": 17,
        "device_count": 3,
        "ip_count": 3,
        "payment_instrument_count": 5,
        "return_rate": 0.8182,
        "refund_rate": 0.6364,
        "high_value_order_count": 7,
        "suspicious_activity_score": 0.9053,
        "device_type": "emulator_bot",
        "primary_payment_method": "virtual_card",
    }
    resp = client.post("/risk/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # 1. Account / Transactional authorization
    assert data["risk_level"] == RISK_TIER_HIGH
    assert data["recommended_action"] == "CHALLENGE_OR_BLOCK"

    # 2. Return / Refund authorization
    assert data["return_risk"] is not None
    assert data["return_risk"]["return_risk_level"] == RISK_TIER_LOW
    assert data["return_risk"]["recommended_return_action"] == "ALLOW_STANDARD_RETURNS"


def test_p1_domain_separation_general_medium_return_high(client):
    """TEST 3: Verify General MEDIUM + Return HIGH preserves domain separation.
    
    Account/Checkout authorization must remain MANUAL_REVIEW.
    Return/Refund authorization must remain RESTRICT_INSTANT_REFUNDS_AND_INSPECT.
    """
    payload = {
        "account_id": "ACC_DOMAIN_MED_GEN_HIGH_RET",
        "order_count": 25,
        "return_count": 22,
        "refund_count": 21,
        "total_spend": 4500.0,
        "average_order_value": 180.0,
        "account_age_days": 400,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.88,
        "refund_rate": 0.84,
        "high_value_order_count": 15,
        "suspicious_activity_score": 0.55,
        "device_type": "desktop_chrome",
        "primary_payment_method": "credit_card",
    }
    resp = client.post("/risk/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # 1. Account / Transactional authorization
    assert data["risk_level"] == RISK_TIER_MEDIUM
    assert data["recommended_action"] == "MANUAL_REVIEW"

    # 2. Return / Refund authorization
    assert data["return_risk"] is not None
    assert data["return_risk"]["return_risk_level"] == RISK_TIER_HIGH
    assert data["return_risk"]["recommended_return_action"] == "RESTRICT_INSTANT_REFUNDS_AND_INSPECT"


def test_get_account_profile_success(client):
    """Verify looking up a known account profile returns authentic metrics."""
    resp = client.get("/risk/account/ACC_MERCHANT_90210")
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_id"] == "ACC_MERCHANT_90210"
    assert data["order_count"] == 12.0
    assert data["total_spend"] == 650.0
    assert data["return_count"] == 1.0
    assert data["refund_count"] == 0.0
    assert data["return_rate"] == 0.0833
    assert data["refund_rate"] == 0.0


def test_get_account_profile_from_dataset(client):
    """Verify looking up an account from synthetic_accounts.csv."""
    resp = client.get("/risk/account/ACC_WARD_00001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_id"] == "ACC_WARD_00001"
    assert data["order_count"] == 58.0
    assert data["return_rate"] > 0.5


def test_get_account_profile_not_found(client):
    """Verify looking up an unknown account returns 404."""
    resp = client.get("/risk/account/ACC_NONEXISTENT_999")
    assert resp.status_code == 404
    data = resp.json()
    assert "not found in registry" in data["detail"]






