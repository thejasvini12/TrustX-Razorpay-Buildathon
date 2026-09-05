"""Abuse-Ring Sentinel Feature Extraction Module.

Single Source of Truth (SSOT) for extracting cluster-level graph topological,
relational overlap, and behavioral coordination features.

Standard Feature Schema (15 ML features):
1. cluster_size
2. shared_device_account_count
3. shared_ip_account_count
4. shared_payment_account_count
5. shared_address_account_count
6. entity_overlap_score
7. bipartite_degree_centrality
8. creation_velocity_window_hours
9. payment_to_device_ratio
10. account_to_payment_ratio
11. behavior_similarity_score
12. temporal_coordination_score
13. suspicious_behavior_overlap
14. return_behavior_similarity
15. transaction_pattern_similarity
"""

from typing import Dict, List, Set, Tuple, Any
import numpy as np
import pandas as pd

FEATURE_COLUMNS: List[str] = [
    "cluster_size",
    "shared_device_account_count",
    "shared_ip_account_count",
    "shared_payment_account_count",
    "shared_address_account_count",
    "entity_overlap_score",
    "bipartite_degree_centrality",
    "creation_velocity_window_hours",
    "payment_to_device_ratio",
    "account_to_payment_ratio",
    "behavior_similarity_score",
    "temporal_coordination_score",
    "suspicious_behavior_overlap",
    "return_behavior_similarity",
    "transaction_pattern_similarity",
]

TARGET_COLUMN: str = "cluster_abuse_label"
EVALUATION_METADATA_COLUMNS: List[str] = [
    "cluster_id",
    "cluster_type",
    "member_count",
]


