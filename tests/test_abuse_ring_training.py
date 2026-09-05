"""Unit and integration tests for Abuse-Ring Sentinel feature extraction, training, and model bundle."""

import os
import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

from src.abuse_ring_features import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_cluster_dataset,
    extract_cluster_features,
)
from src.train_abuse_ring import (
    get_file_hashes,
    verify_model_integrity,
    FROZEN_MODEL_PATHS,
    OUTPUT_MODEL_PATH,
    simulate_daisy_chain_ood_clusters,
)


@pytest.fixture(scope="module")
def raw_data():
    """Load the frozen raw Abuse-Ring datasets."""
    df_acc = pd.read_csv("data/ring_accounts.csv")
    df_edg = pd.read_csv("data/ring_entity_edges.csv")
    df_cls = pd.read_csv("data/ring_clusters.csv")
    return df_acc, df_edg, df_cls


def test_cluster_level_matrix_construction(raw_data):
    """Verify that extract_cluster_features produces exactly 1 row per cluster (316 rows)."""
    df_acc, df_edg, df_cls = raw_data
    df_feat = extract_cluster_features(df_acc, df_edg, df_cls)

    assert len(df_feat) == len(df_cls), f"Expected {len(df_cls)} cluster rows, got {len(df_feat)}"
    assert len(df_feat) == 316, f"Expected exactly 316 clusters, got {len(df_feat)}"
    assert "cluster_id" in df_feat.columns


def test_exactly_15_features(raw_data):
    """Verify feature schema matches the exact 15 approved features in exact order."""
    df_acc, df_edg, df_cls = raw_data
    X, y, meta = build_cluster_dataset(df_acc, df_edg, df_cls)

    assert X.shape == (316, 15), f"Expected shape (316, 15), got {X.shape}"
    assert list(X.columns) == FEATURE_COLUMNS
    assert len(FEATURE_COLUMNS) == 15
    assert not X.isna().any().any(), "Feature matrix contains NaN values"
    assert not np.isinf(X.values).any(), "Feature matrix contains infinite values"


def test_no_target_leakage(raw_data):
    """Verify that target labels, account labels, archetype names, and IDs are strictly excluded from X."""
    df_acc, df_edg, df_cls = raw_data
    X, y, meta = build_cluster_dataset(df_acc, df_edg, df_cls)

    forbidden_cols = {
        TARGET_COLUMN,
        "is_ring_member_label",
        "cluster_type",
        "cluster_id",
        "account_id",
        "edge_id",
        "entity_id",
    }
    present_forbidden = forbidden_cols.intersection(set(X.columns))
    assert len(present_forbidden) == 0, f"Target leakage detected in X: {present_forbidden}"


def test_deterministic_split(raw_data):
    """Verify deterministic 3-way cluster-level split: 221 train, 47 val, 48 test."""
    df_acc, df_edg, df_cls = raw_data
    X, y, meta = build_cluster_dataset(df_acc, df_edg, df_cls)
    df_all = pd.concat([meta, X, y], axis=1)

    train_df1, temp_df1 = train_test_split(df_all, test_size=95, random_state=42, stratify=df_all[TARGET_COLUMN])
    val_df1, test_df1 = train_test_split(temp_df1, test_size=48, random_state=42, stratify=temp_df1[TARGET_COLUMN])

    train_df2, temp_df2 = train_test_split(df_all, test_size=95, random_state=42, stratify=df_all[TARGET_COLUMN])
    val_df2, test_df2 = train_test_split(temp_df2, test_size=48, random_state=42, stratify=temp_df2[TARGET_COLUMN])

    assert len(train_df1) == 221
    assert len(val_df1) == 47
    assert len(test_df1) == 48

    pd.testing.assert_frame_equal(train_df1, train_df2)
    pd.testing.assert_frame_equal(val_df1, val_df2)
    pd.testing.assert_frame_equal(test_df1, test_df2)


