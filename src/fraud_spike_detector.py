import os
import json
import math
import time
import threading
from datetime import datetime, timezone
from collections import OrderedDict
from typing import Dict, Any, List, Tuple, Optional
import joblib
import numpy as np
import pandas as pd

from src.temporal_data_generator import SPIKE_FEATURE_COLUMNS

# Centralized Evidence Volume Thresholds
MIN_BASELINE_TX_FOR_STRONG_EVIDENCE: float = 120.0  # >= 5 tx/hr over 24h baseline
MIN_CURRENT_TX_FOR_STRONG_EVIDENCE: float = 15.0    # >= 15 tx in latest 1h observation
MIN_BASELINE_TX_FOR_LIMITED_EVIDENCE: float = 24.0   # >= 1 tx/hr over 24h baseline
MIN_CURRENT_TX_FOR_LIMITED_EVIDENCE: float = 5.0     # >= 5 tx in latest 1h observation


class MerchantIncidentTracker:
    """Thread-safe, bounded in-memory tracker for rolling merchant anomaly incidents."""

    def __init__(self, max_merchants: int = 10000, escalation_threshold: int = 3):
        self._max_merchants = max_merchants
        self._escalation_threshold = escalation_threshold
        self._lock = threading.Lock()
        self._state: OrderedDict[str, int] = OrderedDict()

    def record_evaluation(self, merchant_id: str, operational_tier: str) -> Tuple[int, bool]:
        """Record an operational evaluation tier for a merchant.

        Returns:
            Tuple[int, bool]: (consecutive_anomaly_windows, persistence_escalation_triggered)
        """
        # Anonymous/unknown merchants are evaluated statelessly to prevent cross-merchant contamination
        if not merchant_id or merchant_id == "MERCH_UNKNOWN":
            return 0, False

        with self._lock:
            current_count = self._state.get(merchant_id, 0)
            if operational_tier in ("MEDIUM", "HIGH"):
                new_count = current_count + 1
                self._state[merchant_id] = new_count
                self._state.move_to_end(merchant_id)

                # Evict oldest entry if capacity exceeded
                if len(self._state) > self._max_merchants:
                    self._state.popitem(last=False)

                escalate = (new_count >= self._escalation_threshold) and (operational_tier == "MEDIUM")
                return new_count, escalate
            else:  # LOW
                if merchant_id in self._state:
                    del self._state[merchant_id]
                return 0, False

    def get_count(self, merchant_id: str) -> int:
        """Retrieve current consecutive anomaly count for a merchant."""
        if not merchant_id or merchant_id == "MERCH_UNKNOWN":
            return 0
        with self._lock:
            return self._state.get(merchant_id, 0)

    def reset(self, merchant_id: Optional[str] = None) -> None:
        """Reset tracking state for a specific merchant or all merchants."""
        with self._lock:
            if merchant_id is not None:
                self._state.pop(merchant_id, None)
            else:
                self._state.clear()