def extract_cluster_features(
    df_accounts: pd.DataFrame,
    df_edges: pd.DataFrame,
    df_clusters: pd.DataFrame,
) -> pd.DataFrame:
    """Extract exactly one 15-dimensional feature vector per cluster.
    
    Implements deterministic aggregation from account-level bipartite graph
    neighborhoods and cluster-level behavioral and temporal coordination.
    
    Guaranteed Zero-Leakage: Never uses cluster_abuse_label, is_ring_member_label,
    or cluster_type in the computed feature matrix.
    
    Args:
        df_accounts: DataFrame containing account records with cluster_id.
        df_edges: DataFrame containing bipartite graph interaction edges.
        df_clusters: DataFrame containing cluster summaries.
        
    Returns:
        pd.DataFrame: One row per cluster with columns ['cluster_id'] + FEATURE_COLUMNS.
    """
    eps = 1e-4

    # Map cluster metadata
    cluster_meta: Dict[str, Dict[str, Any]] = df_clusters.set_index("cluster_id").to_dict(orient="index")

    # Map entity occurrences to account IDs for shared entity calculation
    entity_to_accs: Dict[str, Set[str]] = df_edges.groupby("entity_id")["account_id"].apply(set).to_dict()

    # Map account to its entities by type
    acc_to_entities: Dict[str, Dict[str, Set[str]]] = {}
    for row in df_edges.itertuples():
        if row.account_id not in acc_to_entities:
            acc_to_entities[row.account_id] = {
                "DEVICE": set(),
                "IP": set(),
                "PAYMENT": set(),
                "ADDRESS": set(),
            }
        etype = getattr(row, "entity_type", None)
        if etype in acc_to_entities[row.account_id]:
            acc_to_entities[row.account_id][etype].add(row.entity_id)

    # Group accounts by cluster
    cluster_acc_groups = df_accounts.groupby("cluster_id")
    cluster_acc_sets: Dict[str, Set[str]] = df_accounts.groupby("cluster_id")["account_id"].apply(set).to_dict()

    cluster_rows: List[Dict[str, Any]] = []

    for cid, cmeta in cluster_meta.items():
        if cid not in cluster_acc_groups.groups:
            continue

        group = cluster_acc_groups.get_group(cid)
        c_size = int(cmeta.get("member_count", len(group)))
        c_members = cluster_acc_sets.get(cid, set())

        # 1. Temporal Window & Coordination Score
        created_dt = pd.to_datetime(group["created_at"])
        time_span_hours = float((created_dt.max() - created_dt.min()).total_seconds() / 3600.0)
        std_hours = float(np.std([(t - created_dt.min()).total_seconds() / 3600.0 for t in created_dt])) if len(group) > 1 else 100.0
        temporal_coord = float(np.round(1.0 / (1.0 + (std_hours / 12.0)), 4))

        # 2. Behavioral Similarity Scores
        aov_mean = float(group["average_order_value"].mean())
        aov_std = float(group["average_order_value"].std()) if len(group) > 1 else 0.0
        tx_pattern_sim = float(np.round(max(0.0, 1.0 - (aov_std / (aov_mean + eps))), 4))

        ret_std = float(group["return_rate"].std()) if len(group) > 1 else 0.0
        ret_sim = float(np.round(max(0.0, 1.0 - (ret_std * 2.5)), 4))

        susp_mean = float(group["suspicious_activity_score"].mean())
        behavior_sim = float(np.round((tx_pattern_sim * 0.5) + (ret_sim * 0.5), 4))

        # 3. Graph Density & Structural Token Ratios
        pay_cnt = float(cmeta.get("payment_count", len(group)))
        dev_cnt = float(cmeta.get("device_count", 1.0))
        pay_to_dev_ratio = float(np.round(pay_cnt / max(1.0, dev_cnt), 4))
        acc_to_pay_ratio = float(np.round(float(c_size) / max(1.0, pay_cnt), 4))

        # 4. Account-Level Shared Entity Neighborhoods & Deterministic Aggregations (Mean)
        dev_counts: List[float] = []
        ip_counts: List[float] = []
        pay_counts: List[float] = []
        addr_counts: List[float] = []
        overlap_scores: List[float] = []
        degrees: List[float] = []

        for acc_row in group.itertuples():
            a_entities = acc_to_entities.get(
                acc_row.account_id,
                {"DEVICE": set(), "IP": set(), "PAYMENT": set(), "ADDRESS": set()},
            )

            shared_dev_accs: Set[str] = set()
            for dev in a_entities["DEVICE"]:
                shared_dev_accs.update(entity_to_accs.get(dev, set()))
            s_dev = max(0, len(shared_dev_accs) - 1)

            shared_ip_accs: Set[str] = set()
            for ip in a_entities["IP"]:
                shared_ip_accs.update(entity_to_accs.get(ip, set()))
            s_ip = max(0, len(shared_ip_accs) - 1)

            shared_card_accs: Set[str] = set()
            for card in a_entities["PAYMENT"]:
                shared_card_accs.update(entity_to_accs.get(card, set()))
            s_pay = max(0, len(shared_card_accs) - 1)

            shared_addr_accs: Set[str] = set()
            for addr in a_entities["ADDRESS"]:
                shared_addr_accs.update(entity_to_accs.get(addr, set()))
            s_addr = max(0, len(shared_addr_accs) - 1)

            # Weighted Entity Overlap Score (Cards > Devices > Addresses > IPs)
            weighted_overlap = (
                (s_pay * 0.40) +
                (s_dev * 0.30) +
                (s_addr * 0.20) +
                (s_ip * 0.10)
            ) / max(1.0, float(c_size - 1) if c_size > 1 else 1.0)
            ov_score = float(np.round(np.clip(weighted_overlap, 0.0, 1.0), 4))

            # Projected 1-mode bipartite degree centrality
            projected_neighbors: Set[str] = set()
            for etype in ["DEVICE", "IP", "PAYMENT", "ADDRESS"]:
                for token in a_entities[etype]:
                    projected_neighbors.update(entity_to_accs.get(token, set()))
            projected_neighbors.discard(acc_row.account_id)
            projected_in_cluster = projected_neighbors.intersection(c_members)
            bipartite_degree = float(np.round(len(projected_in_cluster) / max(1.0, float(c_size - 1)), 4)) if c_size > 1 else 0.0

            dev_counts.append(float(s_dev))
            ip_counts.append(float(s_ip))
            pay_counts.append(float(s_pay))
            addr_counts.append(float(s_addr))
            overlap_scores.append(ov_score)
            degrees.append(bipartite_degree)

        cluster_rows.append({
            "cluster_id": cid,
            "cluster_size": c_size,
            "shared_device_account_count": float(np.round(np.mean(dev_counts), 4)),
            "shared_ip_account_count": float(np.round(np.mean(ip_counts), 4)),
            "shared_payment_account_count": float(np.round(np.mean(pay_counts), 4)),
            "shared_address_account_count": float(np.round(np.mean(addr_counts), 4)),
            "entity_overlap_score": float(np.round(np.mean(overlap_scores), 4)),
            "bipartite_degree_centrality": float(np.round(np.mean(degrees), 4)),
            "creation_velocity_window_hours": round(time_span_hours, 2),
            "payment_to_device_ratio": pay_to_dev_ratio,
            "account_to_payment_ratio": acc_to_pay_ratio,
            "behavior_similarity_score": behavior_sim,
            "temporal_coordination_score": temporal_coord,
            "suspicious_behavior_overlap": round(susp_mean, 4),
            "return_behavior_similarity": ret_sim,
            "transaction_pattern_similarity": tx_pattern_sim,
        })

    df_result = pd.DataFrame(cluster_rows)
    return df_result


