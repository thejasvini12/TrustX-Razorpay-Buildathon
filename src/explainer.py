"""Modular Explainability Engine for Merchant Abuse Risk Detection.

Provides transparent, evaluator-friendly explanations for ML predictions:
1. Decision Overview:
   - Final Risk Tier: LOW / MEDIUM / HIGH
   - Explanation Summary: Dynamic high-level rationale for the combined ML assessment.
   - Decision Reasoning ("Why this tier?"): Explains the quantitative score range and
     clarifies that individual directional signals do not override the ensemble model's
     combined multidimensional assessment.
2. Signal Categorization:
   - Risk Increasing Signals: Behavioral patterns associated with higher risk.
   - Risk Reducing Signals: Protective patterns associated with customer trust.
   - Backward-compatible risk_factors and mitigating_factors lists.
3. Model-Informed Feature Influences (Feature Contributions):
   - Ranked list of features based on the trained Random Forest classifier's
     global feature_importances_ and observed feature values.

Important Note on Terminology & Methodology:
Feature importances represent GLOBAL model feature reliance across all 150 decision trees
(Mean Decrease in Impurity). They indicate how strongly the model weights each feature overall.
Directional labels (INCREASES_RISK, DECREASES_RISK, NEUTRAL) describe whether the observed
value falls in an elevated or healthy domain range. They are NOT exact causal or per-instance
SHAP values.
"""

from typing import Dict, Any, List, Tuple, Optional
from sklearn.pipeline import Pipeline
from src.features import RISK_TIER_LOW, RISK_TIER_MEDIUM, RISK_TIER_HIGH


