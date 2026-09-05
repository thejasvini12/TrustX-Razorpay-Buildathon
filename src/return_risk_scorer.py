"""Specialized Return-Risk Scorer for Digital Merchants.

Provides dedicated ML-powered detection, verification, and auto-response recommendations
for Return & Refund Abuse (Serial Wardrobing).
Operates downstream or as a specialized loss-class sub-engine alongside general abuse detection.
"""

import os
import json
from typing import Dict, Any, List, Union, Optional
import joblib
import numpy as np
import pandas as pd

from src.features import (
    ID_COLUMN,
    MODEL_FEATURES,
    get_risk_tier,
    validate_and_sanitize_account_input,
    RISK_TIER_LOW,
    RISK_TIER_MEDIUM,
    RISK_TIER_HIGH,
)


class ReturnRiskScorer:
    """Specialized inference engine for detecting and mitigating return/refund abuse."""

    def __init__(
        self,
        model_path: str = os.path.join("models", "return_risk_model.joblib"),
        metadata_path: str = os.path.join("models", "return_risk_metadata.json"),
    ):
        """Initialize the return-risk scorer with trained model and metadata."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Trained return-risk model artifact not found at '{model_path}'.")

        self.pipeline = joblib.load(model_path)
        self.metadata = {}
        if metadata_path and os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)

    def _extract_return_risk_factors(self, data: Dict[str, Any]) -> List[str]:
        """Identify specific return-related risk signals from account data."""
        factors = []
        return_rate = float(data.get("return_rate", 0.0))
        refund_rate = float(data.get("refund_rate", 0.0))
        return_count = int(data.get("return_count", 0))
        refund_count = int(data.get("refund_count", 0))
        high_val_count = int(data.get("high_value_order_count", 0))
        avg_order_val = float(data.get("average_order_value", 0.0))
        total_spend = float(data.get("total_spend", 0.0))

        if return_rate > 0.60:
            factors.append(f"Excessive return rate ({return_rate:.1%})")
        elif return_rate > 0.35:
            factors.append(f"Elevated return rate ({return_rate:.1%})")

        if refund_rate > 0.60:
            factors.append(f"Excessive refund claim rate ({refund_rate:.1%})")
        elif refund_rate > 0.35:
            factors.append(f"Elevated refund claim rate ({refund_rate:.1%})")

        if return_count >= 10:
            factors.append(f"High cumulative return volume ({return_count} return claims)")
        elif return_count >= 4:
            factors.append(f"Frequent return activity ({return_count} return claims)")

        if high_val_count >= 3 and avg_order_val >= 120.0:
            factors.append(f"Concentrated return risk on high-value basket items (${avg_order_val:.2f} avg)")

        if not factors:
            factors.append("Return and refund behavior within normal retail tolerance")

        return factors

    def _extract_return_mitigating_factors(self, data: Dict[str, Any]) -> List[str]:
        """Identify protective signals indicating legitimate return shopping behavior."""
        mitigations = []
        return_rate = float(data.get("return_rate", 0.0))
        refund_rate = float(data.get("refund_rate", 0.0))
        order_count = int(data.get("order_count", 0))
        account_age_days = float(data.get("account_age_days", 0))

        if return_rate == 0.0 and order_count >= 2:
            mitigations.append("Zero returned orders across transaction history")
        elif return_rate <= 0.15 and order_count >= 5:
            mitigations.append(f"Low return rate ({return_rate:.1%}) consistent with normal shopping")

        if refund_rate == 0.0 and order_count >= 2:
            mitigations.append("Zero refund claims filed")
        elif refund_rate <= 0.10 and order_count >= 5:
            mitigations.append(f"Healthy low refund rate ({refund_rate:.1%})")

        if account_age_days >= 90 and return_rate <= 0.25:
            mitigations.append(f"Seasoned account history ({int(account_age_days)} days) with controlled return rate")

        return mitigations

    def _generate_return_explanation(
        self,
        risk_level: str,
        risk_score: int,
        return_rate: float,
        refund_rate: float,
        order_count: int,
        guardrail_triggered: bool = False,
    ) -> str:
        """Generate human-readable explanation tailored specifically to return abuse."""
        if guardrail_triggered and risk_level == RISK_TIER_MEDIUM:
            return (
                f"Moderate return risk (score: {risk_score}/100). High return frequency observed within a limited order history "
                f"({return_rate:.1%} return rate across {order_count} orders). Secondary return-desk verification is recommended."
            )
        elif risk_level == RISK_TIER_HIGH:
            return (
                f"High return-abuse risk (score: {risk_score}/100) driven primarily by an elevated {return_rate:.1%} "
                f"return rate and {refund_rate:.1%} refund claim rate across {order_count} completed orders."
            )
        elif risk_level == RISK_TIER_MEDIUM:
            return (
                f"Moderate return risk (score: {risk_score}/100). The account shows elevated return frequency ({return_rate:.1%}) "
                f"that warrants secondary return-desk verification or size-consultation review."
            )
        else:
            return (
                f"Low return-abuse risk (score: {risk_score}/100). The account exhibits standard return rates ({return_rate:.1%}) "
                f"and healthy transaction history consistent with legitimate consumer behavior."
            )

    def _determine_return_action(self, risk_level: str) -> str:
        """Determine automated return-desk operational policy action for returns/refunds.
        
        Controls post-purchase return/refund authorization (ALLOW_STANDARD_RETURNS,
        FLAG_FOR_RETURN_DESK_AUDIT, RESTRICT_INSTANT_REFUNDS_AND_INSPECT).
        Does NOT alter or restrict account-level checkout or login privileges.
        """
        if risk_level == RISK_TIER_HIGH:
            return "RESTRICT_INSTANT_REFUNDS_AND_INSPECT"
        elif risk_level == RISK_TIER_MEDIUM:
            return "FLAG_FOR_RETURN_DESK_AUDIT"
        else:
            return "ALLOW_STANDARD_RETURNS"

    def predict_account(self, input_record: Dict[str, Any]) -> Dict[str, Any]:
        """Predict return risk for a single account dictionary."""
        results = self.predict_accounts([input_record])
        return results[0]

    def predict_accounts(
        self,
        input_data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Validate, sanitize, and score return-abuse risk for one or more accounts."""
        if isinstance(input_data, dict):
            raw_records = [input_data]
        elif isinstance(input_data, list):
            raw_records = input_data
        elif isinstance(input_data, pd.DataFrame):
            raw_records = input_data.to_dict(orient="records")
        else:
            raise TypeError(f"input_data must be a dict, list, or DataFrame, got {type(input_data).__name__}.")

        if not raw_records:
            return []

        sanitized_records = []
        for record in raw_records:
            sanitized, _, _ = validate_and_sanitize_account_input(record)
            sanitized_records.append(sanitized)

        df_for_model = pd.DataFrame(sanitized_records)[MODEL_FEATURES]

        probabilities = self.pipeline.predict_proba(df_for_model)[:, 1]
        predictions = self.pipeline.predict(df_for_model)

        results = []
        for idx in range(len(raw_records)):
            prob = float(probabilities[idx])
            pred = int(predictions[idx])
            raw_risk_score = int(np.clip(np.round(prob * 100), 0, 100))
            raw_risk_level = get_risk_tier(raw_risk_score)

            rec = sanitized_records[idx]
            return_rate = float(rec.get("return_rate", 0.0))
            refund_rate = float(rec.get("refund_rate", 0.0))
            order_count = int(rec.get("order_count", 0))

            # Small-History Policy Guardrail:
            # Protects against emerging wardrobing patterns in 4 <= order_count <= 10 with >= 75% returns
            # without penalizing normal single/early returns (order_count <= 3).
            guardrail_triggered = (4 <= order_count <= 10) and (return_rate >= 0.75)
            if guardrail_triggered and raw_risk_level == RISK_TIER_LOW:
                risk_level = RISK_TIER_MEDIUM
                risk_score = max(raw_risk_score, 45)
            else:
                risk_level = raw_risk_level
                risk_score = raw_risk_score

            action = self._determine_return_action(risk_level)

            risk_factors = self._extract_return_risk_factors(rec)
            mitigating_factors = self._extract_return_mitigating_factors(rec)

            if guardrail_triggered:
                guardrail_factor = "High return frequency observed within a limited order history."
                if guardrail_factor not in risk_factors:
                    risk_factors.insert(0, guardrail_factor)
                mitigating_factors = [m for m in mitigating_factors if "controlled return rate" not in m]

            explanation = self._generate_return_explanation(
                risk_level=risk_level,
                risk_score=risk_score,
                return_rate=return_rate,
                refund_rate=refund_rate,
                order_count=order_count,
                guardrail_triggered=guardrail_triggered,
            )

            results.append({
                "account_id": rec.get(ID_COLUMN, "unknown"),
                "return_abuse_prediction": pred,
                "return_risk_probability": round(prob, 4),
                "return_risk_score": risk_score,
                "return_risk_level": risk_level,
                "return_risk_factors": risk_factors,
                "return_mitigating_factors": mitigating_factors,
                "return_explanation": explanation,
                "recommended_return_action": action,
            })

        return results
