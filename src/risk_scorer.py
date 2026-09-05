"""Production-grade Risk Scorer & Inference Engine for Merchant Abuse Risk.

Provides:
- Input schema validation and sanitization.
- Safe missing value and extreme input handling.
- Unknown categorical level tolerance.
- Prediction with a unified Scikit-Learn Pipeline.
- Calibrated 0-100 risk scores, LOW/MEDIUM/HIGH risk levels, data quality scores, and warning logs.
"""

import os
import json
from typing import Dict, Any, List, Union, Optional
import joblib
import numpy as np
import pandas as pd

from src.features import (
    ID_COLUMN,
    TARGET_COLUMN,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    get_risk_tier,
    validate_and_sanitize_account_input,
    RISK_TIER_LOW,
    RISK_TIER_MEDIUM,
    RISK_TIER_HIGH,
)
from src.explainer import RiskExplainer
from src.decision_engine import AdaptiveDecisionEngine
from src.return_risk_scorer import ReturnRiskScorer


class RiskScorer:
    """Production inference engine to score unseen merchant accounts for coordinated abuse risk."""

    def __init__(
        self,
        model_path: str = os.path.join("models", "risk_engine_rf.joblib"),
        metadata_path: str = os.path.join("models", "model_metadata.json"),
        return_risk_model_path: str = os.path.join("models", "return_risk_model.joblib"),
        return_risk_metadata_path: str = os.path.join("models", "return_risk_metadata.json"),
    ):
        """Initialize the risk scorer by loading the serialized sklearn Pipeline."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Trained pipeline artifact not found at '{model_path}'. Run training first.")

        self.pipeline = joblib.load(model_path)
        self.metadata = {}
        if metadata_path and os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)

        # Initialize modular explainability engine
        self.explainer = RiskExplainer(pipeline=self.pipeline, model_metadata=self.metadata)

        # Initialize adaptive decision policy engine
        self.decision_engine = AdaptiveDecisionEngine()

        # Initialize dedicated Return-Risk Scorer
        if os.path.exists(return_risk_model_path):
            self.return_risk_scorer = ReturnRiskScorer(
                model_path=return_risk_model_path,
                metadata_path=return_risk_metadata_path,
            )
        else:
            self.return_risk_scorer = None

    def _determine_action(self, risk_level: str) -> str:
        """Determine automated merchant defense policy action for account/checkout authorization.
        
        Controls transactional authorization (ALLOW, MANUAL_REVIEW, CHALLENGE_OR_BLOCK).
        Operates independently of specialized post-purchase return/refund authorization.
        """
        if risk_level == RISK_TIER_LOW:
            return "ALLOW"
        elif risk_level == RISK_TIER_MEDIUM:
            return "MANUAL_REVIEW"
        elif risk_level == RISK_TIER_HIGH:
            return "CHALLENGE_OR_BLOCK"
        return "MANUAL_REVIEW"

    def _extract_risk_factors(self, data: Dict[str, Any]) -> List[str]:
        """Identify specific elevated behavioral attributes for an account (backward compatible helper)."""
        return self.explainer.extract_risk_factors(data)

    def predict_account(self, input_record: Dict[str, Any]) -> Dict[str, Any]:
        """Predict risk for a single unseen account dictionary.

        Args:
            input_record: Dictionary containing merchant/account features.

        Returns:
            Dictionary containing prediction, risk score, risk tier, and metadata.
        """
        if not isinstance(input_record, dict):
            raise TypeError(f"input_record must be a dictionary, got {type(input_record).__name__}.")
        results = self.predict_accounts([input_record])
        return results[0]

    def predict_accounts(
        self,
        input_data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Validate, sanitize, and score one or more account records.

        Args:
            input_data: Single dictionary, list of dictionaries, or pandas DataFrame.

        Returns:
            List of structured risk prediction dictionaries.
        """
        # Standardize input to list of dicts
        if isinstance(input_data, dict):
            raw_records = [input_data]
        elif isinstance(input_data, list):
            raw_records = input_data
        elif isinstance(input_data, pd.DataFrame):
            raw_records = input_data.to_dict(orient="records")
        else:
            raise TypeError(f"input_data must be a dict, list of dicts, or pandas DataFrame, got {type(input_data).__name__}.")

        if not raw_records:
            return []

        # Validate that each item is a dictionary
        for idx, record in enumerate(raw_records):
            if not isinstance(record, dict):
                raise TypeError(f"Each record in input_data must be a dictionary, but record at index {idx} is {type(record).__name__}.")

        # Step 1: Validate and sanitize every input record independently
        sanitized_records = []
        data_quality_scores = []
        warning_lists = []
        account_ids = []

        for record in raw_records:
            sanitized, quality_score, warnings = validate_and_sanitize_account_input(record)
            sanitized_records.append(sanitized)
            data_quality_scores.append(quality_score)
            warning_lists.append(warnings)
            account_ids.append(sanitized[ID_COLUMN])

        # Step 2: Build feature DataFrame for the model (STRICTLY EXCLUDING account_id and target labels)
        df_for_model = pd.DataFrame(sanitized_records)[MODEL_FEATURES]

        # Step 3: Run prediction through the unified Scikit-Learn Pipeline
        probabilities = self.pipeline.predict_proba(df_for_model)[:, 1]
        predictions = self.pipeline.predict(df_for_model)

        # Step 4: Assemble results
        results = []
        for idx in range(len(raw_records)):
            prob = float(probabilities[idx])
            pred = int(predictions[idx])
            risk_score = int(np.clip(np.round(prob * 100), 0, 100))
            risk_level = get_risk_tier(risk_score)
            action = self._determine_action(risk_level)

            # Generate dual-layer explanations with score and tier context
            explanation = self.explainer.explain(
                data=sanitized_records[idx],
                risk_score=risk_score,
                risk_level=risk_level,
            )

            # Generate contextual adaptive decision policy
            decision_policy = self.decision_engine.evaluate_decision(
                risk_score=risk_score,
                risk_level=risk_level,
                risk_probability=prob,
                account_data=sanitized_records[idx],
                signals=explanation["risk_increasing_signals"],
            )

            # Evaluate dedicated Return & Refund Abuse risk
            return_risk = None
            if self.return_risk_scorer is not None:
                rr_res = self.return_risk_scorer.predict_account(sanitized_records[idx])
                return_risk = {k: v for k, v in rr_res.items() if k != "account_id"}

            results.append({
                "account_id": account_ids[idx],
                "prediction": pred,
                "risk_probability": round(prob, 4),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_tier": risk_level,
                "data_quality_score": data_quality_scores[idx],
                "warnings": warning_lists[idx],
                "recommended_action": action,
                "explanation_summary": explanation["explanation_summary"],
                "decision_reasoning": explanation["decision_reasoning"],
                "risk_increasing_signals": explanation["risk_increasing_signals"],
                "risk_reducing_signals": explanation["risk_reducing_signals"],
                "risk_factors": explanation["risk_factors"],
                "mitigating_factors": explanation["mitigating_factors"],
                "feature_contributions": explanation["feature_contributions"],
                "decision_policy": decision_policy,
                "return_risk": return_risk,
            })

        return results


def predict_account_risk(
    input_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
    model_path: str = os.path.join("models", "risk_engine_rf.joblib"),
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Convenience functional API to score risk on unseen account data.

    Args:
        input_data: Dict for single account, or list of dicts / DataFrame for batch accounts.
        model_path: Path to serialized sklearn Pipeline.

    Returns:
        Dict (for single record) or List[Dict] (for batch records) containing risk assessments.
    """
    scorer = RiskScorer(model_path=model_path)
    if isinstance(input_data, dict):
        return scorer.predict_account(input_data)
    else:
        return scorer.predict_accounts(input_data)
