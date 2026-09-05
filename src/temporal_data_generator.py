"""Temporal Dataset Generator for Fraud-Spike Detection.

Generates realistic temporal merchant activity windows comparing a historical baseline
(e.g., previous 24 hours) against a current evaluation window (e.g., latest 1 hour).

Simulates:
1. Normal Stable Traffic (Spike = 0): Stable low fraud rate (1-4%) and regular transaction volume.
2. Genuine Fraud Spikes (Spike = 1): Sudden velocity surge with a sharp increase in fraud rate (18-45%), high device cycling, and elevated syndicate indicators.
3. High but Stable Fraud Rate (Spike = 0, Hard Negative): Merchant with historically elevated dispute baseline (10-15%) that remains steady in the current window.
4. High Volume Flash Sale / Promo (Spike = 0, Hard Negative): 5x-10x volume increase during legitimate marketing events with standard low fraud rates (1-3%).
5. Low-Volume Random Noise (Spike = 0, Hard Negative): Small transaction count (1-3 tx) where 1 disputed transaction creates statistical noise without representing an actual syndicate attack.
6. Legitimate Organic Growth (Spike = 0): Gradual 20-50% volume growth with stable fraud baseline.
"""

import os
from typing import Tuple, Dict, Any, List
import numpy as np
import pandas as pd


SPIKE_FEATURE_COLUMNS: List[str] = [
    "baseline_tx_count",
    "current_tx_count",
    "baseline_fraud_count",
    "current_fraud_count",
    "baseline_fraud_rate",
    "current_fraud_rate",
    "fraud_rate_delta",
    "fraud_rate_ratio",
    "volume_surge_ratio",
    "baseline_device_count",
    "current_device_count",
    "device_concentration_ratio",
    "baseline_suspicious_score",
    "current_suspicious_score",
    "suspicious_score_delta",
]

SPIKE_TARGET_COLUMN = "fraud_spike_label"


