"""Unit tests for synthetic dataset generation."""

import pytest
import pandas as pd
from src.data_generator import generate_synthetic_dataset
from src.features import FEATURE_COLUMNS, TARGET_COLUMN, ID_COLUMN


def test_generate_synthetic_dataset_shape_and_columns():
    """Verify that dataset generates expected number of records and all required columns."""
    df = generate_synthetic_dataset(num_accounts=200, abuse_ratio=0.15, random_seed=42)
    assert len(df) == 200
    
    # Check all feature columns exist
    for col in FEATURE_COLUMNS:
        assert col in df.columns, f"Feature column '{col}' is missing"
    
    assert TARGET_COLUMN in df.columns
    assert ID_COLUMN in df.columns


def test_generate_synthetic_dataset_reproducibility():
    """Verify that using the same seed produces exact identical dataframes."""
    df1 = generate_synthetic_dataset(num_accounts=100, random_seed=99)
    df2 = generate_synthetic_dataset(num_accounts=100, random_seed=99)
    pd.testing.assert_frame_equal(df1, df2)


def test_generate_synthetic_dataset_no_nulls():
    """Verify there are no missing or NaN values in the generated dataset."""
    df = generate_synthetic_dataset(num_accounts=300, random_seed=42)
    assert df.isnull().sum().sum() == 0


def test_behavioral_logic_and_ranges():
    """Verify that generated behavioral metrics adhere to domain logic."""
    df = generate_synthetic_dataset(num_accounts=500, random_seed=42)

    # Return and refund counts cannot exceed order count
    assert (df["return_count"] <= df["order_count"]).all()
    assert (df["refund_count"] <= df["order_count"]).all()

    # Rates must be between 0 and 1
    assert (df["return_rate"] >= 0.0).all() and (df["return_rate"] <= 1.0).all()
    assert (df["refund_rate"] >= 0.0).all() and (df["refund_rate"] <= 1.0).all()

    # Target label must be strictly binary (0 or 1)
    assert set(df[TARGET_COLUMN].unique()).issubset({0, 1})
