"""Feature definitions, input schema, validation, and sanitization for AI-RISK."""

import math
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd

# Primary identifier & Target
ID_COLUMN = "account_id"
TARGET_COLUMN = "abuse_label"

# Numeric features used by the ML model
NUMERIC_FEATURES: List[str] = [
    "order_count",
    "return_count",
    "refund_count",
    "total_spend",
    "average_order_value",
    "account_age_days",
    "device_count",
    "ip_count",
    "payment_instrument_count",
    "return_rate",
    "refund_rate",
    "high_value_order_count",
    "suspicious_activity_score",
]

# Categorical features supported by the ML pipeline
CATEGORICAL_FEATURES: List[str] = [
    "device_type",
    "primary_payment_method",
]

# All predictive model features (excluding account_id and target label)
MODEL_FEATURES: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Legacy alias for backward compatibility
FEATURE_COLUMNS = MODEL_FEATURES

# Risk level thresholds
RISK_THRESHOLD_LOW = 30.0    # Below 30: LOW
RISK_THRESHOLD_HIGH = 70.0   # 70 and above: HIGH (30-69: MEDIUM)

# Human-readable labels for risk bands
RISK_TIER_LOW = "LOW"
RISK_TIER_MEDIUM = "MEDIUM"
RISK_TIER_HIGH = "HIGH"

# Sensible default values for missing data imputation
DEFAULT_NUMERIC_VALUES: Dict[str, float] = {
    "order_count": 1.0,
    "return_count": 0.0,
    "refund_count": 0.0,
    "total_spend": 50.0,
    "average_order_value": 50.0,
    "account_age_days": 60.0,
    "device_count": 1.0,
    "ip_count": 1.0,
    "payment_instrument_count": 1.0,
    "return_rate": 0.0,
    "refund_rate": 0.0,
    "high_value_order_count": 0.0,
    "suspicious_activity_score": 0.05,
}

DEFAULT_CATEGORICAL_VALUES: Dict[str, str] = {
    "device_type": "unknown",
    "primary_payment_method": "unknown",
}


# Detailed Schema for New Account Input
ACCOUNT_INPUT_SCHEMA: Dict[str, Dict[str, Any]] = {
    ID_COLUMN: {
        "type": "string",
        "required": False,
        "default": "UNSEEN_ACCOUNT",
        "description": "Unique identifier for the merchant/account (not used as a predictive feature).",
    },
    "order_count": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["order_count"],
        "min": 0,
        "description": "Total count of completed orders.",
    },
    "return_count": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["return_count"],
        "min": 0,
        "description": "Total count of returned orders.",
    },
    "refund_count": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["refund_count"],
        "min": 0,
        "description": "Total count of refunded claims.",
    },
    "total_spend": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["total_spend"],
        "min": 0.0,
        "max": 1_000_000.0,
        "description": "Gross lifetime spend in USD.",
    },
    "average_order_value": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["average_order_value"],
        "min": 0.0,
        "max": 100_000.0,
        "description": "Average transaction order value in USD.",
    },
    "account_age_days": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["account_age_days"],
        "min": 0,
        "max": 25_000,
        "description": "Age of the account in days.",
    },
    "device_count": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["device_count"],
        "min": 0,
        "max": 500,
        "description": "Number of distinct hardware devices linked to the account.",
    },
    "ip_count": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["ip_count"],
        "min": 0,
        "max": 500,
        "description": "Number of distinct IP addresses used by the account.",
    },
    "payment_instrument_count": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["payment_instrument_count"],
        "min": 0,
        "max": 500,
        "description": "Number of payment cards / accounts linked to the merchant.",
    },
    "return_rate": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["return_rate"],
        "min": 0.0,
        "max": 1.0,
        "description": "Ratio of returns to total orders (0.0 to 1.0).",
    },
    "refund_rate": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["refund_rate"],
        "min": 0.0,
        "max": 1.0,
        "description": "Ratio of refund claims to total orders (0.0 to 1.0).",
    },
    "high_value_order_count": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["high_value_order_count"],
        "min": 0,
        "description": "Number of orders exceeding high-value threshold.",
    },
    "suspicious_activity_score": {
        "type": "numeric",
        "required": False,
        "default": DEFAULT_NUMERIC_VALUES["suspicious_activity_score"],
        "min": 0.0,
        "max": 1.0,
        "description": "Automated syndicate / velocity risk index (0.0 to 1.0).",
    },
    "device_type": {
        "type": "categorical",
        "required": False,
        "default": DEFAULT_CATEGORICAL_VALUES["device_type"],
        "known_values": ["mobile_ios", "mobile_android", "desktop_chrome", "desktop_safari", "emulator_bot", "unknown"],
        "description": "Primary device category or browser fingerprint.",
    },
    "primary_payment_method": {
        "type": "categorical",
        "required": False,
        "default": DEFAULT_CATEGORICAL_VALUES["primary_payment_method"],
        "known_values": ["credit_card", "debit_card", "paypal", "apple_pay", "virtual_card", "crypto_gift_card", "unknown"],
        "description": "Primary payment method used by the account.",
    },
}


