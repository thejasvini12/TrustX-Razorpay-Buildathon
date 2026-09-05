"""Unit tests for the Adaptive Risk Decision Engine."""

import pytest
from src.features import RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH
from src.decision_engine import (
    AdaptiveDecisionEngine,
    PATTERN_LOW_RISK_STANDARD,
    PATTERN_MEDIUM_RISK_REVIEW,
    PATTERN_SERIAL_RETURN,
    PATTERN_COORDINATED_SYNDICATE,
    PATTERN_BOT_OR_AUTOMATION,
    PATTERN_HIGH_VALUE_RISK,
    PATTERN_GENERAL_HIGH_RISK,
)


@pytest.fixture
def engine():
    """Fixture providing initialized AdaptiveDecisionEngine."""
    return AdaptiveDecisionEngine()


def test_low_risk_standard_decision(engine):
    """Verify that a low-risk legitimate account produces LOW_RISK_STANDARD with ALLOW_STANDARD."""
    account = {
        "account_id": "ACC_LOW_TEST",
        "order_count": 25,
        "return_count": 1,
        "refund_count": 0,
        "total_spend": 1200.0,
        "average_order_value": 48.0,
        "account_age_days": 350,
        "device_count": 1,
        "ip_count": 1,
        "payment_instrument_count": 1,
        "return_rate": 0.04,
        "refund_rate": 0.0,
        "suspicious_activity_score": 0.02,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }

    decision = engine.evaluate_decision(
        risk_score=5,
        risk_level=RISK_TIER_LOW,
        risk_probability=0.05,
        account_data=account,
    )

    assert decision["abuse_pattern"] == PATTERN_LOW_RISK_STANDARD
    assert decision["primary_action"] == "ALLOW_STANDARD"
    assert "ENABLE_FRICTIONLESS_CHECKOUT" in decision["secondary_actions"]
    assert len(decision["policy_triggers"]) > 0
    assert "LOW" in decision["policy_reasoning"]
    assert decision["confidence"] in ["HIGH", "MEDIUM"]


def test_medium_risk_review_decision(engine):
    """Verify that a medium-risk borderline account produces MEDIUM_RISK_REVIEW with REQUIRE_MANUAL_REVIEW."""
    account = {
        "account_id": "ACC_MED_TEST",
        "order_count": 12,
        "return_count": 4,
        "refund_count": 3,
        "total_spend": 900.0,
        "average_order_value": 75.0,
        "account_age_days": 90,
        "device_count": 2,
        "ip_count": 3,
        "payment_instrument_count": 2,
        "return_rate": 0.3333,
        "refund_rate": 0.25,
        "suspicious_activity_score": 0.38,
        "device_type": "desktop_chrome",
        "primary_payment_method": "paypal",
    }

    decision = engine.evaluate_decision(
        risk_score=45,
        risk_level=RISK_TIER_MEDIUM,
        risk_probability=0.45,
        account_data=account,
    )

    assert decision["abuse_pattern"] == PATTERN_MEDIUM_RISK_REVIEW
    assert decision["primary_action"] == "REQUIRE_MANUAL_REVIEW"
    assert len(decision["secondary_actions"]) > 0
    assert len(decision["policy_triggers"]) > 0
    assert "Borderline" in decision["policy_reasoning"] or "MEDIUM" in decision["policy_reasoning"]


def test_serial_return_abuse_decision(engine):
    """Verify that high return/refund rates trigger SERIAL_RETURN_ABUSE with return restrictions."""
    account = {
        "account_id": "ACC_WARDROBE_TEST",
        "order_count": 15,
        "return_count": 12,
        "refund_count": 11,
        "total_spend": 2400.0,
        "average_order_value": 160.0,
        "account_age_days": 180,
        "device_count": 1,
        "ip_count": 2,
        "payment_instrument_count": 1,
        "return_rate": 0.80,
        "refund_rate": 0.7333,
        "suspicious_activity_score": 0.65,
        "device_type": "desktop_chrome",
        "primary_payment_method": "credit_card",
    }

    decision = engine.evaluate_decision(
        risk_score=85,
        risk_level=RISK_TIER_HIGH,
        risk_probability=0.85,
        account_data=account,
    )

    assert decision["abuse_pattern"] == PATTERN_SERIAL_RETURN
    assert decision["primary_action"] == "RESTRICT_RETURN_WITHOUT_RECEIPT"
    assert any("DISABLE_INSTANT_REFUND" in a or "INSPECTION" in a for a in decision["secondary_actions"])
    assert any("return_rate" in t for t in decision["policy_triggers"])
    assert "serial" in decision["policy_reasoning"].lower()


