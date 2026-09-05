"""Unified Scikit-Learn Preprocessing & Classification Pipeline for AI-RISK.

Constructs a reproducible, robust Pipeline combining:
- Numeric imputation for missing values
- OneHotEncoding with `handle_unknown='ignore'` for unknown categorical levels
- RandomForestClassifier for calibrated ensemble prediction
"""

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier

from src.features import NUMERIC_FEATURES, CATEGORICAL_FEATURES


def build_risk_pipeline(random_state: int = 42) -> Pipeline:
    """Build a complete, self-contained sklearn Pipeline for feature preprocessing and classification.

    The exact same pipeline is used during training and prediction, guaranteeing identical
    imputation, feature alignment, and handling of unseen categorical levels.

    Args:
        random_state: Seed for random forest reproducibility.

    Returns:
        sklearn.pipeline.Pipeline object.
    """
    # 1. Numeric Feature Transformer
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    # 2. Categorical Feature Transformer (robust to unseen categories)
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    # 3. Composite Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder="drop",  # Strictly drops unmodeled identifiers like account_id or targets
    )

    # 4. Final Estimator
    classifier = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=random_state,
        n_jobs=-1,
    )

    # 5. Assemble Full Pipeline
    risk_pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )

    return risk_pipeline
