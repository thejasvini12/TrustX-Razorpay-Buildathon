"""Adaptive Risk Decision Engine for Merchant Abuse Risk Mitigation.

Operates as a post-scoring decision and defense policy layer downstream of ML inference.
Evaluates calibrated ML risk scores, observed behavioral features, and explainability
signals to recommend tailored, granular operational actions.

Abuse Pattern Archetypes:
- SERIAL_RETURN_ABUSE: Excessive return/refund volume on high-value transactions.
- COORDINATED_SYNDICATE: Multi-device, multi-IP, multi-card cluster signals.
- BOT_OR_AUTOMATION: Automated emulator/bot fingerprints and velocity bursts.
- HIGH_VALUE_RISK: Substantial financial exposure with elevated risk indicators.
- GENERAL_HIGH_RISK: Fallback high-risk assessment without specific archetype dominance.
- MEDIUM_RISK_REVIEW: Borderline risk requiring human review or step-up authentication.
- LOW_RISK_STANDARD: Standard legitimate traffic permitted with standard monitoring.
"""

from typing import Dict, Any, List, Optional
from src.features import RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH


# Configurable Policy Thresholds
POLICY_THRESHOLDS = {
    # Serial Return / Wardrobing Thresholds
    "serial_return_rate": 0.50,
    "serial_refund_rate": 0.50,
    "serial_return_min_orders": 3,
    
    # Coordinated Syndicate Thresholds
    "syndicate_min_devices": 3,
    "syndicate_min_ips": 4,
    "syndicate_min_cards": 3,
    "syndicate_suspicious_score": 0.50,

    # Bot / Automation Thresholds
    "bot_account_max_age_days": 14,
    "bot_min_order_burst": 3,
    "bot_suspicious_score": 0.60,

    # High Value Exposure Thresholds
    "high_value_min_orders": 2,
    "high_value_avg_order_usd": 120.0,
    "high_value_total_spend_usd": 1500.0,
}


# Recognized Abuse Pattern Identifiers
PATTERN_SERIAL_RETURN = "SERIAL_RETURN_ABUSE"
PATTERN_COORDINATED_SYNDICATE = "COORDINATED_SYNDICATE"
PATTERN_BOT_OR_AUTOMATION = "BOT_OR_AUTOMATION"
PATTERN_HIGH_VALUE_RISK = "HIGH_VALUE_RISK"
PATTERN_GENERAL_HIGH_RISK = "GENERAL_HIGH_RISK"
PATTERN_MEDIUM_RISK_REVIEW = "MEDIUM_RISK_REVIEW"
PATTERN_LOW_RISK_STANDARD = "LOW_RISK_STANDARD"