def test_bot_or_automation_decision(engine):
    """Verify that emulator fingerprint and velocity bursts trigger BOT_OR_AUTOMATION."""
    account = {
        "account_id": "ACC_BOT_TEST",
        "order_count": 10,
        "return_count": 2,
        "refund_count": 2,
        "total_spend": 400.0,
        "average_order_value": 40.0,
        "account_age_days": 4,
        "device_count": 2,
        "ip_count": 3,
        "payment_instrument_count": 2,
        "return_rate": 0.20,
        "refund_rate": 0.20,
        "suspicious_activity_score": 0.88,
        "device_type": "emulator_bot",
        "primary_payment_method": "virtual_card",
    }

    decision = engine.evaluate_decision(
        risk_score=95,
        risk_level=RISK_TIER_HIGH,
        risk_probability=0.95,
        account_data=account,
    )

    assert decision["abuse_pattern"] == PATTERN_BOT_OR_AUTOMATION
    assert decision["primary_action"] == "CHALLENGE_OR_BLOCK"
    assert any("CAPTCHA" in a or "RATE_LIMIT" in a or "PROOF_OF_WORK" in a for a in decision["secondary_actions"])
    assert any("emulator" in t.lower() or "burst" in t.lower() for t in decision["policy_triggers"])


def test_coordinated_syndicate_decision(engine):
    """Verify that multi-device, multi-IP, multi-card turnover triggers COORDINATED_SYNDICATE."""
    account = {
        "account_id": "ACC_SYNDICATE_TEST",
        "order_count": 14,
        "return_count": 4,
        "refund_count": 3,
        "total_spend": 1200.0,
        "average_order_value": 85.71,
        "account_age_days": 40,
        "device_count": 5,
        "ip_count": 6,
        "payment_instrument_count": 4,
        "return_rate": 0.2857,
        "refund_rate": 0.2143,
        "suspicious_activity_score": 0.78,
        "device_type": "desktop_chrome",
        "primary_payment_method": "virtual_card",
    }

    decision = engine.evaluate_decision(
        risk_score=90,
        risk_level=RISK_TIER_HIGH,
        risk_probability=0.90,
        account_data=account,
    )

    assert decision["abuse_pattern"] == PATTERN_COORDINATED_SYNDICATE
    assert decision["primary_action"] == "REQUIRE_2FA_VERIFICATION"
    assert any("RESTRICT_VIRTUAL_PAYMENT_METHODS" in a or "BIND_HARDWARE_FINGERPRINT" in a for a in decision["secondary_actions"])
    assert any("devices" in t for t in decision["policy_triggers"])
    assert any("IP" in t for t in decision["policy_triggers"])


def test_high_value_risk_decision(engine):
    """Verify that heavy financial exposure on an elevated risk account triggers HIGH_VALUE_RISK."""
    account = {
        "account_id": "ACC_HIGH_VAL_TEST",
        "order_count": 18,
        "return_count": 3,
        "refund_count": 2,
        "total_spend": 5500.0,
        "average_order_value": 305.56,
        "account_age_days": 120,
        "device_count": 2,
        "ip_count": 2,
        "payment_instrument_count": 2,
        "return_rate": 0.1667,
        "refund_rate": 0.1111,
        "high_value_order_count": 8,
        "suspicious_activity_score": 0.40,
        "device_type": "mobile_ios",
        "primary_payment_method": "credit_card",
    }

    decision = engine.evaluate_decision(
        risk_score=75,
        risk_level=RISK_TIER_HIGH,
        risk_probability=0.75,
        account_data=account,
    )

    assert decision["abuse_pattern"] == PATTERN_HIGH_VALUE_RISK
    assert decision["primary_action"] == "HOLD_HIGH_VALUE_DISPATCH"
    assert any("SIGNATURE" in a or "MANUAL" in a for a in decision["secondary_actions"])
    assert any("spend" in t.lower() or "average order value" in t.lower() for t in decision["policy_triggers"])


def test_general_high_risk_fallback_decision(engine):
    """Verify that a high-risk account without an archetype dominance falls back to GENERAL_HIGH_RISK."""
    account = {
        "account_id": "ACC_GENERIC_HIGH_TEST",
        "order_count": 8,
        "return_count": 1,
        "refund_count": 1,
        "total_spend": 350.0,
        "average_order_value": 43.75,
        "account_age_days": 45,
        "device_count": 1,
        "ip_count": 2,
        "payment_instrument_count": 1,
        "return_rate": 0.125,
        "refund_rate": 0.125,
        "suspicious_activity_score": 0.30,
        "device_type": "mobile_android",
        "primary_payment_method": "debit_card",
    }

    decision = engine.evaluate_decision(
        risk_score=72,
        risk_level=RISK_TIER_HIGH,
        risk_probability=0.72,
        account_data=account,
    )

    assert decision["abuse_pattern"] == PATTERN_GENERAL_HIGH_RISK
    assert decision["primary_action"] == "REQUIRE_MANUAL_REVIEW"
    assert len(decision["policy_triggers"]) > 0
    assert len(decision["policy_reasoning"]) > 0


def test_decision_engine_does_not_mutate_inputs(engine):
    """Verify that evaluating decisions never modifies input arguments or ML scores."""
    original_score = 42
    original_level = "MEDIUM"
    original_prob = 0.4218
    account = {
        "account_id": "ACC_IMMUTABLE_TEST",
        "order_count": 10,
        "total_spend": 500.0,
    }
    account_copy = dict(account)

    decision = engine.evaluate_decision(
        risk_score=original_score,
        risk_level=original_level,
        risk_probability=original_prob,
        account_data=account,
    )

    # Input structures remain identical
    assert account == account_copy
    assert original_score == 42
    assert original_level == "MEDIUM"
    assert original_prob == 0.4218
    assert isinstance(decision, dict)
