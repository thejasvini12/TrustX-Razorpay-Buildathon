"""Unit tests and schema validation for Abuse-Ring dataset generator."""

import os
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def ring_datasets():
    """Load the 4 generated Abuse-Ring dataset files."""
    df_accs = pd.read_csv("data/ring_accounts.csv")
    df_edges = pd.read_csv("data/ring_entity_edges.csv")
    df_clusters = pd.read_csv("data/ring_clusters.csv")
    df_feats = pd.read_csv("data/ring_account_network_features.csv")
    return df_accs, df_edges, df_clusters, df_feats


def test_files_exist():
    """Verify all 4 required dataset files exist in data/."""
    assert os.path.exists("data/ring_accounts.csv")
    assert os.path.exists("data/ring_entity_edges.csv")
    assert os.path.exists("data/ring_clusters.csv")
    assert os.path.exists("data/ring_account_network_features.csv")


def test_no_duplicate_primary_keys(ring_datasets):
    """Verify primary key uniqueness across all 4 datasets."""
    df_accs, df_edges, df_clusters, df_feats = ring_datasets

    assert df_accs["account_id"].is_unique, "Duplicate account_id found in ring_accounts.csv"
    assert df_edges["edge_id"].is_unique, "Duplicate edge_id found in ring_entity_edges.csv"
    assert df_clusters["cluster_id"].is_unique, "Duplicate cluster_id found in ring_clusters.csv"
    assert df_feats["account_id"].is_unique, "Duplicate account_id found in ring_account_network_features.csv"


def test_foreign_key_integrity(ring_datasets):
    """Verify all foreign keys resolve completely to parent tables."""
    df_accs, df_edges, df_clusters, df_feats = ring_datasets

    cluster_ids = set(df_clusters["cluster_id"])
    account_ids = set(df_accs["account_id"])

    # 1. Accounts -> Clusters
    for cid in df_accs["cluster_id"]:
        assert cid in cluster_ids, f"Orphan cluster_id '{cid}' in ring_accounts.csv"

    # 2. Edges -> Accounts
    for aid in df_edges["account_id"]:
        assert aid in account_ids, f"Orphan account_id '{aid}' in ring_entity_edges.csv"

    # 3. Features -> Accounts & Clusters
    for aid in df_feats["account_id"]:
        assert aid in account_ids, f"Orphan account_id '{aid}' in ring_account_network_features.csv"
    for cid in df_feats["cluster_id"]:
        assert cid in cluster_ids, f"Orphan cluster_id '{cid}' in ring_account_network_features.csv"


def test_discrete_entity_token_formats(ring_datasets):
    """Verify entity tokens follow discrete prefix masking (DEV_*, IP_*, CARD_*, ADDR_*)."""
    _, df_edges, _, _ = ring_datasets

    valid_prefixes = ("DEV_", "IP_", "CARD_", "ADDR_")
    for entity_id in df_edges["entity_id"]:
        assert entity_id.startswith(valid_prefixes), f"Invalid entity token '{entity_id}'"


def test_no_nans_or_infs_in_datasets(ring_datasets):
    """Verify no NaN or infinite values across all 4 datasets."""
    df_accs, df_edges, df_clusters, df_feats = ring_datasets

    for name, df in [("accounts", df_accs), ("edges", df_edges), ("clusters", df_clusters), ("features", df_feats)]:
        assert not df.isnull().values.any(), f"NaN values detected in {name} dataset"
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert not np.isinf(df[col]).values.any(), f"Inf values detected in {name}.{col}"


def test_timestamp_ordering_and_interaction_counts(ring_datasets):
    """Verify timestamp logic: last_seen_at >= first_seen_at and interaction_count >= 1."""
    _, df_edges, _, _ = ring_datasets

    first_seen = pd.to_datetime(df_edges["first_seen_at"])
    last_seen = pd.to_datetime(df_edges["last_seen_at"])

    assert (last_seen >= first_seen).all(), "Found edges where last_seen_at < first_seen_at"
    assert (df_edges["interaction_count"] >= 1).all(), "Found edges with interaction_count < 1"


def test_valid_rates_and_scores_ranges(ring_datasets):
    """Verify return_rate, refund_rate, suspicious scores, and similarities stay within [0, 1]."""
    df_accs, _, _, df_feats = ring_datasets

    assert df_accs["return_rate"].between(0.0, 1.0).all()
    assert df_accs["refund_rate"].between(0.0, 1.0).all()
    assert df_accs["suspicious_activity_score"].between(0.0, 1.0).all()

    bounded_features = [
        "entity_overlap_score",
        "bipartite_degree_centrality",
        "behavior_similarity_score",
        "temporal_coordination_score",
        "suspicious_behavior_overlap",
        "return_behavior_similarity",
        "transaction_pattern_similarity",
    ]
    for feat in bounded_features:
        assert df_feats[feat].between(0.0, 1.0).all(), f"Feature '{feat}' out of [0, 1] bounds"


def test_bipartite_degree_centrality_properties(ring_datasets):
    """Verify bipartite_degree_centrality is non-constant, 0.0 for singletons, and strictly in [0, 1]."""
    _, _, df_clusters, df_feats = ring_datasets

    s = df_feats["bipartite_degree_centrality"]
    assert not s.nunique() <= 1, "bipartite_degree_centrality must not be constant"
    assert s.min() == 0.0, "Expected min centrality to be 0.0 for singletons"
    assert s.max() <= 1.0, "Expected max centrality to be <= 1.0"

    singleton_clusters = set(df_clusters[df_clusters["cluster_type"] == "SINGLETON_CLEAN"]["cluster_id"])
    singleton_feats = df_feats[df_feats["cluster_id"].isin(singleton_clusters)]
    assert (singleton_feats["bipartite_degree_centrality"] == 0.0).all(), "Singletons must have 0.0 centrality"


def test_cluster_aggregation_consistency(ring_datasets):
    """Verify cluster member counts match actual account distribution."""
    df_accs, _, df_clusters, _ = ring_datasets

    acc_counts_per_cluster = df_accs["cluster_id"].value_counts().to_dict()
    for row in df_clusters.itertuples():
        expected_members = acc_counts_per_cluster.get(row.cluster_id, 0)
        assert row.member_count == expected_members, f"Cluster {row.cluster_id} member_count mismatch"


def test_all_positive_and_negative_scenarios_represented(ring_datasets):
    """Verify positive abuse rings, benign hard negatives, and OOD topologies are generated."""
    _, _, df_clusters, _ = ring_datasets

    types = set(df_clusters["cluster_type"])
    required_archetypes = {
        "SYNTHETIC_IDENTITY_RING",
        "CARD_TESTING_SYNDICATE",
        "PROMO_FARMING_RING",
        "WARDROBING_MULE_CLUSTER",
        "SLOW_DRIP_COORDINATED_RING",
        "CAMPUS_SHARED_IP",
        "COWORKING_PUBLIC_WIFI",
        "FAMILY_HOUSEHOLD",
        "APARTMENT_BUILDING_ADDR",
        "PUBLIC_KIOSK_DEVICE",
        "PARTIAL_NETWORK_OVERLAP",
        "SINGLETON_CLEAN",
    }
    for arch in required_archetypes:
        assert arch in types, f"Archetype '{arch}' missing from generated clusters"

