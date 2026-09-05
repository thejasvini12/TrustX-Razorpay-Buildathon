"""Evaluation script for the specialized Return-Risk Scorer model.

Evaluates the saved model strictly on the held-out test dataset (data/return_risk_test.csv)
and outputs a comprehensive performance report.
"""

import os
import json
from typing import Dict, Any
import joblib
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
    classification_report,
)

from src.features import MODEL_FEATURES

RETURN_TARGET_COLUMN = "return_abuse_label"


def evaluate_return_risk_on_test_set(
    model_path: str = "models/return_risk_model.joblib",
    test_path: str = "data/return_risk_test.csv",
) -> Dict[str, Any]:
    """Load the trained return-risk model and evaluate strictly on the held-out test set."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Trained model not found at {model_path}.")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test dataset not found at {test_path}.")

    pipeline = joblib.load(model_path)
    test_df = pd.read_csv(test_path)

    X_test = test_df[MODEL_FEATURES]
    y_test = test_df[RETURN_TARGET_COLUMN]

    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_prob))

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0

    report = {
        "dataset_summary": {
            "test_set_size": len(test_df),
            "negative_samples (non-return abuse)": int((y_test == 0).sum()),
            "positive_samples (return abuse)": int((y_test == 1).sum()),
            "test_prevalence": round(float(y_test.mean()), 4),
        },
        "performance_metrics": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
        },
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
    }

    return report


if __name__ == "__main__":
    report = evaluate_return_risk_on_test_set()
    print("=" * 60)
    print("RETURN-RISK SCORER: HELD-OUT TEST EVALUATION REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))