class AdaptiveDecisionEngine:
    """Evaluates contextual risk policies and recommends granular defense actions."""

    def __init__(self, custom_thresholds: Optional[Dict[str, Any]] = None):
        """Initialize decision engine with standard or customized merchant thresholds."""
        self.thresholds = dict(POLICY_THRESHOLDS)
        if custom_thresholds:
            self.thresholds.update(custom_thresholds)

    def evaluate_decision(
        self,
        risk_score: int,
        risk_level: str,
        risk_probability: float,
        account_data: Dict[str, Any],
        signals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Evaluate account profile and generate an adaptive risk decision policy.

        Args:
            risk_score: Model calibrated risk score (0 to 100).
            risk_level: Model qualitative tier (LOW, MEDIUM, HIGH).
            risk_probability: Model posterior abuse probability (0.0 to 1.0).
            account_data: Sanitized merchant account features.
            signals: Optional list of explainability risk factors/signals.

        Returns:
            Dictionary containing structured decision policy:
            - primary_action
            - secondary_actions
            - policy_triggers
            - abuse_pattern
            - policy_reasoning
            - confidence
        """
        # Feature extraction
        return_rate = float(account_data.get("return_rate", 0.0))
        refund_rate = float(account_data.get("refund_rate", 0.0))
        order_count = int(account_data.get("order_count", 0))
        return_count = int(account_data.get("return_count", 0))
        refund_count = int(account_data.get("refund_count", 0))
        device_count = int(account_data.get("device_count", 1))
        ip_count = int(account_data.get("ip_count", 1))
        payment_inst_count = int(account_data.get("payment_instrument_count", 1))
        account_age_days = float(account_data.get("account_age_days", 999))
        susp_score = float(account_data.get("suspicious_activity_score", 0.0))
        avg_order_val = float(account_data.get("average_order_value", 0.0))
        total_spend = float(account_data.get("total_spend", 0.0))
        high_val_count = int(account_data.get("high_value_order_count", 0))
        device_type = str(account_data.get("device_type", "")).lower()
        payment_method = str(account_data.get("primary_payment_method", "")).lower()

        # =====================================================================
        # 1. LOW RISK EVALUATION
        # =====================================================================
        if risk_level == RISK_TIER_LOW or risk_score < 30:
            return {
                "abuse_pattern": PATTERN_LOW_RISK_STANDARD,
                "primary_action": "ALLOW_STANDARD",
                "secondary_actions": [
                    "ENABLE_FRICTIONLESS_CHECKOUT",
                    "STANDARD_DISPUTE_MONITORING",
                ],
                "policy_triggers": [
                    f"risk_score ({risk_score}) is below review threshold (< 30)",
                    "no critical abuse pattern thresholds exceeded",
                ],
                "policy_reasoning": (
                    "Overall risk assessment is LOW. The account demonstrates healthy behavioral indicators "
                    "consistent with standard customer activity. Frictionless processing is recommended."
                ),
                "confidence": "HIGH" if risk_score <= 10 else "MEDIUM",
            }

        # =====================================================================
        # 2. HIGH RISK EVALUATIONS (Archetype-Specific Rules)
        # =====================================================================
        if risk_level == RISK_TIER_HIGH or risk_score >= 70:

            # 2a. Bot / Automation Pattern
            bot_triggers = []
            if device_type == "emulator_bot":
                bot_triggers.append("detected emulator or bot browser fingerprint")
            if account_age_days <= self.thresholds["bot_account_max_age_days"] and order_count >= self.thresholds["bot_min_order_burst"]:
                bot_triggers.append(f"fresh account burst ({int(account_age_days)}d old with {order_count} orders)")
            if susp_score >= self.thresholds["bot_suspicious_score"]:
                bot_triggers.append(f"high velocity anomaly score ({susp_score:.2f})")

            if len(bot_triggers) >= 2 or device_type == "emulator_bot":
                return {
                    "abuse_pattern": PATTERN_BOT_OR_AUTOMATION,
                    "primary_action": "CHALLENGE_OR_BLOCK",
                    "secondary_actions": [
                        "REQUIRE_DEVICE_PROOF_OF_WORK",
                        "ENFORCE_CAPTCHA_AND_RATE_LIMIT",
                        "BLOCK_AUTOMATED_CHECKOUT_API",
                    ],
                    "policy_triggers": bot_triggers,
                    "policy_reasoning": (
                        "Elevated indicators of automated or scripted interaction detected. Recommended policy is to "
                        "challenge with cryptographic proof-of-work or block automated checkout endpoints."
                    ),
                    "confidence": "HIGH" if device_type == "emulator_bot" else "MEDIUM",
                }

            # 2b. Coordinated Syndicate Pattern
            syndicate_triggers = []
            if device_count >= self.thresholds["syndicate_min_devices"]:
                syndicate_triggers.append(f"multiple linked hardware devices ({device_count})")
            if ip_count >= self.thresholds["syndicate_min_ips"]:
                syndicate_triggers.append(f"high IP address turnover ({ip_count} distinct IPs)")
            if payment_inst_count >= self.thresholds["syndicate_min_cards"]:
                syndicate_triggers.append(f"elevated payment card turnover ({payment_inst_count} cards)")
            if payment_method in ["virtual_card", "crypto_gift_card"]:
                syndicate_triggers.append(f"high-risk payment method ({payment_method})")
            if susp_score >= self.thresholds["syndicate_suspicious_score"]:
                syndicate_triggers.append(f"elevated cluster connectivity score ({susp_score:.2f})")

            if len(syndicate_triggers) >= 2:
                return {
                    "abuse_pattern": PATTERN_COORDINATED_SYNDICATE,
                    "primary_action": "REQUIRE_2FA_VERIFICATION",
                    "secondary_actions": [
                        "BIND_HARDWARE_FINGERPRINT",
                        "RESTRICT_VIRTUAL_PAYMENT_METHODS",
                        "HOLD_FOR_SYNDICATE_INVESTIGATION",
                    ],
                    "policy_triggers": syndicate_triggers,
                    "policy_reasoning": (
                        "Behavioral and network signals indicate potential multi-account syndicate or credential "
                        "cycling. Recommended policy is to enforce mandatory step-up 2FA and restrict disposable cards."
                    ),
                    "confidence": "HIGH" if len(syndicate_triggers) >= 3 else "MEDIUM",
                }

            # 2c. Serial Return & Refund Abuse (Wardrobing)
            return_triggers = []
            if return_rate >= self.thresholds["serial_return_rate"]:
                return_triggers.append(f"return_rate ({return_rate:.1%}) exceeds serial return threshold ({self.thresholds['serial_return_rate']:.0%})")
            if refund_rate >= self.thresholds["serial_refund_rate"]:
                return_triggers.append(f"refund_rate ({refund_rate:.1%}) exceeds refund threshold ({self.thresholds['serial_refund_rate']:.0%})")
            if return_count >= self.thresholds["serial_return_min_orders"]:
                return_triggers.append(f"sustained return volume ({return_count} return claims)")

            if len(return_triggers) >= 2:
                return {
                    "abuse_pattern": PATTERN_SERIAL_RETURN,
                    "primary_action": "RESTRICT_RETURN_WITHOUT_RECEIPT",
                    "secondary_actions": [
                        "REQUIRE_PHYSICAL_ITEM_INSPECTION",
                        "DISABLE_INSTANT_REFUND_PRIVILEGE",
                        "CHARGE_RESTOCKING_FEE_ON_RETURNS",
                    ],
                    "policy_triggers": return_triggers,
                    "policy_reasoning": (
                        "High proportion of orders claimed for refund/return indicates a potential serial wardrobing "
                        "or return abuse pattern. Recommended policy is to disable instant refunds and require item inspection."
                    ),
                    "confidence": "HIGH" if return_rate >= 0.70 else "MEDIUM",
                }

            # 2d. High-Value Financial Exposure Risk
            high_val_triggers = []
            if avg_order_val >= self.thresholds["high_value_avg_order_usd"]:
                high_val_triggers.append(f"high average order value (${avg_order_val:.2f})")
            if high_val_count >= self.thresholds["high_value_min_orders"]:
                high_val_triggers.append(f"frequent high-value orders ({high_val_count} transactions)")
            if total_spend >= self.thresholds["high_value_total_spend_usd"]:
                high_val_triggers.append(f"substantial gross spend (${total_spend:,.2f})")

            if len(high_val_triggers) >= 2:
                return {
                    "abuse_pattern": PATTERN_HIGH_VALUE_RISK,
                    "primary_action": "HOLD_HIGH_VALUE_DISPATCH",
                    "secondary_actions": [
                        "REQUIRE_SIGNATURE_ON_DELIVERY",
                        "MANUAL_PAYMENT_ORIGIN_VERIFICATION",
                        "FLAG_FOR_SENIOR_ANALYST_REVIEW",
                    ],
                    "policy_triggers": high_val_triggers,
                    "policy_reasoning": (
                        "High financial exposure on an account with elevated model risk score. Recommended policy "
                        "is to place high-value dispatches on temporary hold pending delivery signature confirmation."
                    ),
                    "confidence": "HIGH" if total_spend >= 3000.0 else "MEDIUM",
                }

            # 2e. General High Risk Fallback
            return {
                "abuse_pattern": PATTERN_GENERAL_HIGH_RISK,
                "primary_action": "REQUIRE_MANUAL_REVIEW",
                "secondary_actions": [
                    "APPLY_STRICT_TRANSACTION_LIMITS",
                    "STEP_UP_IDENTITY_VERIFICATION",
                ],
                "policy_triggers": [
                    f"risk_score ({risk_score}) meets or exceeds high-risk threshold (>= 70)",
                    "multiple composite behavioral risk factors present",
                ],
                "policy_reasoning": (
                    "Account evaluated as high risk by the composite ML model. Detailed pattern does not uniquely "
                    "match a single archetype. Step-up verification and analyst review are recommended."
                ),
                "confidence": "HIGH" if risk_score >= 85 else "MEDIUM",
            }

        # =====================================================================
        # 3. MEDIUM RISK EVALUATION (Borderline Human Review)
        # =====================================================================
        medium_triggers = [
            f"risk_score ({risk_score}) falls in borderline review tier (30 to 69)",
        ]
        if return_rate >= 0.30:
            medium_triggers.append(f"elevated return rate ({return_rate:.1%})")
        if susp_score >= 0.30:
            medium_triggers.append(f"moderate anomaly indicator ({susp_score:.2f})")
        if device_count >= 2:
            medium_triggers.append(f"multiple linked devices ({device_count})")

        return {
            "abuse_pattern": PATTERN_MEDIUM_RISK_REVIEW,
            "primary_action": "REQUIRE_MANUAL_REVIEW",
            "secondary_actions": [
                "REQUEST_ADDITIONAL_2FA_AT_CHECKOUT",
                "ALLOW_ORDER_WITH_ASYNC_AUDIT",
            ],
            "policy_triggers": medium_triggers,
            "policy_reasoning": (
                "Borderline risk score indicates conflicting signals: elevated risk factors are partially offset "
                "by legitimate customer tenure or spend history. Recommended policy is asynchronous manual review."
            ),
            "confidence": "MEDIUM",
        }