class AccountInputValidationError(ValueError):
    """Raised when an account input payload fails validation or schema checking."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or [message]


def get_risk_tier(risk_score: float) -> str:
    """Map a 0-100 risk score to its corresponding qualitative risk level."""
    if risk_score < RISK_THRESHOLD_LOW:
        return RISK_TIER_LOW
    elif risk_score < RISK_THRESHOLD_HIGH:
        return RISK_TIER_MEDIUM
    else:
        return RISK_TIER_HIGH


def validate_and_sanitize_account_input(
    raw_input: Dict[str, Any],
    strict: bool = False,
) -> Tuple[Dict[str, Any], float, List[str]]:
    """Validate, sanitize, and compute data quality score for an unseen account input.

    Rules applied:
    - Never uses account_id or abuse_label as predictive features.
    - Missing fields: Imputed with safe defaults, reduces data quality score, logs warning.
    - Booleans in numeric fields: Rejected as non-numeric, imputed with default.
    - NaN / Infinite numeric values: Safely imputed with default, logs warning.
    - Negative numeric values: Clamped to 0, reduces data quality score, logs warning.
    - Inconsistent counts (return_count > order_count or refund_count > order_count):
      Clamped to order_count, rates re-calculated, reduces quality score, logs warning.
    - Rates out of [0, 1] range: Clamped / recalculated, logs warning.
    - Extreme values (e.g. spend > $1,000,000 or age > 25,000 days): Clamped to safe thresholds, logs warning.
    - Unknown categoricals: Gracefully mapped to lower-case string or 'unknown'.
    - Non-scalar categoricals (lists, dicts): Defaulted to 'unknown', logs warning.

    Args:
        raw_input: Dictionary of input features.
        strict: If True, raises AccountInputValidationError on fatal type errors or missing required fields.

    Returns:
        Tuple of (sanitized_dict, data_quality_score, list_of_warnings)

    Raises:
        TypeError: If raw_input is not a dictionary.
        AccountInputValidationError: If strict=True and payload contains validation violations.
    """
    if not isinstance(raw_input, dict):
        raise TypeError(f"Expected input to be a dictionary, got {type(raw_input).__name__}")

    sanitized: Dict[str, Any] = {}
    warnings: List[str] = []
    fatal_errors: List[str] = []
    penalty = 0.0

    # Preserve account_id separately for tracing (never used as a model feature)
    account_id = raw_input.get(ID_COLUMN, "UNSEEN_ACCOUNT")
    if isinstance(account_id, (list, dict, set)):
        warnings.append(f"Non-scalar account_id converted to string.")
        account_id = str(account_id)
    sanitized[ID_COLUMN] = str(account_id)

    # 1. Process Numeric Features
    for feat in NUMERIC_FEATURES:
        val = raw_input.get(feat, None)

        # Check for missing, None, or boolean
        if val is None:
            imputed_val = DEFAULT_NUMERIC_VALUES[feat]
            sanitized[feat] = imputed_val
            warnings.append(f"Missing field '{feat}' imputed with default ({imputed_val}).")
            fatal_errors.append(f"Missing required numeric field '{feat}'.")
            penalty += 0.08
            continue

        if isinstance(val, bool):
            imputed_val = DEFAULT_NUMERIC_VALUES[feat]
            sanitized[feat] = imputed_val
            warnings.append(f"Invalid boolean value for numeric field '{feat}' ({val}) imputed with default ({imputed_val}).")
            fatal_errors.append(f"Invalid boolean value for numeric field '{feat}'.")
            penalty += 0.12
            continue

        # Check for NaN / float
        if isinstance(val, (float, int)) and (np.isnan(val) or math.isnan(val)):
            imputed_val = DEFAULT_NUMERIC_VALUES[feat]
            sanitized[feat] = imputed_val
            warnings.append(f"NaN value for '{feat}' imputed with default ({imputed_val}).")
            fatal_errors.append(f"NaN value for numeric field '{feat}'.")
            penalty += 0.10
            continue

        try:
            num_val = float(val)
        except (ValueError, TypeError):
            imputed_val = DEFAULT_NUMERIC_VALUES[feat]
            sanitized[feat] = imputed_val
            warnings.append(f"Invalid non-numeric value for '{feat}' ({val}) imputed with default ({imputed_val}).")
            fatal_errors.append(f"Invalid non-numeric value for field '{feat}': {val}.")
            penalty += 0.12
            continue

        # Check for Infinity
        if math.isinf(num_val):
            imputed_val = DEFAULT_NUMERIC_VALUES[feat]
            sanitized[feat] = imputed_val
            warnings.append(f"Infinite value for '{feat}' ({val}) imputed with default ({imputed_val}).")
            fatal_errors.append(f"Infinite value for numeric field '{feat}'.")
            penalty += 0.12
            continue

        # Check for negative numbers
        if num_val < 0.0:
            warnings.append(f"Negative value for '{feat}' ({num_val}) clamped to 0.0.")
            fatal_errors.append(f"Negative value for field '{feat}' ({num_val}) is not permitted in strict mode.")
            num_val = 0.0
            penalty += 0.08

        # Check for extreme out-of-range inputs
        if feat == "total_spend" and num_val > 1_000_000.0:
            warnings.append(f"Extreme total_spend (${num_val:,.2f}) clamped to $1,000,000.00.")
            num_val = 1_000_000.0
            penalty += 0.05
        elif feat == "average_order_value" and num_val > 100_000.0:
            warnings.append(f"Extreme average_order_value (${num_val:,.2f}) clamped to $100,000.00.")
            num_val = 100_000.0
            penalty += 0.05
        elif feat == "account_age_days" and num_val > 25_000.0:
            warnings.append(f"Extreme account_age_days ({num_val}) clamped to 25,000 days.")
            num_val = 25_000.0
            penalty += 0.05
        elif feat in ["device_count", "ip_count", "payment_instrument_count"] and num_val > 500.0:
            warnings.append(f"Extreme count for '{feat}' ({num_val}) clamped to 500.")
            num_val = 500.0
            penalty += 0.05

        sanitized[feat] = num_val

    # 2. Enforce Logical Cross-Feature Consistency
    order_count = sanitized["order_count"]
    return_count = sanitized["return_count"]
    refund_count = sanitized["refund_count"]

    if return_count > order_count:
        warnings.append(
            f"Inconsistent count: return_count ({return_count}) exceeds order_count ({order_count}). Clamped return_count to order_count."
        )
        sanitized["return_count"] = order_count
        penalty += 0.10

    if refund_count > order_count:
        warnings.append(
            f"Inconsistent count: refund_count ({refund_count}) exceeds order_count ({order_count}). Clamped refund_count to order_count."
        )
        sanitized["refund_count"] = order_count
        penalty += 0.10

    # Ensure rate fields are mathematically sound
    if order_count > 0:
        calculated_return_rate = round(sanitized["return_count"] / order_count, 4)
        calculated_refund_rate = round(sanitized["refund_count"] / order_count, 4)

        raw_ret_rate = sanitized["return_rate"]
        raw_ref_rate = sanitized["refund_rate"]

        if raw_ret_rate < 0.0 or raw_ret_rate > 1.0 or abs(raw_ret_rate - calculated_return_rate) > 0.05:
            if raw_ret_rate < 0.0 or raw_ret_rate > 1.0:
                warnings.append(f"return_rate ({raw_ret_rate}) was outside [0, 1]. Recalculated from counts.")
            sanitized["return_rate"] = calculated_return_rate

        if raw_ref_rate < 0.0 or raw_ref_rate > 1.0 or abs(raw_ref_rate - calculated_refund_rate) > 0.05:
            if raw_ref_rate < 0.0 or raw_ref_rate > 1.0:
                warnings.append(f"refund_rate ({raw_ref_rate}) was outside [0, 1]. Recalculated from counts.")
            sanitized["refund_rate"] = calculated_refund_rate
    else:
        sanitized["return_rate"] = 0.0
        sanitized["refund_rate"] = 0.0

    # Suspicious activity score clamp [0, 1]
    susp_score = sanitized["suspicious_activity_score"]
    if susp_score < 0.0 or susp_score > 1.0:
        clamped_susp = float(np.clip(susp_score, 0.0, 1.0))
        warnings.append(f"suspicious_activity_score ({susp_score}) outside [0, 1] clamped to {clamped_susp}.")
        sanitized["suspicious_activity_score"] = clamped_susp
        penalty += 0.05

    # 3. Process Categorical Features
    for feat in CATEGORICAL_FEATURES:
        val = raw_input.get(feat, None)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            sanitized[feat] = DEFAULT_CATEGORICAL_VALUES[feat]
        elif isinstance(val, (list, dict, set, tuple)):
            sanitized[feat] = DEFAULT_CATEGORICAL_VALUES[feat]
            warnings.append(f"Invalid non-scalar value for categorical field '{feat}' ({type(val).__name__}) defaulted to '{DEFAULT_CATEGORICAL_VALUES[feat]}'.")
            fatal_errors.append(f"Invalid non-scalar type for categorical field '{feat}': {type(val).__name__}.")
            penalty += 0.08
        else:
            sanitized[feat] = str(val).strip().lower()

    # Raise in strict mode if any fatal validation errors occurred
    if strict and fatal_errors:
        err_msg = f"Account validation failed with {len(fatal_errors)} error(s): " + "; ".join(fatal_errors)
        raise AccountInputValidationError(err_msg, errors=fatal_errors)

    # Calculate final Data Quality Score in [0.0, 1.0]
    data_quality_score = float(max(0.0, min(1.0, round(1.0 - penalty, 2))))

    return sanitized, data_quality_score, warnings


def validate_account_payload(
    raw_input: Dict[str, Any],
    strict: bool = False,
) -> Tuple[Dict[str, Any], float, List[str]]:
    """Validate and sanitize an account input payload against the defined schema.

    Convenience alias for validate_and_sanitize_account_input.
    """
    return validate_and_sanitize_account_input(raw_input, strict=strict)