def build_cluster_dataset(
    df_accounts: pd.DataFrame,
    df_edges: pd.DataFrame,
    df_clusters: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Build the clean ML feature matrix X, ground-truth label y, and evaluation metadata.
    
    Performs rigorous leakage audit on X to verify that target labels,
    archetype categories, and identifiers are strictly excluded from X.
    
    Returns:
        Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
            - X: DataFrame of shape (num_clusters, 15) containing only FEATURE_COLUMNS.
            - y: Series of shape (num_clusters,) containing binary cluster_abuse_label.
            - metadata: DataFrame containing ['cluster_id', 'cluster_type', 'member_count'].
    """
    df_features = extract_cluster_features(df_accounts, df_edges, df_clusters)

    # Merge metadata and target label from df_clusters
    cluster_targets = df_clusters.set_index("cluster_id")

    df_full = df_features.set_index("cluster_id").join(
        cluster_targets[[TARGET_COLUMN, "cluster_type"]],
        how="inner",
    ).reset_index()

    # Extract X (strictly 15 features in exact order)
    X = df_full[FEATURE_COLUMNS].copy()

    # Extract y (ground truth target)
    y = df_full[TARGET_COLUMN].copy()

    # Extract metadata
    metadata = df_full[["cluster_id", "cluster_type", "cluster_size"]].rename(
        columns={"cluster_size": "member_count"}
    ).copy()

    # Programmatic Leakage Audit
    forbidden_features = {
        TARGET_COLUMN,
        "is_ring_member_label",
        "cluster_type",
        "cluster_id",
        "account_id",
        "edge_id",
        "entity_id",
    }
    present_forbidden = forbidden_features.intersection(set(X.columns))
    if present_forbidden:
        raise ValueError(f"Leakage Audit FAILED: Forbidden columns found in feature matrix X: {present_forbidden}")

    if list(X.columns) != FEATURE_COLUMNS:
        raise ValueError(f"Feature Schema FAILED: Columns do not match exact 15 feature specification: {list(X.columns)}")

    if X.isna().sum().sum() > 0 or np.isinf(X.values).sum() > 0:
        raise ValueError("Feature Matrix contains NaN or Inf values.")

    return X, y, metadata
