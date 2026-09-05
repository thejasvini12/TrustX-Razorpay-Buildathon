"""Abuse-Ring Sentinel v1: Graph-Aware Coordinated Fraud Detection Engine.

Integrates the frozen calibrated Random Forest model with a deterministic
evidence layer, safety guardrails, operational scoring, account-level attribution,
and explainability.

Implements:
1. Input validation & diagnostic parsing.
2. Single-source-of-truth 15-feature extraction (src.abuse_ring_features).
3. Frozen calibrated ML inference (raw_ml_probability).
4. Deterministic evidence signals (+0.15 max, -0.30 max).
5. Operational scoring (final_ring_score in [0.0, 1.0]).
6. Contextual safety guardrails.
7. Evidence quality (SUFFICIENT, LIMITED_SAMPLE, INSUFFICIENT_SAMPLE).
8. Confidence evaluation (HIGH, MEDIUM, LOW).
9. Operational verdicts (NO_RING, POSSIBLE_RING, LIKELY_RING, HIGH_CONFIDENCE_RING).
10. Account-level attribution (CORE_MEMBER, PERIPHERAL_MEMBER, INCIDENTAL_BYSTANDER).
11. Gated operational actions (NO_ACTION, MONITOR, REVIEW_CLUSTER, REVIEW_ACCOUNTS, RESTRICT_SELECTED_ACCOUNT, BLOCK_ENTIRE_RING).
12. Grounded natural-language explainability.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
import joblib
import numpy as np
import pandas as pd

# Add project root to sys.path if needed
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.abuse_ring_features import (
    FEATURE_COLUMNS,
    extract_cluster_features,
)

CANONICAL_ENTITY_TYPES: Set[str] = {"DEVICE", "IP", "PAYMENT", "ADDRESS"}
DEFAULT_MODEL_PATH: str = "models/abuse_ring_model.joblib"


class AbuseRingSentinel:
    """Production inference and evidence evaluation engine for Abuse-Ring Sentinel."""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH) -> None:
        """Load frozen model bundle and initialize Sentinel parameters."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Abuse-Ring model bundle not found at {model_path}")

        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.base_estimator = bundle.get("base_estimator")
        self.feature_names: List[str] = bundle.get("feature_names", FEATURE_COLUMNS)
        self.model_threshold: float = float(bundle.get("threshold", 0.50))
        self.model_version: str = bundle.get("version", "1.0.0")
        self.feature_schema_version: str = "15_feature_cluster_v1"

    def detect(
        self,
        accounts: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        cluster_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate candidate connected component subgraph for coordinated abuse rings.
        
        Args:
            accounts: List of account attribute dictionaries.
            edges: List of bipartite interaction edge dictionaries.
            cluster_metadata: Optional summary dictionary.
            
        Returns:
            Dict[str, Any]: Comprehensive detection response conforming to the approved schema.
        """
        cluster_id = "CLUSTER_RUNTIME_00001"
        if cluster_metadata and "cluster_id" in cluster_metadata:
            cluster_id = str(cluster_metadata["cluster_id"])
        elif accounts and "cluster_id" in accounts[0]:
            cluster_id = str(accounts[0]["cluster_id"])

        diagnostics: List[str] = []

        # -------------------------------------------------------------
        # 1. Input Validation & Edge Case Fast-Paths
        # -------------------------------------------------------------
        if not isinstance(accounts, list) or not isinstance(edges, list):
            raise TypeError("Both 'accounts' and 'edges' must be lists of dictionaries.")

        num_accounts = len(accounts)

        # 1A. Empty Cluster Fallback
        if num_accounts == 0:
            return self._build_empty_response(cluster_id, "EMPTY_CLUSTER")

        # 1B. Filter Valid Canonical Edges
        valid_edges: List[Dict[str, Any]] = []
        for e in edges:
            etype = e.get("entity_type")
            if etype in CANONICAL_ENTITY_TYPES:
                valid_edges.append(e)
            else:
                diagnostics.append(f"UNKNOWN_ENTITY_TYPE: {etype} ignored")

        # 1C. Singleton Account Fast-Path
        if num_accounts == 1:
            return self._build_singleton_response(cluster_id, accounts[0], valid_edges, diagnostics)

        # -------------------------------------------------------------
        # 2. Timestamp & Behavioral Completeness Auditing
        # -------------------------------------------------------------
        temporal_data_incomplete = False
        parsed_timestamps: List[pd.Timestamp] = []

        for acc in accounts:
            raw_ts = acc.get("created_at")
            if raw_ts is None:
                temporal_data_incomplete = True
            else:
                try:
                    ts = pd.to_datetime(raw_ts)
                    if pd.isna(ts):
                        temporal_data_incomplete = True
                    else:
                        parsed_timestamps.append(ts)
                except Exception:
                    temporal_data_incomplete = True

        if temporal_data_incomplete or len(parsed_timestamps) < num_accounts:
            temporal_data_incomplete = True
            diagnostics.append("MALFORMED_OR_MISSING_TIMESTAMP: Temporal burst evidence disabled")

        # Check behavioral completeness
        missing_behavioral_count = 0
        for acc in accounts:
            if (
                "average_order_value" not in acc
                or "return_rate" not in acc
                or "suspicious_activity_score" not in acc
                or acc.get("average_order_value") is None
                or acc.get("return_rate") is None
                or acc.get("suspicious_activity_score") is None
            ):
                missing_behavioral_count += 1

        missing_behavioral_ratio = missing_behavioral_count / max(1, num_accounts)
        behavioral_data_incomplete = missing_behavioral_ratio > 0.20
        if behavioral_data_incomplete:
            diagnostics.append(f"MISSING_BEHAVIORAL_FIELDS: {missing_behavioral_ratio:.1%} accounts incomplete")

        # -------------------------------------------------------------
        # 3. Single Source of Truth (SSOT) Feature Extraction
        # -------------------------------------------------------------
        # Prepare DataFrames for extract_cluster_features
        df_accounts = pd.DataFrame(accounts)
        if "cluster_id" not in df_accounts.columns:
            df_accounts["cluster_id"] = cluster_id

        # Clean fallback for feature extraction without inventing false temporal bursts
        if temporal_data_incomplete:
            # When timestamps are invalid/incomplete, use uniform placeholder dates spread out to prevent false burst
            df_accounts["created_at"] = [
                (pd.Timestamp("2026-01-01") + pd.Timedelta(days=k * 10)).isoformat()
                for k in range(len(df_accounts))
            ]

        # Ensure required numerical columns exist in df_accounts for feature calculation
        for col, default_val in [
            ("average_order_value", 0.0),
            ("return_rate", 0.0),
            ("suspicious_activity_score", 0.0),
        ]:
            if col not in df_accounts.columns:
                df_accounts[col] = default_val
            else:
                df_accounts[col] = df_accounts[col].fillna(default_val)

        df_edges = pd.DataFrame(valid_edges) if valid_edges else pd.DataFrame(columns=["edge_id", "account_id", "entity_type", "entity_id"])

        # Cluster metadata DataFrame
        meta_dict: Dict[str, Any] = {
            "cluster_id": cluster_id,
            "member_count": num_accounts,
            "device_count": len({e["entity_id"] for e in valid_edges if e["entity_type"] == "DEVICE"}) if valid_edges else 0,
            "ip_count": len({e["entity_id"] for e in valid_edges if e["entity_type"] == "IP"}) if valid_edges else 0,
            "payment_count": len({e["entity_id"] for e in valid_edges if e["entity_type"] == "PAYMENT"}) if valid_edges else 0,
            "address_count": len({e["entity_id"] for e in valid_edges if e["entity_type"] == "ADDRESS"}) if valid_edges else 0,
        }
        if cluster_metadata:
            meta_dict.update(cluster_metadata)
            meta_dict["cluster_id"] = cluster_id

        df_clusters = pd.DataFrame([meta_dict])

        # Extract 15 cluster features
        df_features = extract_cluster_features(df_accounts, df_edges, df_clusters)

        # Strict Feature Schema Validation
        missing_features = [f for f in self.feature_names if f not in df_features.columns]
        if missing_features:
            raise ValueError(f"Feature extraction schema error. Missing columns: {missing_features}")

        X = df_features[self.feature_names].copy()
        feat_dict = X.iloc[0].to_dict()

        # -------------------------------------------------------------
        # 4. Frozen Model Inference
        # -------------------------------------------------------------
        raw_ml_prob = float(self.model.predict_proba(X)[0, 1])
        model_pred = bool(raw_ml_prob >= self.model_threshold)

        # -------------------------------------------------------------
        # 5. Deterministic Evidence Signals & Adjustments
        # -------------------------------------------------------------
        pos_adjustments: List[Dict[str, Any]] = []
        neg_adjustments: List[Dict[str, Any]] = []
        ring_factors: List[str] = []
        mitigating_factors: List[str] = []

        c_size = feat_dict["cluster_size"]
        overlap_score = feat_dict["entity_overlap_score"]
        velocity_hrs = feat_dict["creation_velocity_window_hours"]
        pay_dev_ratio = feat_dict["payment_to_device_ratio"]
        acc_pay_ratio = feat_dict["account_to_payment_ratio"]
        behav_sim = feat_dict["behavior_similarity_score"]
        temp_coord = feat_dict["temporal_coordination_score"]
        susp_overlap = feat_dict["suspicious_behavior_overlap"]

        # Entity presence across types
        shared_dev = feat_dict["shared_device_account_count"] > 0
        shared_card = feat_dict["shared_payment_account_count"] > 0
        shared_ip = feat_dict["shared_ip_account_count"] > 0
        shared_addr = feat_dict["shared_address_account_count"] > 0
        num_shared_types = sum([shared_dev, shared_card, shared_ip, shared_addr])

        # Positive Corroborating Signals (Max +0.15 total)
        if overlap_score >= 0.40 and num_shared_types >= 2:
            delta = 0.05
            pos_adjustments.append({
                "code": "CORROBORATE_MULTI_MODAL",
                "delta": delta,
                "reason": f"Cross-modal entity overlap (score: {overlap_score:.4f}) across {num_shared_types} entity types.",
            })
            ring_factors.append(f"High multi-entity overlap across hardware and financial tokens (score: {overlap_score:.4f})")

        if not temporal_data_incomplete and velocity_hrs <= 2.0 and c_size >= 4:
            delta = 0.05
            pos_adjustments.append({
                "code": "CORROBORATE_RAPID_BURST",
                "delta": delta,
                "reason": f"Rapid synchronized registration burst across {c_size} accounts within {velocity_hrs:.2f} hours.",
            })
            ring_factors.append(f"Rapid account creation burst within {velocity_hrs:.2f} hours")

        if pay_dev_ratio >= 3.0 and c_size >= 5:
            delta = 0.05
            pos_adjustments.append({
                "code": "CORROBORATE_CARD_CHURN",
                "delta": delta,
                "reason": f"High payment-to-device ratio ({pay_dev_ratio:.2f}) indicates card testing or virtual card churning.",
            })
            ring_factors.append(f"Elevated payment-to-device ratio ({pay_dev_ratio:.2f})")

        if behav_sim >= 0.80 and not behavioral_data_incomplete and c_size >= 3:
            ring_factors.append(f"High behavioral synchronization across order values and return patterns (score: {behav_sim:.4f})")

        if susp_overlap >= 0.65 and not behavioral_data_incomplete:
            ring_factors.append(f"High individual suspicious activity overlap across cluster members (mean: {susp_overlap:.4f})")

        # Mitigating Signals (Max -0.30 total)
        if shared_ip and not shared_card and not shared_dev and not shared_addr and behav_sim < 0.50:
            delta = -0.15
            neg_adjustments.append({
                "code": "MITIGATE_SINGLE_IP_BENIGN",
                "delta": delta,
                "reason": "Single-IP sharing with distinct payment instruments, devices, and natural behavioral diversity.",
            })
            mitigating_factors.append("Shared IP only with independent devices, payment methods, and diverse behaviors (benign network)")

        if shared_addr and not shared_card and not shared_dev and not shared_ip and behav_sim < 0.50:
            delta = -0.10
            neg_adjustments.append({
                "code": "MITIGATE_SINGLE_ADDR_BENIGN",
                "delta": delta,
                "reason": "Single-address sharing with distinct hardware and cards (multi-unit apartment residence).",
            })
            mitigating_factors.append("Shared physical address only with independent devices and cards (multi-unit delivery)")

        if not temporal_data_incomplete and velocity_hrs > 720.0 and temp_coord < 0.25:
            delta = -0.05
            neg_adjustments.append({
                "code": "MITIGATE_TEMPORAL_DISPERSION",
                "delta": delta,
                "reason": f"Staggered, organic account registration over {velocity_hrs / 24.0:.1f} days.",
            })
            mitigating_factors.append(f"Organic account onboarding spread over {velocity_hrs / 24.0:.1f} days")

        if behav_sim < 0.35 and not behavioral_data_incomplete:
            delta = -0.05
            neg_adjustments.append({
                "code": "MITIGATE_HIGH_BEHAVIOR_ENTROPY",
                "delta": delta,
                "reason": "High variance in shopping basket values and return behaviors inconsistent with scripted bot syndicates.",
            })
            mitigating_factors.append("Natural behavioral variance across member order values and return patterns")

        # -------------------------------------------------------------
        # 6. Operational Score Calculation
        # -------------------------------------------------------------
        tot_pos_delta = round(min(0.15, sum(p["delta"] for p in pos_adjustments)), 4)
        tot_neg_delta = round(max(-0.30, sum(m["delta"] for m in neg_adjustments)), 4)
        net_delta = round(tot_pos_delta + tot_neg_delta, 4)
        final_ring_score = float(np.clip(round(raw_ml_prob + tot_pos_delta + tot_neg_delta, 4), 0.0, 1.0))

        # -------------------------------------------------------------
        # 7. Evidence Quality & Confidence Evaluation
        # -------------------------------------------------------------
        entity_types_present = {e["entity_type"] for e in valid_edges}

        if len(valid_edges) == 0 or missing_behavioral_ratio >= 0.50:
            evidence_quality = "INSUFFICIENT_SAMPLE"
        elif num_accounts in [2, 3] or len(entity_types_present) == 1 or behavioral_data_incomplete or temporal_data_incomplete:
            evidence_quality = "LIMITED_SAMPLE"
        elif num_accounts >= 2 and len(entity_types_present) >= 2 and missing_behavioral_ratio <= 0.20 and not temporal_data_incomplete:
            evidence_quality = "SUFFICIENT"
        else:
            evidence_quality = "LIMITED_SAMPLE"

        if evidence_quality == "INSUFFICIENT_SAMPLE":
            confidence = "LOW"
        elif evidence_quality == "SUFFICIENT" and len(valid_edges) >= (2 * num_accounts) and not temporal_data_incomplete:
            confidence = "HIGH"
        else:
            confidence = "MEDIUM"

        # -------------------------------------------------------------
        # 8. Operational Verdict & Risk Level
        # -------------------------------------------------------------
        if final_ring_score < 0.30:
            verdict = "NO_RING"
            risk_level = "LOW"
        elif final_ring_score < 0.50:
            verdict = "POSSIBLE_RING"
            risk_level = "MEDIUM"
        elif final_ring_score < 0.75:
            verdict = "LIKELY_RING"
            risk_level = "HIGH"
        else:  # >= 0.75
            if confidence == "HIGH":
                verdict = "HIGH_CONFIDENCE_RING"
                risk_level = "CRITICAL"
            else:
                verdict = "LIKELY_RING"
                risk_level = "HIGH"

        ring_detected = bool(verdict in ["LIKELY_RING", "HIGH_CONFIDENCE_RING"])

        # -------------------------------------------------------------
        # 9. Account-Level Attribution
        # -------------------------------------------------------------
        account_attribution = self._compute_account_attribution(
            accounts=accounts,
            valid_edges=valid_edges,
            verdict=verdict,
        )

        bystander_count = sum(1 for a in account_attribution if a["attribution_role"] == "INCIDENTAL_BYSTANDER")
        has_multi_modal = (overlap_score >= 0.35 and len(entity_types_present) >= 2)

        # -------------------------------------------------------------
        # 10. Operational Action Recommendation
        # -------------------------------------------------------------
        if verdict == "NO_RING":
            recommended_action = "NO_ACTION"
        elif verdict == "POSSIBLE_RING":
            recommended_action = "MONITOR"
        elif verdict == "LIKELY_RING":
            if bystander_count > 0:
                recommended_action = "REVIEW_ACCOUNTS"
            else:
                recommended_action = "REVIEW_CLUSTER"
        elif verdict == "HIGH_CONFIDENCE_RING":
            # Gated BLOCK_ENTIRE_RING requires all 4 gates
            if confidence == "HIGH" and bystander_count == 0 and has_multi_modal:
                recommended_action = "BLOCK_ENTIRE_RING"
            elif bystander_count > 0:
                recommended_action = "REVIEW_ACCOUNTS"
            else:
                recommended_action = "RESTRICT_SELECTED_ACCOUNT"
        else:
            recommended_action = "MONITOR"

        # -------------------------------------------------------------
        # 11. Explainability Synthesis
        # -------------------------------------------------------------
        evidence_summary = self._synthesize_evidence_summary(
            c_size=num_accounts,
            edges=valid_edges,
            velocity_hrs=velocity_hrs,
            temporal_incomplete=temporal_data_incomplete,
        )

        decision_reasoning = self._synthesize_decision_reasoning(
            raw_prob=raw_ml_prob,
            final_score=final_ring_score,
            verdict=verdict,
            confidence=confidence,
            recommended_action=recommended_action,
            bystander_count=bystander_count,
        )

        return {
            "cluster_id": cluster_id,
            "ring_detected": ring_detected,
            "raw_ml_probability": round(raw_ml_prob, 4),
            "model_prediction": model_pred,
            "model_threshold": self.model_threshold,
            "evidence_adjustments": {
                "positive_adjustments": pos_adjustments,
                "mitigating_adjustments": neg_adjustments,
                "total_positive_delta": tot_pos_delta,
                "total_negative_delta": tot_neg_delta,
                "net_delta": net_delta,
            },
            "final_ring_score": final_ring_score,
            "risk_level": risk_level,
            "verdict": verdict,
            "evidence_quality": evidence_quality,
            "confidence": confidence,
            "cluster_size": num_accounts,
            "ring_factors": ring_factors,
            "mitigating_factors": mitigating_factors,
            "evidence_summary": evidence_summary,
            "decision_reasoning": decision_reasoning,
            "account_attribution": account_attribution,
            "recommended_action": recommended_action,
            "model_metadata": {
                "model_version": self.model_version,
                "feature_schema_version": self.feature_schema_version,
                "calibrated": True,
            },
            "diagnostics": diagnostics,
        }

    def _compute_account_attribution(
        self,
        accounts: List[Dict[str, Any]],
        valid_edges: List[Dict[str, Any]],
        verdict: str,
    ) -> List[Dict[str, Any]]:
        """Compute deterministic account-level roles without conflating cluster prediction with account label."""
        n_accounts = len(accounts)
        if n_accounts == 0:
            return []

        entity_to_accs: Dict[str, Set[str]] = {}
        acc_to_entities: Dict[str, Dict[str, Set[str]]] = {}

        for e in valid_edges:
            aid = e["account_id"]
            eid = e["entity_id"]
            etype = e["entity_type"]

            entity_to_accs.setdefault(eid, set()).add(aid)
            if aid not in acc_to_entities:
                acc_to_entities[aid] = {"DEVICE": set(), "IP": set(), "PAYMENT": set(), "ADDRESS": set()}
            if etype in acc_to_entities[aid]:
                acc_to_entities[aid][etype].add(eid)

        all_acc_ids = {a.get("account_id") for a in accounts if "account_id" in a}
        attributions: List[Dict[str, Any]] = []

        for acc in accounts:
            aid = acc.get("account_id", "UNKNOWN")
            a_entities = acc_to_entities.get(aid, {"DEVICE": set(), "IP": set(), "PAYMENT": set(), "ADDRESS": set()})

            # Calculate connected neighbors in cluster
            projected_neighbors: Set[str] = set()
            shared_types_present: Set[str] = set()

            for etype in ["DEVICE", "IP", "PAYMENT", "ADDRESS"]:
                for token in a_entities[etype]:
                    token_accs = entity_to_accs.get(token, set())
                    if len(token_accs) > 1:
                        shared_types_present.add(etype)
                    projected_neighbors.update(token_accs)

            projected_neighbors.discard(aid)
            in_cluster_neighbors = projected_neighbors.intersection(all_acc_ids)
            bipartite_degree = round(len(in_cluster_neighbors) / max(1.0, float(n_accounts - 1)), 4) if n_accounts > 1 else 0.0

            susp_score = float(acc.get("suspicious_activity_score", 0.0) or 0.0)
            has_shared_card = "PAYMENT" in shared_types_present
            has_shared_dev = "DEVICE" in shared_types_present
            has_shared_ip = "IP" in shared_types_present
            has_shared_addr = "ADDRESS" in shared_types_present

            # Deterministic Role Assignment
            if verdict in ["LIKELY_RING", "HIGH_CONFIDENCE_RING"]:
                if not has_shared_card and not has_shared_dev and susp_score < 0.20:
                    role = "INCIDENTAL_BYSTANDER"
                    risk_contrib = "LOW"
                    reason = "Coincidental connectivity via shared infrastructure (IP/Address) with independent payment and low suspicion."
                elif (
                    bipartite_degree >= 0.50
                    or (has_shared_card and has_shared_dev)
                    or ((has_shared_card or has_shared_dev) and susp_score >= 0.60)
                ):
                    role = "CORE_MEMBER"
                    risk_contrib = "HIGH"
                    reason = f"Central coordinator node (degree: {bipartite_degree:.2f}) with shared hardware/financial instruments."
                else:
                    role = "PERIPHERAL_MEMBER"
                    risk_contrib = "MEDIUM"
                    reason = f"Peripheral node connected to ring via {', '.join(shared_types_present) or 'link'}."
            else:
                # Benign or Possible Ring
                if has_shared_card or has_shared_dev:
                    role = "PERIPHERAL_MEMBER"
                    risk_contrib = "LOW"
                    reason = "Shares token within benign cluster."
                else:
                    role = "INCIDENTAL_BYSTANDER"
                    risk_contrib = "LOW"
                    reason = "Independent account on shared common-carrier network."

            attributions.append({
                "account_id": aid,
                "attribution_role": role,
                "linked_ring_accounts_count": len(in_cluster_neighbors),
                "shared_entity_types": sorted(list(shared_types_present)),
                "bipartite_degree": bipartite_degree,
                "suspicious_activity_score": round(susp_score, 4),
                "risk_contribution": risk_contrib,
                "attribution_reasoning": reason,
            })

        return attributions

    def _build_empty_response(self, cluster_id: str, diag: str) -> Dict[str, Any]:
        """Construct fallback response for empty cluster."""
        return {
            "cluster_id": cluster_id,
            "ring_detected": False,
            "raw_ml_probability": 0.0,
            "model_prediction": False,
            "model_threshold": self.model_threshold,
            "evidence_adjustments": {
                "positive_adjustments": [],
                "mitigating_adjustments": [],
                "total_positive_delta": 0.0,
                "total_negative_delta": 0.0,
                "net_delta": 0.0,
            },
            "final_ring_score": 0.0,
            "risk_level": "LOW",
            "verdict": "NO_RING",
            "evidence_quality": "INSUFFICIENT_SAMPLE",
            "confidence": "LOW",
            "cluster_size": 0,
            "ring_factors": [],
            "mitigating_factors": ["No accounts in candidate cluster."],
            "evidence_summary": "Empty candidate cluster with 0 accounts.",
            "decision_reasoning": "Zero accounts provided. Defaulted to NO_RING.",
            "account_attribution": [],
            "recommended_action": "NO_ACTION",
            "model_metadata": {
                "model_version": self.model_version,
                "feature_schema_version": self.feature_schema_version,
                "calibrated": True,
            },
            "diagnostics": [diag],
        }

    def _build_singleton_response(
        self,
        cluster_id: str,
        account: Dict[str, Any],
        edges: List[Dict[str, Any]],
        diagnostics: List[str],
    ) -> Dict[str, Any]:
        """Construct fast-path response for singleton account."""
        aid = account.get("account_id", "ACC_SOLO_000001")
        susp_score = float(account.get("suspicious_activity_score", 0.0) or 0.0)

        return {
            "cluster_id": cluster_id,
            "ring_detected": False,
            "raw_ml_probability": 0.0,
            "model_prediction": False,
            "model_threshold": self.model_threshold,
            "evidence_adjustments": {
                "positive_adjustments": [],
                "mitigating_adjustments": [],
                "total_positive_delta": 0.0,
                "total_negative_delta": 0.0,
                "net_delta": 0.0,
            },
            "final_ring_score": 0.0,
            "risk_level": "LOW",
            "verdict": "NO_RING",
            "evidence_quality": "INSUFFICIENT_SAMPLE",
            "confidence": "LOW",
            "cluster_size": 1,
            "ring_factors": [],
            "mitigating_factors": ["Singleton account cannot form a coordinated abuse ring."],
            "evidence_summary": f"Candidate cluster contains only 1 account ({aid}) with {len(edges)} entity edges.",
            "decision_reasoning": "Singleton account evaluated. Single accounts cannot constitute a multi-account abuse ring.",
            "account_attribution": [
                {
                    "account_id": aid,
                    "attribution_role": "INCIDENTAL_BYSTANDER",
                    "linked_ring_accounts_count": 0,
                    "shared_entity_types": [],
                    "bipartite_degree": 0.0,
                    "suspicious_activity_score": round(susp_score, 4),
                    "risk_contribution": "LOW",
                    "attribution_reasoning": "Isolated singleton account.",
                }
            ],
            "recommended_action": "NO_ACTION",
            "model_metadata": {
                "model_version": self.model_version,
                "feature_schema_version": self.feature_schema_version,
                "calibrated": True,
            },
            "diagnostics": diagnostics + ["SINGLETON_FAST_PATH"],
        }

    def _synthesize_evidence_summary(
        self,
        c_size: int,
        edges: List[Dict[str, Any]],
        velocity_hrs: float,
        temporal_incomplete: bool,
    ) -> str:
        """Synthesize natural-language summary of graph connectivity."""
        dev_cnt = len({e["entity_id"] for e in edges if e["entity_type"] == "DEVICE"})
        card_cnt = len({e["entity_id"] for e in edges if e["entity_type"] == "PAYMENT"})
        ip_cnt = len({e["entity_id"] for e in edges if e["entity_type"] == "IP"})
        addr_cnt = len({e["entity_id"] for e in edges if e["entity_type"] == "ADDRESS"})

        entity_summary_parts = []
        if dev_cnt > 0:
            entity_summary_parts.append(f"{dev_cnt} device(s)")
        if card_cnt > 0:
            entity_summary_parts.append(f"{card_cnt} card(s)")
        if ip_cnt > 0:
            entity_summary_parts.append(f"{ip_cnt} IP(s)")
        if addr_cnt > 0:
            entity_summary_parts.append(f"{addr_cnt} address(es)")

        joined_entities = ", ".join(entity_summary_parts) if entity_summary_parts else "0 entity tokens"

        if temporal_incomplete:
            time_str = "with unverified/incomplete timestamps"
        elif velocity_hrs <= 24.0:
            time_str = f"registered within a {velocity_hrs:.1f}-hour window"
        else:
            time_str = f"registered over {velocity_hrs / 24.0:.1f} days"

        return f"{c_size} accounts connected across {joined_entities}, {time_str}."

    def _synthesize_decision_reasoning(
        self,
        raw_prob: float,
        final_score: float,
        verdict: str,
        confidence: str,
        recommended_action: str,
        bystander_count: int,
    ) -> str:
        """Synthesize decision justification without claiming ungrounded causality."""
        if verdict == "HIGH_CONFIDENCE_RING":
            bystander_str = "Zero incidental bystanders detected." if bystander_count == 0 else f"{bystander_count} bystander(s) present."
            return (
                f"Calibrated ML probability ({raw_prob:.4f}) and operational risk score ({final_score:.4f}) exceed the critical threshold (0.7500) "
                f"with {confidence} confidence. {bystander_str} Action: {recommended_action}."
            )
        elif verdict == "LIKELY_RING":
            return (
                f"Calibrated ML probability ({raw_prob:.4f}) and operational score ({final_score:.4f}) exceed the operational model threshold (0.5000) "
                f"with {confidence} confidence. Recommended action: {recommended_action}."
            )
        elif verdict == "POSSIBLE_RING":
            return (
                f"Operational score ({final_score:.4f}) falls in the warning threshold tier [0.3000, 0.5000). "
                f"Telemetry logged for passive monitoring without consumer friction."
            )
        else:
            return (
                f"Operational score ({final_score:.4f}) is below the suspicion threshold (0.3000). "
                f"Graph patterns and mitigating adjustments indicate benign shared infrastructure."
            )


_sentinel: Optional[AbuseRingSentinel] = None


def get_abuse_ring_sentinel() -> AbuseRingSentinel:
    """Retrieve or initialize singleton AbuseRingSentinel instance."""
    global _sentinel
    if _sentinel is None:
        _sentinel = AbuseRingSentinel()
    return _sentinel