class RiskExplainer:
    """Explains predictions produced by the AI-RISK machine learning pipeline."""

    def __init__(
        self,
        pipeline: Optional[Pipeline] = None,
        model_metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize explainer with trained pipeline and model metadata."""
        self.pipeline = pipeline
        self.metadata = model_metadata or {}
        self._feature_importances: Dict[str, float] = {}
        self._init_feature_importances()

    def _init_feature_importances(self) -> None:
        """Extract and aggregate global feature importances from pipeline or metadata."""
        # 1. Try reading from pre-extracted metadata if available
        if self.metadata and "top_features" in self.metadata:
            for item in self.metadata["top_features"]:
                feat = item["feature"]
                imp = float(item["importance"])
                base_feat = feat
                if feat.startswith("primary_payment_method_"):
                    base_feat = "primary_payment_method"
                elif feat.startswith("device_type_"):
                    base_feat = "device_type"

                self._feature_importances[base_feat] = self._feature_importances.get(base_feat, 0.0) + imp

        # 2. Fall back to pipeline directly if metadata was not populated
        elif self.pipeline is not None:
            try:
                preprocessor = self.pipeline.named_steps.get("preprocessor")
                classifier = self.pipeline.named_steps.get("classifier")
                if preprocessor and classifier and hasattr(classifier, "feature_importances_"):
                    raw_names = preprocessor.get_feature_names_out()
                    importances = classifier.feature_importances_
                    for raw_name, imp in zip(raw_names, importances):
                        clean_name = raw_name.replace("num__", "").replace("cat__", "")
                        base_feat = clean_name
                        if clean_name.startswith("primary_payment_method_"):
                            base_feat = "primary_payment_method"
                        elif clean_name.startswith("device_type_"):
                            base_feat = "device_type"
                        self._feature_importances[base_feat] = self._feature_importances.get(base_feat, 0.0) + float(imp)
            except Exception:
                pass

    def extract_risk_factors(self, data: Dict[str, Any]) -> List[str]:
        """Identify specific elevated behavioral attributes associated with higher risk."""
        factors = []
        return_rate = data.get("return_rate", 0.0)
        refund_rate = data.get("refund_rate", 0.0)
        susp_score = data.get("suspicious_activity_score", 0.0)
        device_count = data.get("device_count", 0)
        ip_count = data.get("ip_count", 0)
        payment_inst_count = data.get("payment_instrument_count", 0)
        account_age_days = data.get("account_age_days", 999)
        order_count = data.get("order_count", 0)
        high_val_count = data.get("high_value_order_count", 0)
        device_type = data.get("device_type", "unknown")
        payment_method = data.get("primary_payment_method", "unknown")

        if return_rate > 0.50:
            factors.append(f"High return rate ({return_rate:.1%})")
        elif return_rate > 0.30:
            factors.append(f"Elevated return rate ({return_rate:.1%})")

        if refund_rate > 0.50:
            factors.append(f"High refund claim rate ({refund_rate:.1%})")
        elif refund_rate > 0.30:
            factors.append(f"Elevated refund claim rate ({refund_rate:.1%})")

        if susp_score > 0.60:
            factors.append(f"Elevated syndicate activity indicator ({susp_score:.2f})")
        elif susp_score > 0.30:
            factors.append(f"Moderate external velocity anomaly indicator ({susp_score:.2f})")

        if device_count >= 3:
            factors.append(f"Multiple linked hardware devices ({int(device_count)})")

        if ip_count >= 4:
            factors.append(f"High IP address turnover ({int(ip_count)} distinct IPs)")

        if payment_inst_count >= 3:
            factors.append(f"High payment instrument turnover ({int(payment_inst_count)})")

        if account_age_days <= 14 and order_count >= 3:
            factors.append(f"Fresh account velocity burst (age: {int(account_age_days)}d, orders: {int(order_count)})")

        if high_val_count >= 3 and order_count > 0 and (high_val_count / order_count) >= 0.40:
            factors.append(f"Concentrated high-value order volume ({int(high_val_count)} orders)")

        if device_type == "emulator_bot":
            factors.append("Detected potential emulator/bot device fingerprint")

        if payment_method in ["virtual_card", "crypto_gift_card"]:
            factors.append(f"High-risk payment method ({payment_method})")

        if not factors:
            factors.append("Normal shopping patterns within standard thresholds")

        return factors

    def extract_mitigating_factors(self, data: Dict[str, Any]) -> List[str]:
        """Identify positive protective signals associated with reduced risk."""
        mitigations = []
        account_age_days = data.get("account_age_days", 0)
        order_count = data.get("order_count", 0)
        return_rate = data.get("return_rate", 0.0)
        refund_rate = data.get("refund_rate", 0.0)
        susp_score = data.get("suspicious_activity_score", 0.0)
        device_count = data.get("device_count", 0)
        ip_count = data.get("ip_count", 0)
        payment_inst_count = data.get("payment_instrument_count", 0)
        payment_method = data.get("primary_payment_method", "unknown")

        if account_age_days >= 180:
            mitigations.append(f"Established account tenure ({int(account_age_days)} days)")
        elif account_age_days >= 60:
            mitigations.append(f"Seasoned account history ({int(account_age_days)} days)")

        if order_count >= 10 and return_rate <= 0.15:
            mitigations.append(f"Strong purchase history with low return rate ({int(order_count)} orders, {return_rate:.1%} returns)")
        elif order_count >= 3 and return_rate == 0.0:
            mitigations.append("Zero returned orders across transaction history")

        if refund_rate == 0.0 and order_count >= 2:
            mitigations.append("Zero refund claims filed")
        elif refund_rate <= 0.10 and order_count >= 5:
            mitigations.append(f"Healthy low refund rate ({refund_rate:.1%})")

        if susp_score <= 0.10:
            mitigations.append("Clean external velocity & network risk profile")

        if device_count == 1 and ip_count <= 2:
            mitigations.append("Consistent single-device access pattern")

        if payment_inst_count == 1:
            mitigations.append("Stable single payment instrument on file")

        if payment_method in ["credit_card", "debit_card", "apple_pay"]:
            mitigations.append(f"Standard verified payment method ({payment_method})")

        return mitigations

    def compute_feature_contributions(
        self,
        data: Dict[str, Any],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Generate ranked model-informed feature influences based on global feature importances and input values."""
        contributions = []

        feature_evaluators = {
            "suspicious_activity_score": lambda v: (
                "INCREASES_RISK" if v > 0.25 else "DECREASES_RISK",
                f"Syndicate anomaly score ({v:.2f}) is " + ("associated with elevated risk" if v > 0.25 else "within safe baseline range"),
            ),
            "return_rate": lambda v: (
                "INCREASES_RISK" if v > 0.20 else "DECREASES_RISK",
                f"Return rate of {v:.1%} is " + ("associated with elevated return/wardrobing activity" if v > 0.20 else "associated with standard shopping behavior"),
            ),
            "refund_rate": lambda v: (
                "INCREASES_RISK" if v > 0.20 else "DECREASES_RISK",
                f"Refund claim rate of {v:.1%} is " + ("associated with elevated dispute risk" if v > 0.20 else "healthy and low"),
            ),
            "return_count": lambda v: (
                "INCREASES_RISK" if v >= 5 else ("NEUTRAL" if v > 1 else "DECREASES_RISK"),
                f"Total return count of {int(v)} orders",
            ),
            "refund_count": lambda v: (
                "INCREASES_RISK" if v >= 5 else ("NEUTRAL" if v > 1 else "DECREASES_RISK"),
                f"Total refund claim count of {int(v)}",
            ),
            "account_age_days": lambda v: (
                "DECREASES_RISK" if v >= 60 else "INCREASES_RISK",
                f"Account age of {int(v)} days " + ("is associated with customer tenure trust" if v >= 60 else "is associated with new account risk"),
            ),
            "high_value_order_count": lambda v: (
                "INCREASES_RISK" if v >= 3 else "NEUTRAL",
                f"High-value order volume ({int(v)} transactions)",
            ),
            "total_spend": lambda v: (
                "NEUTRAL" if 20 <= v <= 2000 else ("INCREASES_RISK" if v > 2000 else "DECREASES_RISK"),
                f"Gross lifetime spend of ${v:,.2f}",
            ),
            "average_order_value": lambda v: (
                "INCREASES_RISK" if v > 130 else "NEUTRAL",
                f"Average transaction order value of ${v:,.2f}",
            ),
            "order_count": lambda v: (
                "DECREASES_RISK" if v >= 5 else "NEUTRAL",
                f"Lifetime completed order volume ({int(v)})",
            ),
            "payment_instrument_count": lambda v: (
                "INCREASES_RISK" if v >= 3 else "DECREASES_RISK",
                f"Linked payment cards ({int(v)}) " + ("is associated with card turnover risk" if v >= 3 else "is stable"),
            ),
            "device_count": lambda v: (
                "INCREASES_RISK" if v >= 3 else "DECREASES_RISK",
                f"Linked hardware devices ({int(v)}) " + ("is associated with multi-device risk" if v >= 3 else "is standard"),
            ),
            "ip_count": lambda v: (
                "INCREASES_RISK" if v >= 4 else "DECREASES_RISK",
                f"Distinct IP addresses ({int(v)}) " + ("is associated with network shifting" if v >= 4 else "is standard"),
            ),
            "primary_payment_method": lambda v: (
                "INCREASES_RISK" if v in ["virtual_card", "crypto_gift_card"] else "DECREASES_RISK",
                f"Payment method '{v}' is " + ("associated with elevated abuse risk" if v in ["virtual_card", "crypto_gift_card"] else "a standard payment method"),
            ),
            "device_type": lambda v: (
                "INCREASES_RISK" if v == "emulator_bot" else "NEUTRAL",
                f"Device environment '{v}' " + ("flags automated emulator/bot tooling" if v == "emulator_bot" else "is a standard client"),
            ),
        }

        for feat, importance in self._feature_importances.items():
            if feat in data:
                val = data[feat]
                evaluator = feature_evaluators.get(
                    feat,
                    lambda v: ("NEUTRAL", f"Observed feature value: {v}")
                )
                direction, summary = evaluator(val)
                contributions.append({
                    "feature": feat,
                    "value": val,
                    "importance": round(float(importance), 4),
                    "contribution_direction": direction,
                    "summary": summary,
                })

        # Sort by global feature importance descending
        contributions.sort(key=lambda x: x["importance"], reverse=True)
        return contributions[:top_k]

    def generate_explanation_summary(
        self,
        risk_level: str,
        risk_score: int,
        has_risk_signals: bool,
        has_mitigating_signals: bool,
    ) -> str:
        """Generate a concise, dynamic high-level summary explaining the final assessment."""
        if risk_level == RISK_TIER_LOW:
            if has_risk_signals:
                return (
                    f"Overall risk is LOW (score: {risk_score}/100). While individual behavioral signals show "
                    f"minor variations, the trained machine learning model's combined multidimensional assessment "
                    f"remains firmly within the LOW-risk range."
                )
            return (
                f"Overall risk is LOW (score: {risk_score}/100). The account demonstrates healthy shopping, "
                f"return, and payment behaviors consistent with legitimate customer activity."
            )
        elif risk_level == RISK_TIER_MEDIUM:
            return (
                f"Overall risk is MEDIUM (score: {risk_score}/100). The account exhibits a combination of "
                f"elevated risk signals alongside protective history, placing it in the borderline threshold "
                f"for manual review."
            )
        else:
            return (
                f"Overall risk is HIGH (score: {risk_score}/100). Multiple strong risk-increasing signals "
                f"combine across velocity, return, and network features to produce a high-confidence abuse assessment."
            )

    def generate_decision_reasoning(
        self,
        risk_level: str,
        risk_score: int,
        risk_increasing: List[str],
        risk_reducing: List[str],
    ) -> str:
        """Generate a clear explanation detailing why the final score landed in its qualitative tier."""
        if risk_level == RISK_TIER_LOW:
            reason = (
                f"The final calibrated risk score is {risk_score}/100, which falls below the threshold of 30 (LOW tier). "
                f"Individual features that show elevated values do not override the overall model decision, "
                f"as the combined multidimensional pattern is predominantly legitimate."
            )
            if risk_reducing:
                reason += f" Primary trust drivers include: {', '.join(risk_reducing[:3])}."
            return reason

        elif risk_level == RISK_TIER_MEDIUM:
            reason = (
                f"The final calibrated risk score is {risk_score}/100, which falls in the 30–69 range (MEDIUM tier). "
                f"This borderline score reflects conflicting signals: elevated risk drivers are partially offset "
                f"by mitigating account history, warranting human review."
            )
            return reason

        else:
            reason = (
                f"The final calibrated risk score is {risk_score}/100, which meets or exceeds the threshold of 70 (HIGH tier). "
                f"The model identified severe coordinated or serial abuse indicators with high confidence."
            )
            if risk_increasing:
                reason += f" Primary risk drivers include: {', '.join(risk_increasing[:3])}."
            return reason

    def explain(
        self,
        data: Dict[str, Any],
        risk_score: int = 0,
        risk_level: str = RISK_TIER_LOW,
    ) -> Dict[str, Any]:
        """Produce a complete, structured, and evaluator-friendly explanation."""
        risk_increasing = [f for f in self.extract_risk_factors(data) if "Normal shopping patterns" not in f]
        risk_reducing = self.extract_mitigating_factors(data)
        feature_contributions = self.compute_feature_contributions(data)

        # Backward compatible lists
        risk_factors = self.extract_risk_factors(data)
        mitigating_factors = risk_reducing

        # Generate clear dynamic explanations
        explanation_summary = self.generate_explanation_summary(
            risk_level=risk_level,
            risk_score=risk_score,
            has_risk_signals=len(risk_increasing) > 0,
            has_mitigating_signals=len(risk_reducing) > 0,
        )
        decision_reasoning = self.generate_decision_reasoning(
            risk_level=risk_level,
            risk_score=risk_score,
            risk_increasing=risk_increasing,
            risk_reducing=risk_reducing,
        )

        return {
            "explanation_summary": explanation_summary,
            "decision_reasoning": decision_reasoning,
            "risk_increasing_signals": risk_increasing,
            "risk_reducing_signals": risk_reducing,
            "risk_factors": risk_factors,
            "mitigating_factors": mitigating_factors,
            "feature_contributions": feature_contributions,
        }