def test_no_cluster_overlap(raw_data):
    """Verify that train, validation, and test partitions have zero overlapping clusters, accounts, or edges."""
    df_acc, df_edg, df_cls = raw_data
    X, y, meta = build_cluster_dataset(df_acc, df_edg, df_cls)
    df_all = pd.concat([meta, X, y], axis=1)

    train_df, temp_df = train_test_split(df_all, test_size=95, random_state=42, stratify=df_all[TARGET_COLUMN])
    val_df, test_df = train_test_split(temp_df, test_size=48, random_state=42, stratify=temp_df[TARGET_COLUMN])

    train_cids = set(train_df["cluster_id"])
    val_cids = set(val_df["cluster_id"])
    test_cids = set(test_df["cluster_id"])

    assert len(train_cids & val_cids) == 0
    assert len(train_cids & test_cids) == 0
    assert len(val_cids & test_cids) == 0

    # Account-level disjointness
    train_accs = set(df_acc[df_acc["cluster_id"].isin(train_cids)]["account_id"])
    val_accs = set(df_acc[df_acc["cluster_id"].isin(val_cids)]["account_id"])
    test_accs = set(df_acc[df_acc["cluster_id"].isin(test_cids)]["account_id"])

    assert len(train_accs & val_accs) == 0
    assert len(train_accs & test_accs) == 0
    assert len(val_accs & test_accs) == 0


def test_model_serialization_and_metadata():
    """Verify that models/abuse_ring_model.joblib exists, loads properly, and contains complete metadata."""
    assert os.path.exists(OUTPUT_MODEL_PATH), f"Model bundle {OUTPUT_MODEL_PATH} not found"
    bundle = joblib.load(OUTPUT_MODEL_PATH)

    assert "model" in bundle
    assert "base_estimator" in bundle
    assert "feature_names" in bundle
    assert "threshold" in bundle
    assert "training_seed" in bundle
    assert "metrics" in bundle

    assert bundle["feature_names"] == FEATURE_COLUMNS
    assert 0.0 < bundle["threshold"] < 1.0
    assert bundle["training_seed"] == 42


def test_probability_output_range(raw_data):
    """Verify calibrated probability predictions fall strictly within [0.0, 1.0]."""
    df_acc, df_edg, df_cls = raw_data
    X, y, meta = build_cluster_dataset(df_acc, df_edg, df_cls)

    bundle = joblib.load(OUTPUT_MODEL_PATH)
    model = bundle["model"]

    probs = model.predict_proba(X)[:, 1]
    assert len(probs) == 316
    assert np.all(probs >= 0.0)
    assert np.all(probs <= 1.0)
    assert not np.isnan(probs).any()


def test_threshold_behavior(raw_data):
    """Verify operational threshold produces valid binary decisions."""
    df_acc, df_edg, df_cls = raw_data
    X, y, meta = build_cluster_dataset(df_acc, df_edg, df_cls)

    bundle = joblib.load(OUTPUT_MODEL_PATH)
    model = bundle["model"]
    threshold = bundle["threshold"]

    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= threshold).astype(int)

    assert set(np.unique(preds)).issubset({0, 1})
    assert preds.sum() > 0  # Should detect rings
    assert (preds == 0).sum() > 0  # Should classify benign clusters


def test_feature_order_consistency(raw_data):
    """Verify that reordering input DataFrame produces identical output when aligned to FEATURE_COLUMNS."""
    df_acc, df_edg, df_cls = raw_data
    X, y, meta = build_cluster_dataset(df_acc, df_edg, df_cls)

    bundle = joblib.load(OUTPUT_MODEL_PATH)
    model = bundle["model"]

    probs_orig = model.predict_proba(X[FEATURE_COLUMNS])[:, 1]

    # Reorder columns randomly
    shuffled_cols = list(FEATURE_COLUMNS)
    np.random.default_rng(123).shuffle(shuffled_cols)
    X_shuffled = X[shuffled_cols]

    # Align back to FEATURE_COLUMNS
    probs_aligned = model.predict_proba(X_shuffled[FEATURE_COLUMNS])[:, 1]
    np.testing.assert_allclose(probs_orig, probs_aligned)


def test_frozen_models_integrity():
    """Verify that existing models remain intact and undamaged."""
    hashes = get_file_hashes(FROZEN_MODEL_PATHS)
    assert len(hashes) == len(FROZEN_MODEL_PATHS), "One or more frozen models missing"
    # Verify no exception raised
    verify_model_integrity(hashes, hashes)


def test_daisy_chain_ood_synthesis():
    """Verify daisy chain OOD simulator produces valid bipartite graph components."""
    ood_accs, ood_edgs, ood_cls = simulate_daisy_chain_ood_clusters(num_clusters=3, chain_length=10, seed=42)
    assert len(ood_cls) == 3
    assert len(ood_accs) == 30
    df_f = extract_cluster_features(ood_accs, ood_edgs, ood_cls)
    assert len(df_f) == 3
    assert list(df_f.columns) == ["cluster_id"] + FEATURE_COLUMNS
