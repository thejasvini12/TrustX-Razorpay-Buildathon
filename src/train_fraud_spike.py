"""Training script for dedicated Fraud-Spike Detector model.

Trains a specialized classifier to detect sudden temporal surges in fraudulent activity
using baseline-to-current velocity, fraud rate deltas, and cluster connectivity indicators.
Saves model artifact to models/fraud_spike_model.joblib.
"""

import os
import json
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
)

from src.temporal_data_generator import SPIKE_FEATURE_COLUMNS, SPIKE_TARGET_COLUMN


def create_fraud_spike_pipeline(random_state: int = 42) -> Pipeline:
    """Build unified sklearn pipeline for fraud-spike detection."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                min_samples_split=4,
                min_samples_leaf=2,
                class_weight="balanced_subsample",
                random_state=random_state,
                n_jobs=-1,
            ),
        ),
    ])


def train_and_evaluate_fraud_spike_model(
    train_path: str = "data/fraud_spike_train.csv",
    val_path: str = "data/fraud_spike_val.csv",
    test_path: str = "data/fraud_spike_test.csv",
    model_output_path: str = "models/fraud_spike_model.joblib",
    metadata_output_path: str = "models/fraud_spike_metadata.json",
    random_state: int = 42,
) -> Tuple[Pipeline, Dict[str, Any]]:
    """Train on train set, validate, and evaluate on held-out test set."""
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)

    X_train = train_df[SPIKE_FEATURE_COLUMNS]
    y_train = train_df[SPIKE_TARGET_COLUMN]

    X_val = val_df[SPIKE_FEATURE_COLUMNS]
    y_val = val_df[SPIKE_TARGET_COLUMN]

    X_test = test_df[SPIKE_FEATURE_COLUMNS]
    y_test = test_df[SPIKE_TARGET_COLUMN]

    pipeline = create_fraud_spike_pipeline(random_state=random_state)
    pipeline.fit(X_train, y_train)

    # Validate
    val_probs = pipeline.predict_proba(X_val)[:, 1]
    val_roc = float(roc_auc_score(y_val, val_probs))

    # Evaluate strictly on held-out test set
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

    # Feature importances
    classifier = pipeline.named_steps["classifier"]
    importances = classifier.feature_importances_
    top_features = sorted(
        [{"feature": f, "importance": round(float(imp), 4)} for f, imp in zip(SPIKE_FEATURE_COLUMNS, importances)],
        key=lambda x: x["importance"],
        reverse=True,
    )

    metadata = {
        "model_type": "RandomForestClassifier",
        "task": "Temporal Fraud-Spike Detection",
        "target_column": SPIKE_TARGET_COLUMN,
        "features": SPIKE_FEATURE_COLUMNS,
        "dataset_summary": {
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "test_positive_samples": int(y_test.sum()),
            "test_prevalence": round(float(y_test.mean()), 4),
        },
        "validation_metrics": {
            "val_roc_auc": round(val_roc, 4),
        },
        "test_metrics": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "confusion_matrix": {
                "true_negatives": int(tn),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp),
            },
        },
        "top_features": top_features[:8],
    }

    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(pipeline, model_output_path)
    with open(metadata_output_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return pipeline, metadata


if __name__ == "__main__":
    pipeline, metadata = train_and_evaluate_fraud_spike_model()
    print("Fraud-Spike Detector Model Trained Successfully.")
    print(json.dumps(metadata["test_metrics"], indent=2))