def generate_fraud_spike_windows(
    num_samples: int = 4000,
    spike_ratio: float = 0.20,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Generate structured merchant temporal observation windows with explicit spike ground truth."""
    rng = np.random.default_rng(random_seed)

    num_spikes = int(num_samples * spike_ratio)
    num_normal = num_samples - num_spikes

    records = []

    # -------------------------------------------------------------
    # 1. NORMAL / NON-SPIKE SCENARIOS (target = 0)
    # -------------------------------------------------------------
    # Sub-scenarios:
    # 50% Standard stable merchants (low fraud, normal volume)
    # 20% High-volume Flash Sale / Marketing burst (volume surge, LOW fraud) [HARD NEGATIVE]
    # 15% High-but-stable fraud rate merchants (steady 10-15% fraud, no sudden change) [HARD NEGATIVE]
    # 10% Low-volume random fluctuation (small N noise) [HARD NEGATIVE]
    # 5%  Organic merchant growth (mild volume expansion, steady fraud)
    n_std = int(num_normal * 0.50)
    n_flash = int(num_normal * 0.20)
    n_high_stable = int(num_normal * 0.15)
    n_small_noise = int(num_normal * 0.10)
    n_organic = num_normal - n_std - n_flash - n_high_stable - n_small_noise

    # 1a. Standard Stable Merchants
    for i in range(n_std):
        merchant_id = f"MERCH_STD_{i+1:05d}"
        hourly_baseline_rate = rng.uniform(20.0, 150.0)
        baseline_tx_count = int(hourly_baseline_rate * 24 * rng.uniform(0.90, 1.10))
        baseline_fraud_rate = float(np.round(rng.uniform(0.01, 0.04), 4))
        baseline_fraud_count = int(baseline_tx_count * baseline_fraud_rate)

        current_tx_count = max(1, int(hourly_baseline_rate * rng.uniform(0.85, 1.15)))
        current_fraud_rate = float(np.round(np.clip(baseline_fraud_rate * rng.uniform(0.80, 1.20), 0.0, 0.06), 4))
        current_fraud_count = int(np.round(current_tx_count * current_fraud_rate))

        baseline_device_count = max(1, int(baseline_tx_count * rng.uniform(0.70, 0.90)))
        current_device_count = max(1, int(current_tx_count * rng.uniform(0.70, 0.90)))

        baseline_susp = float(np.round(rng.uniform(0.02, 0.10), 4))
        current_susp = float(np.round(rng.uniform(0.02, 0.12), 4))

        records.append({
            "merchant_id": merchant_id,
            "scenario": "standard_stable",
            "baseline_tx_count": baseline_tx_count,
            "current_tx_count": current_tx_count,
            "baseline_fraud_count": baseline_fraud_count,
            "current_fraud_count": current_fraud_count,
            "baseline_fraud_rate": baseline_fraud_rate,
            "current_fraud_rate": current_fraud_rate,
            "baseline_device_count": baseline_device_count,
            "current_device_count": current_device_count,
            "baseline_suspicious_score": baseline_susp,
            "current_suspicious_score": current_susp,
            SPIKE_TARGET_COLUMN: 0,
        })

    # 1b. Flash Sale / High Volume Surge without Fraud (Hard Negative)
    for i in range(n_flash):
        merchant_id = f"MERCH_FLASH_{i+1:05d}"
        hourly_baseline_rate = rng.uniform(30.0, 100.0)
        baseline_tx_count = int(hourly_baseline_rate * 24 * rng.uniform(0.90, 1.10))
        baseline_fraud_rate = float(np.round(rng.uniform(0.01, 0.03), 4))
        baseline_fraud_count = int(baseline_tx_count * baseline_fraud_rate)

        # 4x to 8x volume surge in current 1h window
        current_tx_count = int(hourly_baseline_rate * rng.uniform(4.0, 8.0))
        # Fraud rate stays low or even dilutes
        current_fraud_rate = float(np.round(rng.uniform(0.008, 0.025), 4))
        current_fraud_count = int(np.round(current_tx_count * current_fraud_rate))

        baseline_device_count = max(1, int(baseline_tx_count * rng.uniform(0.75, 0.92)))
        current_device_count = max(1, int(current_tx_count * rng.uniform(0.80, 0.95)))

        baseline_susp = float(np.round(rng.uniform(0.02, 0.08), 4))
        current_susp = float(np.round(rng.uniform(0.03, 0.12), 4))

        records.append({
            "merchant_id": merchant_id,
            "scenario": "flash_sale_high_vol",
            "baseline_tx_count": baseline_tx_count,
            "current_tx_count": current_tx_count,
            "baseline_fraud_count": baseline_fraud_count,
            "current_fraud_count": current_fraud_count,
            "baseline_fraud_rate": baseline_fraud_rate,
            "current_fraud_rate": current_fraud_rate,
            "baseline_device_count": baseline_device_count,
            "current_device_count": current_device_count,
            "baseline_suspicious_score": baseline_susp,
            "current_suspicious_score": current_susp,
            SPIKE_TARGET_COLUMN: 0,
        })

    # 1c. High-but-Stable Fraud Rate (Hard Negative)
    for i in range(n_high_stable):
        merchant_id = f"MERCH_HIBAS_{i+1:05d}"
        hourly_baseline_rate = rng.uniform(20.0, 80.0)
        baseline_tx_count = int(hourly_baseline_rate * 24 * rng.uniform(0.90, 1.10))
        baseline_fraud_rate = float(np.round(rng.uniform(0.10, 0.16), 4))
        baseline_fraud_count = int(baseline_tx_count * baseline_fraud_rate)

        current_tx_count = max(1, int(hourly_baseline_rate * rng.uniform(0.85, 1.15)))
        current_fraud_rate = float(np.round(np.clip(baseline_fraud_rate * rng.uniform(0.90, 1.10), 0.08, 0.18), 4))
        current_fraud_count = int(np.round(current_tx_count * current_fraud_rate))

        baseline_device_count = max(1, int(baseline_tx_count * rng.uniform(0.60, 0.80)))
        current_device_count = max(1, int(current_tx_count * rng.uniform(0.60, 0.80)))

        baseline_susp = float(np.round(rng.uniform(0.25, 0.40), 4))
        current_susp = float(np.round(rng.uniform(0.25, 0.42), 4))

        records.append({
            "merchant_id": merchant_id,
            "scenario": "high_stable_fraud",
            "baseline_tx_count": baseline_tx_count,
            "current_tx_count": current_tx_count,
            "baseline_fraud_count": baseline_fraud_count,
            "current_fraud_count": current_fraud_count,
            "baseline_fraud_rate": baseline_fraud_rate,
            "current_fraud_rate": current_fraud_rate,
            "baseline_device_count": baseline_device_count,
            "current_device_count": current_device_count,
            "baseline_suspicious_score": baseline_susp,
            "current_suspicious_score": current_susp,
            SPIKE_TARGET_COLUMN: 0,
        })

    # 1d. Low-Volume Random Noise (Hard Negative)
    for i in range(n_small_noise):
        merchant_id = f"MERCH_NOISE_{i+1:05d}"
        hourly_baseline_rate = rng.uniform(1.0, 4.0)
        baseline_tx_count = int(hourly_baseline_rate * 24)
        baseline_fraud_count = int(rng.choice([0, 1, 2], p=[0.70, 0.25, 0.05]))
        baseline_fraud_rate = float(np.round(baseline_fraud_count / max(1, baseline_tx_count), 4))

        current_tx_count = int(rng.choice([1, 2, 3, 4], p=[0.40, 0.35, 0.15, 0.10]))
        current_fraud_count = int(rng.choice([0, 1], p=[0.75, 0.25]))
        current_fraud_rate = float(np.round(current_fraud_count / current_tx_count, 4))

        baseline_device_count = max(1, int(baseline_tx_count * 0.9))
        current_device_count = current_tx_count

        baseline_susp = float(np.round(rng.uniform(0.01, 0.15), 4))
        current_susp = float(np.round(rng.uniform(0.01, 0.25), 4))

        records.append({
            "merchant_id": merchant_id,
            "scenario": "low_volume_noise",
            "baseline_tx_count": baseline_tx_count,
            "current_tx_count": current_tx_count,
            "baseline_fraud_count": baseline_fraud_count,
            "current_fraud_count": current_fraud_count,
            "baseline_fraud_rate": baseline_fraud_rate,
            "current_fraud_rate": current_fraud_rate,
            "baseline_device_count": baseline_device_count,
            "current_device_count": current_device_count,
            "baseline_suspicious_score": baseline_susp,
            "current_suspicious_score": current_susp,
            SPIKE_TARGET_COLUMN: 0,
        })

    # 1e. Organic Growth
    for i in range(n_organic):
        merchant_id = f"MERCH_ORG_{i+1:05d}"
        hourly_baseline_rate = rng.uniform(15.0, 60.0)
        baseline_tx_count = int(hourly_baseline_rate * 24)
        baseline_fraud_rate = float(np.round(rng.uniform(0.01, 0.035), 4))
        baseline_fraud_count = int(baseline_tx_count * baseline_fraud_rate)

        current_tx_count = int(hourly_baseline_rate * rng.uniform(1.20, 1.50))
        current_fraud_rate = float(np.round(rng.uniform(0.01, 0.04), 4))
        current_fraud_count = int(np.round(current_tx_count * current_fraud_rate))

        baseline_device_count = max(1, int(baseline_tx_count * 0.85))
        current_device_count = max(1, int(current_tx_count * 0.85))

        baseline_susp = float(np.round(rng.uniform(0.02, 0.08), 4))
        current_susp = float(np.round(rng.uniform(0.02, 0.09), 4))

        records.append({
            "merchant_id": merchant_id,
            "scenario": "organic_growth",
            "baseline_tx_count": baseline_tx_count,
            "current_tx_count": current_tx_count,
            "baseline_fraud_count": baseline_fraud_count,
            "current_fraud_count": current_fraud_count,
            "baseline_fraud_rate": baseline_fraud_rate,
            "current_fraud_rate": current_fraud_rate,
            "baseline_device_count": baseline_device_count,
            "current_device_count": current_device_count,
            "baseline_suspicious_score": baseline_susp,
            "current_suspicious_score": current_susp,
            SPIKE_TARGET_COLUMN: 0,
        })

    # -------------------------------------------------------------
    # 2. GENUINE FRAUD SPIKES (target = 1)
    # -------------------------------------------------------------
    # Sub-scenarios:
    # 60% Sudden syndicate bot rush (high volume surge + sharp fraud increase)
    # 40% Targeted card-testing / account takeover attack (moderate volume, extreme fraud rate jump)
    n_rush = int(num_spikes * 0.60)
    n_attack = num_spikes - n_rush

    # 2a. Syndicate Bot Rush
    for i in range(n_rush):
        merchant_id = f"MERCH_SPIKE_RUSH_{i+1:05d}"
        hourly_baseline_rate = rng.uniform(20.0, 80.0)
        baseline_tx_count = int(hourly_baseline_rate * 24 * rng.uniform(0.90, 1.10))
        baseline_fraud_rate = float(np.round(rng.uniform(0.01, 0.035), 4))
        baseline_fraud_count = int(baseline_tx_count * baseline_fraud_rate)

        # 3x to 8x velocity burst with 20% to 55% fraud rate
        current_tx_count = int(hourly_baseline_rate * rng.uniform(3.0, 7.5))
        current_fraud_rate = float(np.round(rng.uniform(0.22, 0.55), 4))
        current_fraud_count = int(np.round(current_tx_count * current_fraud_rate))

        # Device cycling / concentration (few devices generating many orders)
        baseline_device_count = max(1, int(baseline_tx_count * 0.82))
        current_device_count = max(2, int(current_tx_count * rng.uniform(0.25, 0.45)))

        baseline_susp = float(np.round(rng.uniform(0.02, 0.10), 4))
        current_susp = float(np.round(rng.uniform(0.65, 0.95), 4))

        records.append({
            "merchant_id": merchant_id,
            "scenario": "syndicate_bot_rush",
            "baseline_tx_count": baseline_tx_count,
            "current_tx_count": current_tx_count,
            "baseline_fraud_count": baseline_fraud_count,
            "current_fraud_count": current_fraud_count,
            "baseline_fraud_rate": baseline_fraud_rate,
            "current_fraud_rate": current_fraud_rate,
            "baseline_device_count": baseline_device_count,
            "current_device_count": current_device_count,
            "baseline_suspicious_score": baseline_susp,
            "current_suspicious_score": current_susp,
            SPIKE_TARGET_COLUMN: 1,
        })

    # 2b. Card-Testing / Targeted ATO Surge
    for i in range(n_attack):
        merchant_id = f"MERCH_SPIKE_ATO_{i+1:05d}"
        hourly_baseline_rate = rng.uniform(15.0, 50.0)
        baseline_tx_count = int(hourly_baseline_rate * 24 * rng.uniform(0.90, 1.10))
        baseline_fraud_rate = float(np.round(rng.uniform(0.015, 0.04), 4))
        baseline_fraud_count = int(baseline_tx_count * baseline_fraud_rate)

        # 1.5x to 3.0x volume increase with sharp fraud jump (25% to 60%)
        current_tx_count = int(hourly_baseline_rate * rng.uniform(1.8, 3.5))
        current_fraud_rate = float(np.round(rng.uniform(0.25, 0.60), 4))
        current_fraud_count = int(np.round(current_tx_count * current_fraud_rate))

        baseline_device_count = max(1, int(baseline_tx_count * 0.80))
        current_device_count = max(2, int(current_tx_count * rng.uniform(0.30, 0.50)))

        baseline_susp = float(np.round(rng.uniform(0.03, 0.12), 4))
        current_susp = float(np.round(rng.uniform(0.55, 0.90), 4))

        records.append({
            "merchant_id": merchant_id,
            "scenario": "targeted_ato_surge",
            "baseline_tx_count": baseline_tx_count,
            "current_tx_count": current_tx_count,
            "baseline_fraud_count": baseline_fraud_count,
            "current_fraud_count": current_fraud_count,
            "baseline_fraud_rate": baseline_fraud_rate,
            "current_fraud_rate": current_fraud_rate,
            "baseline_device_count": baseline_device_count,
            "current_device_count": current_device_count,
            "baseline_suspicious_score": baseline_susp,
            "current_suspicious_score": current_susp,
            SPIKE_TARGET_COLUMN: 1,
        })

    df = pd.DataFrame(records)

    # Derive engineered temporal delta/ratio features
    eps = 1e-4
    df["fraud_rate_delta"] = np.round(df["current_fraud_rate"] - df["baseline_fraud_rate"], 4)
    df["fraud_rate_ratio"] = np.round((df["current_fraud_rate"] + eps) / (df["baseline_fraud_rate"] + eps), 4)
    
    baseline_hourly_vol = np.maximum(1.0, df["baseline_tx_count"] / 24.0)
    df["volume_surge_ratio"] = np.round(df["current_tx_count"] / baseline_hourly_vol, 4)
    
    df["device_concentration_ratio"] = np.round(df["current_tx_count"] / np.maximum(1, df["current_device_count"]), 4)
    df["suspicious_score_delta"] = np.round(df["current_suspicious_score"] - df["baseline_suspicious_score"], 4)

    df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = generate_fraud_spike_windows(num_samples=4000, spike_ratio=0.20, random_seed=42)
    print("Generated Fraud-Spike Dataset:", len(df))
    print("Class Distribution:")
    print(df[SPIKE_TARGET_COLUMN].value_counts(normalize=True))