class FiveMinuteTelemetryStore:
    """Thread-safe, bounded in-memory store for merchant 5-minute sub-window telemetry."""

    def __init__(self, max_merchants: int = 10000, max_windows_per_merchant: int = 12):
        self._max_merchants = max_merchants
        self._max_windows = max_windows_per_merchant
        self._lock = threading.Lock()
        self._state: OrderedDict[str, List[Dict[str, Any]]] = OrderedDict()

    def record_observation(self, merchant_id: str, observation: Dict[str, Any]) -> None:
        """Record a single 5-minute telemetry observation for a merchant."""
        if not merchant_id or merchant_id == "MERCH_UNKNOWN" or not isinstance(observation, dict):
            return

        with self._lock:
            history = self._state.get(merchant_id, [])
            history.append(dict(observation))
            if len(history) > self._max_windows:
                history = history[-self._max_windows:]
            self._state[merchant_id] = history
            self._state.move_to_end(merchant_id)

            if len(self._state) > self._max_merchants:
                self._state.popitem(last=False)

    def record_observations(self, merchant_id: str, observations: List[Dict[str, Any]]) -> None:
        """Record multiple 5-minute telemetry observations for a merchant."""
        if not merchant_id or merchant_id == "MERCH_UNKNOWN" or not observations:
            return

        with self._lock:
            history = self._state.get(merchant_id, [])
            for obs in observations:
                if isinstance(obs, dict):
                    history.append(dict(obs))
                elif hasattr(obs, "model_dump"):
                    history.append(obs.model_dump())
            if len(history) > self._max_windows:
                history = history[-self._max_windows:]
            self._state[merchant_id] = history
            self._state.move_to_end(merchant_id)

            if len(self._state) > self._max_merchants:
                self._state.popitem(last=False)

    def get_observations(self, merchant_id: str) -> List[Dict[str, Any]]:
        """Retrieve recent 5-minute observations for a merchant."""
        if not merchant_id or merchant_id == "MERCH_UNKNOWN":
            return []
        with self._lock:
            return list(self._state.get(merchant_id, []))

    def record_payment_event(
        self,
        merchant_id: str,
        timestamp: Optional[float] = None,
        is_fraud: bool = False,
        window_seconds: int = 300,
    ) -> Dict[str, Any]:
        """Record an incoming individual payment event and aggregate into 5-minute observation windows."""
        if not merchant_id or merchant_id == "MERCH_UNKNOWN":
            return {}

        now_ts = float(timestamp if timestamp is not None else time.time())
        window_start = int(now_ts // window_seconds) * window_seconds

        with self._lock:
            history = self._state.get(merchant_id, [])
            if history and history[-1].get("window_start") == window_start:
                curr = history[-1]
                curr["tx_count"] = int(curr.get("tx_count", 0)) + 1
                if is_fraud:
                    curr["fraud_count"] = int(curr.get("fraud_count", 0)) + 1
                tx = curr["tx_count"]
                fc = curr.get("fraud_count", 0)
                curr["fraud_rate"] = round(float(fc / tx), 4) if tx > 0 else 0.0
                curr["timestamp"] = datetime.fromtimestamp(now_ts, timezone.utc).isoformat()
                active_obs = dict(curr)
            else:
                new_obs = {
                    "timestamp": datetime.fromtimestamp(now_ts, timezone.utc).isoformat(),
                    "window_start": window_start,
                    "tx_count": 1,
                    "fraud_count": 1 if is_fraud else 0,
                    "fraud_rate": 1.0 if is_fraud else 0.0,
                }
                history.append(new_obs)
                if len(history) > self._max_windows:
                    history = history[-self._max_windows:]
                active_obs = dict(new_obs)

            self._state[merchant_id] = history
            self._state.move_to_end(merchant_id)

            if len(self._state) > self._max_merchants:
                self._state.popitem(last=False)

            return active_obs

    def reset(self, merchant_id: Optional[str] = None) -> None:
        """Reset telemetry store for a specific merchant or all merchants."""
        with self._lock:
            if merchant_id is not None:
                self._state.pop(merchant_id, None)
            else:
                self._state.clear()


class FraudSpikeDetector:
    """Detects temporal fraud spikes and velocity anomalies across merchants and population clusters."""

    def __init__(
        self,
        model_path: str = os.path.join("models", "fraud_spike_model.joblib"),
        metadata_path: str = os.path.join("models", "fraud_spike_metadata.json"),
        tracker: Optional[MerchantIncidentTracker] = None,
        telemetry_store: Optional[FiveMinuteTelemetryStore] = None,
    ):
        """Initialize the detector by loading serialized model, metadata, incident tracker, and telemetry store."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Trained fraud-spike model artifact not found at '{model_path}'.")

        self.pipeline = joblib.load(model_path)
        self.metadata = {}
        if metadata_path and os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)

        self.tracker = tracker if tracker is not None else MerchantIncidentTracker()
        self.telemetry_store = telemetry_store if telemetry_store is not None else FiveMinuteTelemetryStore()

    def reset_tracker(self, merchant_id: Optional[str] = None) -> None:
        """Reset incident persistence tracker and telemetry store state."""
        self.tracker.reset(merchant_id)
        self.telemetry_store.reset(merchant_id)

    def record_five_minute_observation(self, merchant_id: str, observation: Dict[str, Any]) -> None:
        """Record a 5-minute sub-window telemetry observation for a merchant."""
        self.telemetry_store.record_observation(merchant_id, observation)

    def record_payment_event(
        self,
        merchant_id: str,
        timestamp: Optional[float] = None,
        is_fraud: bool = False,
        window_seconds: int = 300,
    ) -> Dict[str, Any]:
        """Record a single payment event into the 5-minute telemetry store for a merchant."""
        return self.telemetry_store.record_payment_event(
            merchant_id=merchant_id,
            timestamp=timestamp,
            is_fraud=is_fraud,
            window_seconds=window_seconds,
        )

    def _prepare_features(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate, compute derived temporal metrics, and sanitize features for inference."""
        eps = 1e-4

        def safe_float(val: Any, default: float = 0.0) -> float:
            try:
                if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
                    return default
                f = float(val)
                return default if (math.isnan(f) or math.isinf(f)) else f
            except (ValueError, TypeError):
                return default

        raw_base_tx = safe_float(input_data.get("baseline_tx_count"), default=240.0)
        raw_curr_tx = safe_float(input_data.get("current_tx_count"), default=10.0)

        # True non-negative counts observed in inputs
        clean_base_tx = float(max(0.0, raw_base_tx))
        clean_curr_tx = float(max(0.0, raw_curr_tx))

        # Model feature input clamping (>= 1.0 prevents NaN/inf in model pipeline)
        baseline_tx = float(max(1.0, clean_base_tx))
        current_tx = float(max(1.0, clean_curr_tx))

        # Fraud counts and rates
        raw_base_fraud = safe_float(input_data.get("baseline_fraud_count"), default=0.0)
        raw_curr_fraud = safe_float(input_data.get("current_fraud_count"), default=0.0)

        baseline_fraud_cnt = float(max(0.0, min(raw_base_fraud, clean_base_tx if clean_base_tx > 0 else 0.0)))
        current_fraud_cnt = float(max(0.0, min(raw_curr_fraud, clean_curr_tx if clean_curr_tx > 0 else 0.0)))

        if "baseline_fraud_rate" in input_data and input_data["baseline_fraud_rate"] is not None:
            baseline_fraud_rate = float(np.clip(safe_float(input_data["baseline_fraud_rate"], default=0.0), 0.0, 1.0))
        else:
            baseline_fraud_rate = float(np.clip(baseline_fraud_cnt / baseline_tx, 0.0, 1.0)) if clean_base_tx > 0 else 0.0

        if "current_fraud_rate" in input_data and input_data["current_fraud_rate"] is not None:
            current_fraud_rate = float(np.clip(safe_float(input_data["current_fraud_rate"], default=0.0), 0.0, 1.0))
        else:
            current_fraud_rate = float(np.clip(current_fraud_cnt / current_tx, 0.0, 1.0)) if clean_curr_tx > 0 else 0.0

        # Device metrics
        raw_base_dev = safe_float(input_data.get("baseline_device_count"), default=max(1.0, baseline_tx * 0.8))
        raw_curr_dev = safe_float(input_data.get("current_device_count"), default=max(1.0, current_tx * 0.8))

        baseline_devices = float(max(1.0, raw_base_dev))
        current_devices = float(max(1.0, raw_curr_dev))

        # Suspicious anomaly scores
        baseline_susp = float(np.clip(safe_float(input_data.get("baseline_suspicious_score"), default=0.05), 0.0, 1.0))
        current_susp = float(np.clip(safe_float(input_data.get("current_suspicious_score"), default=0.05), 0.0, 1.0))

        # Derived temporal metrics
        fraud_rate_delta = float(current_fraud_rate - baseline_fraud_rate)
        fraud_rate_ratio = float((current_fraud_rate + eps) / (baseline_fraud_rate + eps))

        # Volume surge calculation with zero-count awareness (P2)
        volume_surge_observable = (clean_base_tx > 0.0) and (clean_curr_tx > 0.0)
        if clean_curr_tx == 0.0:
            volume_surge_ratio = 0.0
        elif clean_base_tx == 0.0:
            volume_surge_ratio = 1.0  # Neutral baseline for model pipeline
        else:
            baseline_hourly_vol = float(clean_base_tx / 24.0)
            volume_surge_ratio = float(clean_curr_tx / max(0.1, baseline_hourly_vol))

        device_concentration = float(current_tx / current_devices) if clean_curr_tx > 0.0 else 1.0
        susp_delta = float(current_susp - baseline_susp)

        return {
            "baseline_tx_count": baseline_tx,
            "current_tx_count": current_tx,
            "raw_baseline_tx_count": clean_base_tx,
            "raw_current_tx_count": clean_curr_tx,
            "volume_surge_observable": volume_surge_observable,
            "baseline_fraud_count": baseline_fraud_cnt,
            "current_fraud_count": current_fraud_cnt,
            "baseline_fraud_rate": baseline_fraud_rate,
            "current_fraud_rate": current_fraud_rate,
            "fraud_rate_delta": fraud_rate_delta,
            "fraud_rate_ratio": fraud_rate_ratio,
            "volume_surge_ratio": volume_surge_ratio,
            "baseline_device_count": baseline_devices,
            "current_device_count": current_devices,
            "device_concentration_ratio": device_concentration,
            "baseline_suspicious_score": baseline_susp,
            "current_suspicious_score": current_susp,
            "suspicious_score_delta": susp_delta,
        }

    def _evaluate_evidence_quality(self, baseline_tx: float, current_tx: float) -> Tuple[str, str]:
        """Evaluate observational sample adequacy and produce plain English summary."""
        if current_tx < MIN_CURRENT_TX_FOR_LIMITED_EVIDENCE or baseline_tx < MIN_BASELINE_TX_FOR_LIMITED_EVIDENCE:
            quality = "INSUFFICIENT_SAMPLE"
            summary = (
                f"Evidence is insufficient: the observed fraud-rate change is based on too few transactions "
                f"({int(current_tx)} current, {int(baseline_tx)} baseline) to reliably classify as a confirmed fraud spike."
            )
        elif current_tx < MIN_CURRENT_TX_FOR_STRONG_EVIDENCE or baseline_tx < MIN_BASELINE_TX_FOR_STRONG_EVIDENCE:
            quality = "LIMITED_SAMPLE"
            summary = (
                f"Evidence is limited because the current observation window contains relatively few transactions "
                f"({int(current_tx)} current, {int(baseline_tx)} baseline)."
            )
        else:
            quality = "SUFFICIENT"
            summary = (
                f"Evidence is sufficient: the spike assessment is supported by a large number of baseline and current transactions "
                f"({int(current_tx)} current, {int(baseline_tx)} baseline)."
            )

        return quality, summary

    def _determine_operational_confidence(self, spike_score: int, evidence_quality: str) -> str:
        """Determine operational confidence based on signal strength and evidence volume."""
        if evidence_quality == "INSUFFICIENT_SAMPLE":
            return "LOW"
        elif evidence_quality == "LIMITED_SAMPLE":
            if spike_score >= 70 or spike_score <= 15:
                return "MEDIUM"
            return "LOW"
        else:  # SUFFICIENT
            if spike_score >= 70 or spike_score <= 15:
                return "HIGH"
            return "MEDIUM"

    def _extract_spike_factors(self, feat: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Identify specific risk and mitigating factors explaining the temporal change."""
        spike_factors = []
        mitigating_factors = []

        base_fr = feat["baseline_fraud_rate"]
        curr_fr = feat["current_fraud_rate"]
        fr_ratio = feat["fraud_rate_ratio"]
        vol_ratio = feat["volume_surge_ratio"]
        dev_conc = feat["device_concentration_ratio"]
        susp_delta = feat["suspicious_score_delta"]

        vol_observable = feat.get("volume_surge_observable", True)
        curr_tx_count = feat.get("raw_current_tx_count", feat["current_tx_count"])

        if curr_tx_count > 0:
            if curr_fr > base_fr and (curr_fr - base_fr) >= 0.10:
                spike_factors.append(f"Fraud rate increased from {base_fr:.1%} to {curr_fr:.1%} ({fr_ratio:.1f}x surge)")
            elif curr_fr > base_fr and (curr_fr - base_fr) >= 0.04:
                spike_factors.append(f"Elevated fraud rate trend ({curr_fr:.1%} vs {base_fr:.1%} baseline)")

        if vol_observable and vol_ratio >= 2.5:
            spike_factors.append(f"Hourly transaction volume surged {vol_ratio:.1f}x above baseline")

        if curr_tx_count > 0 and dev_conc >= 2.0:
            spike_factors.append(f"Elevated device concentration ({dev_conc:.1f} orders per distinct device)")

        if susp_delta >= 0.30:
            spike_factors.append(f"Sharp increase in syndicate connectivity indicators (+{susp_delta:.2f})")

        # Mitigating signals (P2 zero-count aware)
        if curr_tx_count > 0:
            if curr_fr <= 0.03:
                mitigating_factors.append(f"Current fraud rate is healthy and low ({curr_fr:.1%})")
            if abs(curr_fr - base_fr) <= 0.02:
                mitigating_factors.append("Fraud rate remains stable and aligned with historical baseline")
            if vol_observable and vol_ratio >= 2.5 and curr_fr <= 0.03:
                mitigating_factors.append("High volume corresponds to legitimate marketing/promotional surge")
            if dev_conc <= 1.2:
                mitigating_factors.append("Healthy 1-to-1 device-to-transaction ratio")
        else:
            mitigating_factors.append("No transaction activity observed in current window")

        if not spike_factors:
            spike_factors.append("Traffic volume and fraud indicators within standard baseline tolerances")

        return spike_factors, mitigating_factors

    def _aggregate_five_minute_telemetry(self, observations: Optional[List[Any]]) -> Dict[str, Any]:
        """Deterministically aggregate 5-minute sub-window observations with zero-count safety."""
        if not observations:
            return {
                "available": False,
                "observation_count": 0,
                "current_tx_count": None,
                "baseline_avg_tx_count": None,
                "current_fraud_rate": None,
                "baseline_fraud_rate": None,
                "velocity_ratio": None,
                "fraud_rate_delta": None,
                "evidence_quality": "NO_TELEMETRY",
                "guardrail_triggered": False,
                "burst_detected": False,
                "promotional_surge": False,
                "summary": "No 5-minute sub-window telemetry provided.",
            }

        def safe_float(val: Any, default: float = 0.0) -> float:
            try:
                if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
                    return default
                f = float(val)
                return default if (math.isnan(f) or math.isinf(f)) else f
            except (ValueError, TypeError):
                return default

        clean_obs = []
        for obs in observations:
            if hasattr(obs, "model_dump"):
                obs = obs.model_dump()
            if not isinstance(obs, dict):
                continue
            raw_tx = safe_float(obs.get("tx_count", obs.get("transaction_count", 0)))
            tx = max(0.0, raw_tx)
            raw_fraud = safe_float(obs.get("fraud_count", 0))
            fraud_cnt = max(0.0, min(raw_fraud, tx))
            if "fraud_rate" in obs and obs["fraud_rate"] is not None:
                fr = float(np.clip(safe_float(obs["fraud_rate"]), 0.0, 1.0))
            else:
                fr = float(fraud_cnt / tx) if tx > 0 else 0.0
            ts = obs.get("timestamp", obs.get("observation_timestamp", None))
            clean_obs.append({
                "timestamp": ts,
                "tx_count": tx,
                "fraud_count": fraud_cnt,
                "fraud_rate": fr,
            })

        N = len(clean_obs)
        if N == 0:
            return {
                "available": False,
                "observation_count": 0,
                "current_tx_count": None,
                "baseline_avg_tx_count": None,
                "current_fraud_rate": None,
                "baseline_fraud_rate": None,
                "velocity_ratio": None,
                "fraud_rate_delta": None,
                "evidence_quality": "NO_TELEMETRY",
                "guardrail_triggered": False,
                "burst_detected": False,
                "promotional_surge": False,
                "summary": "No valid 5-minute sub-window telemetry provided.",
            }

        curr_obs = clean_obs[-1]
        curr_tx = curr_obs["tx_count"]
        curr_fr = curr_obs["fraud_rate"]
        prior_obs = clean_obs[:-1]

        if len(prior_obs) == 0:
            return {
                "available": True,
                "observation_count": 1,
                "current_tx_count": int(curr_tx),
                "baseline_avg_tx_count": None,
                "current_fraud_rate": round(curr_fr, 4),
                "baseline_fraud_rate": None,
                "velocity_ratio": None,
                "fraud_rate_delta": None,
                "evidence_quality": "INSUFFICIENT_SAMPLE",
                "guardrail_triggered": False,
                "burst_detected": False,
                "promotional_surge": False,
                "summary": "Insufficient 5-minute telemetry is available to establish a reliable short-window surge.",
            }

        baseline_tx_list = [o["tx_count"] for o in prior_obs]
        baseline_total_tx = sum(baseline_tx_list)
        baseline_avg_tx = float(np.mean(baseline_tx_list))
        baseline_total_fraud = sum(o["fraud_count"] for o in prior_obs)

        if baseline_total_tx > 0:
            baseline_fr = float(np.clip(baseline_total_fraud / baseline_total_tx, 0.0, 1.0))
        else:
            baseline_fr = float(np.clip(np.mean([o["fraud_rate"] for o in prior_obs]), 0.0, 1.0))

        # Zero-count and zero-baseline safe velocity ratio (P2)
        if curr_tx == 0.0:
            velocity_ratio = 0.0
        elif baseline_avg_tx == 0.0:
            velocity_ratio = 1.0  # Neutral baseline, do NOT manufacture infinite surge
        else:
            velocity_ratio = round(float(curr_tx / baseline_avg_tx), 4)

        fr_delta = round(float(curr_fr - baseline_fr), 4)

        # Evidence quality classification
        if N < 3 or baseline_total_tx < 6.0:
            evidence_quality = "INSUFFICIENT_SAMPLE"
        elif baseline_total_tx < 20.0 or curr_tx < 5.0:
            evidence_quality = "LIMITED_SAMPLE"
        else:
            evidence_quality = "SUFFICIENT"

        # Guardrail & burst detection
        is_sufficient = (N >= 3) and (baseline_total_tx >= 10.0) and (curr_tx >= 5.0)

        # Genuine fraud surge: high velocity + significant fraud rate jump
        is_burst = (
            is_sufficient
            and (velocity_ratio >= 2.5)
            and (curr_fr >= 0.25)
            and (fr_delta >= 0.15 or curr_fr >= 0.35)
        )

        # Legitimate promotional surge: high velocity + low fraud rate
        is_promo = (
            (is_sufficient or (N >= 2 and baseline_total_tx >= 10.0))
            and (velocity_ratio >= 2.5)
            and (curr_fr <= 0.03)
        )

        if is_burst:
            guardrail_triggered = True
            summary = (
                f"Rapid transaction activity was observed across recent 5-minute windows "
                f"({velocity_ratio:.1f}x velocity surge, {curr_fr:.1%} fraud rate)."
            )
        elif not is_sufficient:
            guardrail_triggered = False
            summary = "Insufficient 5-minute telemetry is available to establish a reliable short-window surge."
        elif is_promo:
            guardrail_triggered = False
            summary = (
                f"Recent 5-minute volume surge ({velocity_ratio:.1f}x) corresponds to legitimate "
                f"promotional traffic with healthy fraud rate ({curr_fr:.1%})."
            )
        else:
            guardrail_triggered = False
            summary = f"5-minute sub-window telemetry is stable (velocity ratio: {velocity_ratio:.1f}x, fraud rate: {curr_fr:.1%})."

        return {
            "available": True,
            "observation_count": N,
            "current_tx_count": int(curr_tx),
            "baseline_avg_tx_count": round(baseline_avg_tx, 2),
            "current_fraud_rate": round(curr_fr, 4),
            "baseline_fraud_rate": round(baseline_fr, 4),
            "velocity_ratio": velocity_ratio,
            "fraud_rate_delta": fr_delta,
            "evidence_quality": evidence_quality,
            "guardrail_triggered": guardrail_triggered,
            "burst_detected": is_burst,
            "promotional_surge": is_promo,
            "summary": summary,
        }

    def _generate_explanation(
        self,
        spike_level: str,
        spike_score: int,
        feat: Dict[str, Any],
        evidence_quality: str,
        guardrail_triggered: bool = False,
        raw_spike_score: Optional[int] = None,
        persistence_escalated: bool = False,
        consecutive_windows: int = 0,
        five_min_metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate plain-language explanation of the spike assessment."""
        base_fr = feat["baseline_fraud_rate"]
        curr_fr = feat["current_fraud_rate"]
        fr_ratio = feat["fraud_rate_ratio"]
        vol_ratio = feat["volume_surge_ratio"]
        vol_observable = feat.get("volume_surge_observable", True)
        curr_tx = int(feat.get("raw_current_tx_count", feat["current_tx_count"]))
        delta_pct = (curr_fr - base_fr) * 100

        if evidence_quality == "INSUFFICIENT_SAMPLE" and spike_level == "HIGH":
            return (
                f"Model signals indicate a potential spike (score: {spike_score}/100), but the observation is based on "
                f"insufficient transaction volume ({curr_tx} transactions). Additional data should be collected before "
                f"treating this as a confirmed operational spike."
            )

        if persistence_escalated and spike_level == "HIGH":
            return (
                f"High operational risk escalated by persistence policy (score: {spike_score}/100, raw ML: {raw_spike_score}/100). "
                f"Merchant has exhibited elevated risk across {consecutive_windows} consecutive evaluation windows, "
                f"triggering automatic policy escalation to strict enforcement."
            )

        if five_min_metrics and five_min_metrics.get("guardrail_triggered") and spike_level == "MEDIUM" and raw_spike_score is not None and raw_spike_score < 30:
            vel_r = five_min_metrics.get("velocity_ratio", 1.0)
            c_fr = five_min_metrics.get("current_fraud_rate", 0.0)
            return (
                f"Moderate fraud velocity change detected (policy-adjusted score: {spike_score}/100, raw ML: {raw_spike_score}/100). "
                f"Rapid transaction activity was observed across recent 5-minute windows "
                f"({vel_r:.1f}x velocity surge, {c_fr:.1%} fraud rate), warranting active monitoring."
            )

        if guardrail_triggered and spike_level == "MEDIUM" and raw_spike_score is not None and raw_spike_score < 30:
            return (
                f"Moderate fraud velocity change detected (policy-adjusted score: {spike_score}/100, raw ML: {raw_spike_score}/100). "
                f"A significant increase in observed fraud rate ({curr_fr:.1%} vs {base_fr:.1%} baseline, +{delta_pct:.1f} percentage points) "
                f"was detected across {curr_tx} transactions, warranting active monitoring."
            )

        if spike_level == "HIGH":
            vol_detail = f" (volume surge: {vol_ratio:.1f}x)" if vol_observable else ""
            return (
                f"Fraud activity increased from {base_fr:.1%} during the baseline window to {curr_fr:.1%} in the current window, "
                f"representing a {fr_ratio:.1f}x increase{vol_detail}. "
                f"The increase exceeds validated spike thresholds and is classified as HIGH."
            )
        elif spike_level == "MEDIUM":
            return (
                f"Moderate fraud velocity change detected (score: {spike_score}/100). Current fraud rate ({curr_fr:.1%}) "
                f"is elevated compared to historical baseline ({base_fr:.1%}), warranting active monitoring."
            )
        else:
            if curr_tx == 0:
                return (
                    f"No transaction activity observed in the current window (score: {spike_score}/100). "
                    f"Traffic volume and fraud indicators remain within standard baseline tolerances."
                )
            return (
                f"No significant fraud spike detected (score: {spike_score}/100). Fraud activity ({curr_fr:.1%}) "
                f"remains consistent with the historical baseline ({base_fr:.1%}) without abnormal cluster velocity."
            )

    def _determine_action(self, spike_level: str, evidence_quality: str) -> str:
        """Determine automated defense action for the merchant or cluster."""
        if evidence_quality == "INSUFFICIENT_SAMPLE" and spike_level == "HIGH":
            return "COLLECT_ADDITIONAL_DATA_BEFORE_ENFORCING"

        if spike_level == "HIGH":
            return "ENABLE_STRICT_RATE_LIMITS_AND_2FA"
        elif spike_level == "MEDIUM":
            return "FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR"
        else:
            return "ALLOW_STANDARD_OPERATIONS"

    def detect_spike(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect fraud spike for a merchant observation window."""
        merchant_id = str(input_data.get("merchant_id", "MERCH_UNKNOWN"))
        baseline_window = str(input_data.get("baseline_window", "previous_24h"))
        current_window = str(input_data.get("current_window", "latest_1h"))

        feat = self._prepare_features(input_data)
        df_model = pd.DataFrame([feat])[SPIKE_FEATURE_COLUMNS]

        prob = float(self.pipeline.predict_proba(df_model)[:, 1][0])
        pred = int(self.pipeline.predict(df_model)[0])

        raw_spike_score = int(np.clip(np.round(prob * 100), 0, 100))
        if raw_spike_score >= 70:
            raw_spike_level = "HIGH"
        elif raw_spike_score >= 30:
            raw_spike_level = "MEDIUM"
        else:
            raw_spike_level = "LOW"

        # Deterministic Policy Guardrail (P1):
        # Severe fraud-rate increase floor: If fraud_rate_delta >= 0.25 and current_tx_count >= 15.0,
        # guarantee at least MEDIUM risk tier to prevent severe fraud deltas from being masked
        # by missing or low upstream suspicious_score telemetry.
        clean_curr_tx = feat["raw_current_tx_count"]
        clean_base_tx = feat["raw_baseline_tx_count"]
        guardrail_triggered = (feat["fraud_rate_delta"] >= 0.25) and (clean_curr_tx >= 15.0)

        # 5-Minute Sub-Window Telemetry Layer (P5):
        sub_telemetry_input = input_data.get("five_minute_telemetry", input_data.get("sub_windows", None))
        if sub_telemetry_input is not None:
            if isinstance(sub_telemetry_input, list):
                sub_obs = sub_telemetry_input
                if merchant_id and merchant_id != "MERCH_UNKNOWN":
                    self.telemetry_store.record_observations(merchant_id, sub_telemetry_input)
            elif isinstance(sub_telemetry_input, dict):
                if merchant_id and merchant_id != "MERCH_UNKNOWN":
                    self.telemetry_store.record_observation(merchant_id, sub_telemetry_input)
                    sub_obs = self.telemetry_store.get_observations(merchant_id)
                else:
                    sub_obs = [sub_telemetry_input]
            else:
                sub_obs = []
        else:
            sub_obs = []

        five_min_metrics = self._aggregate_five_minute_telemetry(sub_obs)
        five_min_guardrail = bool(five_min_metrics.get("guardrail_triggered", False))

        if (guardrail_triggered or five_min_guardrail) and raw_spike_level == "LOW":
            pre_persistence_level = "MEDIUM"
            pre_persistence_score = max(raw_spike_score, 45)
        else:
            pre_persistence_level = raw_spike_level
            pre_persistence_score = raw_spike_score

        # Stateful Incident Escalation Tracker (P3):
        # Track rolling incident counters across consecutive windows per merchant.
        # If a merchant triggers MEDIUM risk in >= 3 consecutive windows, escalate final recommendation to HIGH.
        consecutive_windows, persistence_escalated = self.tracker.record_evaluation(
            merchant_id=merchant_id,
            operational_tier=pre_persistence_level,
        )

        if persistence_escalated and pre_persistence_level == "MEDIUM":
            spike_level = "HIGH"
            spike_score = max(pre_persistence_score, 75)
        else:
            spike_level = pre_persistence_level
            spike_score = pre_persistence_score

        # Evidence quality and operational confidence (P2 zero-count aware)
        evidence_quality, evidence_summary = self._evaluate_evidence_quality(
            clean_base_tx, clean_curr_tx
        )
        confidence = self._determine_operational_confidence(spike_score, evidence_quality)

        action = self._determine_action(spike_level, evidence_quality)
        spike_factors, mitigating_factors = self._extract_spike_factors(feat)

        if guardrail_triggered:
            delta_pct = feat["fraud_rate_delta"] * 100
            guardrail_factor = f"Large increase in observed fraud rate relative to baseline ({delta_pct:.1f} percentage points)."
            if guardrail_factor not in spike_factors:
                spike_factors.insert(0, guardrail_factor)
            # Remove misleading stability mitigations if guardrail triggered
            mitigating_factors = [
                m for m in mitigating_factors
                if "remains stable and aligned" not in m and "healthy and low" not in m
            ]

        if five_min_guardrail:
            vel_val = five_min_metrics.get("velocity_ratio", 1.0)
            fr_val = five_min_metrics.get("current_fraud_rate", 0.0)
            five_min_factor = f"Rapid 5-minute transaction burst detected ({vel_val:.1f}x velocity surge, {fr_val:.1%} fraud rate across recent 5-min window)."
            if five_min_factor not in spike_factors:
                spike_factors.insert(0, five_min_factor)
            mitigating_factors = [
                m for m in mitigating_factors
                if "remains stable and aligned" not in m and "healthy and low" not in m
            ]

        if five_min_metrics["available"]:
            if five_min_metrics.get("current_tx_count") == 0:
                if "No transaction activity observed in latest 5-minute sub-window" not in mitigating_factors:
                    mitigating_factors.append("No transaction activity observed in latest 5-minute sub-window")
            elif five_min_metrics.get("promotional_surge"):
                vel_val = five_min_metrics.get("velocity_ratio", 1.0)
                fr_val = five_min_metrics.get("current_fraud_rate", 0.0)
                promo_factor = f"Recent 5-minute volume surge ({vel_val:.1f}x) corresponds to legitimate promotional traffic with low fraud rate ({fr_val:.1%})"
                if promo_factor not in mitigating_factors:
                    mitigating_factors.append(promo_factor)
            elif five_min_metrics.get("evidence_quality") == "INSUFFICIENT_SAMPLE" and not five_min_guardrail:
                insuf_factor = "Insufficient 5-minute telemetry is available to establish a reliable short-window surge."
                if insuf_factor not in mitigating_factors and insuf_factor not in spike_factors:
                    mitigating_factors.append(insuf_factor)

        if persistence_escalated:
            persist_factor = f"Persistent anomaly pattern: {consecutive_windows} consecutive evaluation windows with elevated risk."
            if persist_factor not in spike_factors:
                spike_factors.insert(0, persist_factor)

        explanation = self._generate_explanation(
            spike_level=spike_level,
            spike_score=spike_score,
            feat=feat,
            evidence_quality=evidence_quality,
            guardrail_triggered=guardrail_triggered,
            raw_spike_score=raw_spike_score,
            persistence_escalated=persistence_escalated,
            consecutive_windows=consecutive_windows,
            five_min_metrics=five_min_metrics,
        )

        return {
            "merchant_id": merchant_id,
            "spike_prediction": pred,
            "spike_probability": round(prob, 4),
            "spike_score": spike_score,
            "spike_level": spike_level,
            "raw_spike_probability": round(prob, 4),
            "raw_spike_score": raw_spike_score,
            "raw_spike_level": raw_spike_level,
            "guardrail_triggered": guardrail_triggered,
            "five_minute_telemetry_available": five_min_metrics["available"],
            "five_minute_observation_count": five_min_metrics["observation_count"],
            "five_minute_current_tx_count": five_min_metrics["current_tx_count"],
            "five_minute_velocity_ratio": five_min_metrics["velocity_ratio"],
            "five_minute_guardrail_triggered": five_min_guardrail,
            "consecutive_anomaly_windows": consecutive_windows,
            "persistence_escalation_triggered": persistence_escalated,
            "baseline_window": baseline_window,
            "current_window": current_window,
            "baseline_fraud_rate": round(feat["baseline_fraud_rate"], 4),
            "current_fraud_rate": round(feat["current_fraud_rate"], 4),
            "fraud_rate_change": round(feat["fraud_rate_delta"], 4),
            "evidence_quality": evidence_quality,
            "confidence": confidence,
            "evidence_summary": evidence_summary,
            "spike_factors": spike_factors,
            "mitigating_factors": mitigating_factors,
            "explanation": explanation,
            "recommended_action": action,
        }

