"""Model training pipeline for Merchant Abuse Detection.

Trains a unified Scikit-Learn Preprocessing + RandomForest Pipeline on synthetic
account behavioral data, strictly evaluates on held-out test set, extracts
feature importances, and persists the complete pipeline artifact for backend risk scoring.
"""

import os
import json
from datetime import datetime
from typing import Tuple, Dict, Any
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from src.features import ID_COLUMN, TARGET_COLUMN, MODEL_FEATURES
from src.data_generator import generate_synthetic_dataset, save_dataset
from src.model_pipeline import build_risk_pipeline
from src.evaluate import compute_metrics, get_feature_importances, format_metrics_report


def train_pipeline(
    data_path: str = None,
    model_output_dir: str = "models",
    data_output_dir: str = "data",
    test_size: float = 0.20,
    random_state: int = 42,
    num_synthetic_samples: int = 5000,
) -> Tuple[Pipeline, Dict[str, Any]]:
    """Execute the end-to-end training and evaluation workflow using a unified sklearn Pipeline.

    Args:
        data_path: Optional path to an existing dataset CSV. If None, generates synthetic dataset.
        model_output_dir: Directory where trained model artifacts will be saved.
        data_output_dir: Directory to save generated and split dataset CSVs.
        test_size: Proportion of dataset to hold out for evaluation (default 0.20).
        random_state: Random state for deterministic data splitting and training.
        num_synthetic_samples: Number of samples to generate if data_path is None.

    Returns:
        Tuple of (trained_pipeline, test_metrics_dict).
    """
    # 1. Load or Generate Dataset
    if data_path and os.path.exists(data_path):
        print(f"[*] Loading existing dataset from: {data_path}")
        df = pd.read_csv(data_path)
    else:
        print(f"[*] Generating {num_synthetic_samples} synthetic accounts (seed={random_state})...")
        df = generate_synthetic_dataset(
            num_accounts=num_synthetic_samples,
            abuse_ratio=0.15,
            random_seed=random_state,
        )
        os.makedirs(data_output_dir, exist_ok=True)
        raw_csv_path = os.path.join(data_output_dir, "synthetic_accounts.csv")
        save_dataset(df, raw_csv_path)
        print(f"[*] Full dataset saved to: {raw_csv_path}")

    # Exclude ID_COLUMN and TARGET_COLUMN from model input features X
    feature_cols = [c for c in MODEL_FEATURES if c in df.columns]
    X = df[feature_cols]
    y = df[TARGET_COLUMN]

    # 2. Strict Train / Test Split
    print(f"[*] Splitting dataset: {int((1-test_size)*100)}% Train / {int(test_size*100)}% Held-out Test (Stratified)...")
    X_train, X_test, y_train, y_test, indices_train, indices_test = train_test_split(
        X, y, df.index,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    # Save train and test splits for reproducibility & audit
    train_df = df.loc[indices_train].copy()
    test_df = df.loc[indices_test].copy()
    os.makedirs(data_output_dir, exist_ok=True)
    train_df.to_csv(os.path.join(data_output_dir, "train.csv"), index=False)
    test_df.to_csv(os.path.join(data_output_dir, "test.csv"), index=False)
    print(f"[*] Train set: {len(train_df)} rows | Held-out Test set: {len(test_df)} rows")

    # 3. Assemble and Fit Full Pipeline
    print("[*] Training unified Preprocessing + RandomForest Pipeline on training data only...")
    risk_pipeline = build_risk_pipeline(random_state=random_state)
    risk_pipeline.fit(X_train, y_train)

    # 4. Strict Evaluation on Held-out Test Set
    print("[*] Evaluating pipeline strictly on the held-out test set...")
    y_test_pred = risk_pipeline.predict(X_test)
    y_test_prob = risk_pipeline.predict_proba(X_test)[:, 1]

    metrics = compute_metrics(y_true=y_test.values, y_pred=y_test_pred, y_prob=y_test_prob)
    feature_importances = get_feature_importances(risk_pipeline)

    # Print evaluation report
    report = format_metrics_report(metrics, feature_importances)
    print("\n" + report + "\n")

    # 5. Persist Full Pipeline Artifact & Metadata
    os.makedirs(model_output_dir, exist_ok=True)
    model_path = os.path.join(model_output_dir, "risk_engine_rf.joblib")
    joblib.dump(risk_pipeline, model_path)
    print(f"[*] Serialized full Pipeline saved to: {model_path}")

    rf_step = risk_pipeline.named_steps["classifier"]
    metadata = {
        "model_type": "Pipeline(ColumnTransformer + RandomForestClassifier)",
        "trained_at": datetime.now().isoformat(),
        "random_state": random_state,
        "input_features": feature_cols,
        "id_column": ID_COLUMN,
        "target_column": TARGET_COLUMN,
        "hyperparameters": {
            "n_estimators": rf_step.n_estimators,
            "max_depth": rf_step.max_depth,
            "min_samples_split": rf_step.min_samples_split,
            "min_samples_leaf": rf_step.min_samples_leaf,
            "class_weight": str(rf_step.class_weight),
        },
        "evaluation_metrics_held_out": metrics,
        "top_features": [{"feature": feat, "importance": imp} for feat, imp in feature_importances],
    }

    metadata_path = os.path.join(model_output_dir, "model_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[*] Model metadata saved to: {metadata_path}")

    return risk_pipeline, metrics


if __name__ == "__main__":
    train_pipeline()
