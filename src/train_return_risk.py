"""Model training pipeline for the dedicated Return-Risk Scorer.

Trains a specialized classifier targeting Return & Refund Abuse (Serial Wardrobing),
evaluates metrics on the held-out test partition, and serializes the model to models/return_risk_model.joblib.
"""

import os
import json
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
    classification_report,
)

from src.features import NUMERIC_FEATURES, CATEGORICAL_FEATURES, MODEL_FEATURES

RETURN_TARGET_COLUMN = "return_abuse_label"


def create_return_risk_pipeline(random_state: int = 42) -> Pipeline:
    """Build unified sklearn preprocessing and classifier pipeline for return abuse risk."""
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])

    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )

    classifier = RandomForestClassifier(
        n_estimators=120,
        max_depth=8,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=random_state,
        n_jobs=-1,
    )

    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", classifier),
    ])


def train_and_evaluate_return_risk_model(
    train_path: str = "data/return_risk_train.csv",
    test_path: str = "data/return_risk_test.csv",
    model_output_path: str = "models/return_risk_model.joblib",
    metadata_output_path: str = "models/return_risk_metadata.json",
    random_state: int = 42,
) -> Tuple[Pipeline, Dict[str, Any]]:
    """Train return-risk model on training partition and evaluate strictly on held-out test partition."""
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        raise FileNotFoundError(f"Datasets not found at {train_path} or {test_path}.")

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    X_train = train_df[MODEL_FEATURES]
    y_train = train_df[RETURN_TARGET_COLUMN]

    X_test = test_df[MODEL_FEATURES]
    y_test = test_df[RETURN_TARGET_COLUMN]

    pipeline = create_return_risk_pipeline(random_state=random_state)
    pipeline.fit(X_train, y_train)

    # Predict on held-out test set
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    # Metrics
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_prob))

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0

    # Extract feature importances
    preprocessor = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]
    cat_feature_names = preprocessor.named_transformers_["cat"].named_steps["onehot"].get_feature_names_out(CATEGORICAL_FEATURES)
    all_feature_names = list(NUMERIC_FEATURES) + list(cat_feature_names)
    importances = classifier.feature_importances_

    top_features = sorted(
        [{"feature": f, "importance": round(float(imp), 4)} for f, imp in zip(all_feature_names, importances)],
        key=lambda x: x["importance"],
        reverse=True,
    )

    metadata = {
        "model_type": "RandomForestClassifier",
        "task": "Return & Refund Abuse Risk Detection",
        "target_column": RETURN_TARGET_COLUMN,
        "features": MODEL_FEATURES,
        "dataset_summary": {
            "total_samples": len(train_df) + len(test_df),
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "train_positive_samples": int(y_train.sum()),
            "test_positive_samples": int(y_test.sum()),
            "train_prevalence": round(float(y_train.mean()), 4),
            "test_prevalence": round(float(y_test.mean()), 4),
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
        "top_features": top_features[:10],
    }

    # Save artifacts
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(pipeline, model_output_path)
    with open(metadata_output_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return pipeline, metadata


if __name__ == "__main__":
    pipeline, metadata = train_and_evaluate_return_risk_model()
    print("Return Risk Model Trained and Evaluated Successfully.")
    print(json.dumps(metadata["test_metrics"], indent=2))
