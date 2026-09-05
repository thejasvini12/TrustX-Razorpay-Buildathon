"""Synthetic Account & Transaction Behavioral Data Generator for Merchant Abuse Detection.

Generates realistic behavioral profiles for legitimate users and various coordinated
abuse patterns (serial wardrobing, multi-account syndicates, promo abuse rings).
"""

import os
from typing import Optional, Tuple
import numpy as np
import pandas as pd

from src.features import ID_COLUMN, TARGET_COLUMN


def generate_synthetic_dataset(
    num_accounts: int = 5000,
    abuse_ratio: float = 0.15,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Generate a realistic, overlapping synthetic dataset for merchant abuse risk modeling.

    Simulates diverse user personas with natural behavioral overlaps:
    - Legitimate standard buyers (low returns, clean devices, long tenure)
    - Legitimate active/fashion shoppers (moderate returns, multi-device family usage, mild velocity)
    - Legitimate new/infrequent buyers (young tenure, few transactions)
    - High-velocity coordinated abuse syndicates (emulator bots, virtual cards, high fraud indicators)
    - Serial wardrobers / return abusers (high return rates, high-value baskets, sustained refunding)
    - Sophisticated / borderline low-and-slow fraudsters (moderate return rates, sleeper tenures)

    Args:
        num_accounts: Total number of synthetic accounts to generate.
        abuse_ratio: Target fraction of abusive accounts (e.g. 0.15 for 15% abuse prevalence).
        random_seed: Seed for reproducible pseudorandom number generation.

    Returns:
        pd.DataFrame containing account-level behavioral, network, and categorical features.
    """
    rng = np.random.default_rng(random_seed)

    num_abusive = int(num_accounts * abuse_ratio)
    num_legit = num_accounts - num_abusive

    records = []

    # -------------------------------------------------------------
    # 1. LEGITIMATE CUSTOMERS (target = 0)
    # -------------------------------------------------------------
    # Sub-populations:
    # 70% Standard steady customers
    # 20% Active/frequent shoppers (higher returns, multi-devices, family usage)
    # 10% Fresh/new legitimate customers (younger accounts, small order volume)
    num_legit_standard = int(num_legit * 0.70)
    num_legit_active = int(num_legit * 0.20)
    num_legit_new = num_legit - num_legit_standard - num_legit_active

    # 1a. Standard Legitimate Shoppers
    for i in range(num_legit_standard):
        acc_id = f"ACC_LEGIT_STD_{i+1:05d}"

        account_age_days = int(rng.gamma(shape=3.5, scale=110.0)) + 30
        account_age_days = min(account_age_days, 1800)

        base_orders = rng.poisson(lam=max(2.0, account_age_days / 50.0))
        order_count = max(1, int(base_orders))

        average_order_value = float(np.round(rng.normal(loc=65.0, scale=22.0), 2))
        average_order_value = max(15.0, average_order_value)

        total_spend = float(np.round(order_count * average_order_value * rng.uniform(0.92, 1.08), 2))

        # Typical low return rates (0% - 15%)
        raw_return_rate = float(rng.beta(a=1.2, b=16.0))
        return_count = int(rng.binomial(n=order_count, p=min(0.20, raw_return_rate)))
        return_rate = float(np.round(return_count / order_count, 4))

        refund_count = int(rng.binomial(n=max(1, return_count), p=0.85)) if return_count > 0 else 0
        refund_rate = float(np.round(refund_count / order_count, 4))

        p_high_val = 0.05 if average_order_value < 100 else 0.15
        high_value_order_count = int(rng.binomial(n=order_count, p=p_high_val))

        device_count = int(rng.choice([1, 2, 3], p=[0.78, 0.18, 0.04]))
        ip_count = int(rng.choice([1, 2, 3, 4], p=[0.65, 0.23, 0.10, 0.02]))
        payment_instrument_count = int(rng.choice([1, 2, 3], p=[0.75, 0.20, 0.05]))

        # Very low suspicious indicator (0.00 - 0.15)
        suspicious_activity_score = float(np.round(rng.beta(a=1.0, b=15.0), 4))

        device_type = str(rng.choice(["mobile_ios", "mobile_android", "desktop_chrome", "desktop_safari"], p=[0.42, 0.36, 0.17, 0.05]))
        primary_payment_method = str(rng.choice(["credit_card", "debit_card", "apple_pay", "paypal"], p=[0.52, 0.28, 0.12, 0.08]))

        records.append({
            ID_COLUMN: acc_id,
            "order_count": order_count,
            "return_count": return_count,
            "refund_count": refund_count,
            "total_spend": total_spend,
            "average_order_value": average_order_value,
            "account_age_days": account_age_days,
            "device_count": device_count,
            "ip_count": ip_count,
            "payment_instrument_count": payment_instrument_count,
            "return_rate": return_rate,
            "refund_rate": refund_rate,
            "high_value_order_count": high_value_order_count,
            "suspicious_activity_score": suspicious_activity_score,
            "device_type": device_type,
            "primary_payment_method": primary_payment_method,
            TARGET_COLUMN: 0,
        })

    # 1b. Active / Fashion Shoppers (Mildly elevated return rates & multi-devices, but 100% legitimate)
    for i in range(num_legit_active):
        acc_id = f"ACC_LEGIT_ACT_{i+1:05d}"

        account_age_days = int(rng.uniform(60, 900))
        order_count = int(rng.uniform(12, 55))

        average_order_value = float(np.round(rng.normal(loc=95.0, scale=30.0), 2))
        average_order_value = max(25.0, average_order_value)
        total_spend = float(np.round(order_count * average_order_value * rng.uniform(0.95, 1.05), 2))

        # Higher return rates (20% - 48%) due to clothing size try-ons
        raw_return_rate = float(rng.uniform(0.20, 0.48))
        return_count = max(1, int(order_count * raw_return_rate))
        return_rate = float(np.round(return_count / order_count, 4))

        refund_count = max(0, int(return_count * rng.uniform(0.80, 0.98)))
        refund_rate = float(np.round(refund_count / order_count, 4))

        high_value_order_count = int(rng.binomial(n=order_count, p=0.20))

        # Multiple household devices and shifting mobile IPs
        device_count = int(rng.choice([1, 2, 3, 4], p=[0.35, 0.45, 0.16, 0.04]))
        ip_count = int(rng.choice([1, 2, 3, 5], p=[0.30, 0.42, 0.22, 0.06]))
        payment_instrument_count = int(rng.choice([1, 2, 3], p=[0.45, 0.40, 0.15]))

        # Mild anomaly score overlapping with borderline threshold (0.15 - 0.42)
        suspicious_activity_score = float(np.round(rng.beta(a=2.2, b=6.5), 4))

        device_type = str(rng.choice(["mobile_ios", "desktop_chrome", "mobile_android"], p=[0.48, 0.32, 0.20]))
        primary_payment_method = str(rng.choice(["credit_card", "paypal", "debit_card", "apple_pay"], p=[0.45, 0.30, 0.15, 0.10]))

        records.append({
            ID_COLUMN: acc_id,
            "order_count": order_count,
            "return_count": return_count,
            "refund_count": refund_count,
            "total_spend": total_spend,
            "average_order_value": average_order_value,
            "account_age_days": account_age_days,
            "device_count": device_count,
            "ip_count": ip_count,
            "payment_instrument_count": payment_instrument_count,
            "return_rate": return_rate,
            "refund_rate": refund_rate,
            "high_value_order_count": high_value_order_count,
            "suspicious_activity_score": suspicious_activity_score,
            "device_type": device_type,
            "primary_payment_method": primary_payment_method,
            TARGET_COLUMN: 0,
        })

    # 1c. New / Infrequent Legitimate Buyers
    for i in range(num_legit_new):
        acc_id = f"ACC_LEGIT_NEW_{i+1:05d}"

        account_age_days = int(rng.uniform(3, 45))
        order_count = int(rng.choice([1, 2, 3, 4], p=[0.45, 0.35, 0.15, 0.05]))

        average_order_value = float(np.round(rng.normal(loc=55.0, scale=20.0), 2))
        average_order_value = max(15.0, average_order_value)
        total_spend = float(np.round(order_count * average_order_value, 2))

        # Young accounts may have 0 or 1 return
        return_count = int(rng.choice([0, 1], p=[0.80, 0.20])) if order_count > 0 else 0
        return_count = min(return_count, order_count)
        return_rate = float(np.round(return_count / order_count, 4)) if order_count > 0 else 0.0

        refund_count = return_count
        refund_rate = return_rate

        high_value_order_count = 1 if (average_order_value > 100 and order_count > 0) else 0

        device_count = int(rng.choice([1, 2], p=[0.85, 0.15]))
        ip_count = int(rng.choice([1, 2], p=[0.75, 0.25]))
        payment_instrument_count = 1

        suspicious_activity_score = float(np.round(rng.beta(a=1.5, b=9.0), 4))

        device_type = str(rng.choice(["mobile_ios", "mobile_android", "desktop_chrome"], p=[0.45, 0.40, 0.15]))
        primary_payment_method = str(rng.choice(["credit_card", "debit_card", "apple_pay"], p=[0.50, 0.35, 0.15]))

        records.append({
            ID_COLUMN: acc_id,
            "order_count": order_count,
            "return_count": return_count,
            "refund_count": refund_count,
            "total_spend": total_spend,
            "average_order_value": average_order_value,
            "account_age_days": account_age_days,
            "device_count": device_count,
            "ip_count": ip_count,
            "payment_instrument_count": payment_instrument_count,
            "return_rate": return_rate,
            "refund_rate": refund_rate,
            "high_value_order_count": high_value_order_count,
            "suspicious_activity_score": suspicious_activity_score,
            "device_type": device_type,
            "primary_payment_method": primary_payment_method,
            TARGET_COLUMN: 0,
        })

    # -------------------------------------------------------------
    # 2. ABUSIVE CUSTOMERS (target = 1)
    # -------------------------------------------------------------
    # Sub-populations:
    # 45% Severe coordinated syndicate / emulator bots (high confidence abuse)
    # 35% Serial wardrobers / return abusers (high return rates on expensive items)
    # 20% Sophisticated / low-and-slow fraudsters (moderate indicators, overlapping with borderline)
    num_abuse_syndicate = int(num_abusive * 0.45)
    num_abuse_wardrobe = int(num_abusive * 0.35)
    num_abuse_low_slow = num_abusive - num_abuse_syndicate - num_abuse_wardrobe

    # 2a. Severe Coordinated Syndicates & Bot Networks
    ring_clusters = max(1, num_abuse_syndicate // 5)
    for i in range(num_abuse_syndicate):
        cluster_id = i % ring_clusters
        acc_id = f"ACC_RING_{cluster_id:03d}_{i+1:04d}"

        account_age_days = int(rng.uniform(3, 40))
        order_count = int(rng.uniform(6, 28))

        average_order_value = float(np.round(rng.normal(loc=135.0, scale=35.0), 2))
        average_order_value = max(45.0, average_order_value)
        total_spend = float(np.round(order_count * average_order_value, 2))

        # Heavy return / refund claiming
        raw_return_rate = float(rng.uniform(0.68, 0.95))
        return_count = max(1, int(order_count * raw_return_rate))
        return_rate = float(np.round(return_count / order_count, 4))

        refund_count = max(1, int(return_count * rng.uniform(0.80, 1.0)))
        refund_rate = float(np.round(refund_count / order_count, 4))

        high_value_order_count = int(order_count * rng.uniform(0.35, 0.75))

        device_count = int(rng.choice([3, 4, 5, 7], p=[0.30, 0.35, 0.25, 0.10]))
        ip_count = int(rng.choice([3, 4, 6, 9], p=[0.25, 0.40, 0.25, 0.10]))
        payment_instrument_count = int(rng.choice([3, 4, 5, 8], p=[0.30, 0.40, 0.20, 0.10]))

        # High syndicate / velocity indicator (0.75 - 0.98)
        suspicious_activity_score = float(np.round(rng.uniform(0.72, 0.98), 4))

        device_type = str(rng.choice(["emulator_bot", "desktop_chrome", "mobile_android"], p=[0.55, 0.30, 0.15]))
        primary_payment_method = str(rng.choice(["virtual_card", "crypto_gift_card", "credit_card"], p=[0.55, 0.30, 0.15]))

        records.append({
            ID_COLUMN: acc_id,
            "order_count": order_count,
            "return_count": return_count,
            "refund_count": refund_count,
            "total_spend": total_spend,
            "average_order_value": average_order_value,
            "account_age_days": account_age_days,
            "device_count": device_count,
            "ip_count": ip_count,
            "payment_instrument_count": payment_instrument_count,
            "return_rate": return_rate,
            "refund_rate": refund_rate,
            "high_value_order_count": high_value_order_count,
            "suspicious_activity_score": suspicious_activity_score,
            "device_type": device_type,
            "primary_payment_method": primary_payment_method,
            TARGET_COLUMN: 1,
        })

    # 2b. Serial Wardrobing / High-Value Return Abusers
    for i in range(num_abuse_wardrobe):
        acc_id = f"ACC_WARD_{i+1:05d}"

        account_age_days = int(rng.uniform(30, 350))
        order_count = int(rng.uniform(15, 60))

        average_order_value = float(np.round(rng.normal(loc=175.0, scale=40.0), 2))
        average_order_value = max(70.0, average_order_value)
        total_spend = float(np.round(order_count * average_order_value * rng.uniform(0.95, 1.05), 2))

        raw_return_rate = float(rng.uniform(0.60, 0.90))
        return_count = max(1, int(order_count * raw_return_rate))
        return_rate = float(np.round(return_count / order_count, 4))

        refund_count = max(1, int(return_count * rng.uniform(0.85, 1.0)))
        refund_rate = float(np.round(refund_count / order_count, 4))

        high_value_order_count = max(1, int(order_count * rng.uniform(0.40, 0.80)))

        device_count = int(rng.choice([1, 2, 3], p=[0.45, 0.45, 0.10]))
        ip_count = int(rng.choice([1, 2, 3, 4], p=[0.35, 0.45, 0.15, 0.05]))
        payment_instrument_count = int(rng.choice([1, 2, 3, 4], p=[0.35, 0.40, 0.15, 0.10]))

        suspicious_activity_score = float(np.round(rng.uniform(0.52, 0.82), 4))

        device_type = str(rng.choice(["mobile_ios", "desktop_chrome", "mobile_android"], p=[0.45, 0.35, 0.20]))
        primary_payment_method = str(rng.choice(["credit_card", "paypal", "virtual_card"], p=[0.55, 0.30, 0.15]))

        records.append({
            ID_COLUMN: acc_id,
            "order_count": order_count,
            "return_count": return_count,
            "refund_count": refund_count,
            "total_spend": total_spend,
            "average_order_value": average_order_value,
            "account_age_days": account_age_days,
            "device_count": device_count,
            "ip_count": ip_count,
            "payment_instrument_count": payment_instrument_count,
            "return_rate": return_rate,
            "refund_rate": refund_rate,
            "high_value_order_count": high_value_order_count,
            "suspicious_activity_score": suspicious_activity_score,
            "device_type": device_type,
            "primary_payment_method": primary_payment_method,
            TARGET_COLUMN: 1,
        })

    # 2c. Sophisticated / Low-and-Slow Borderline Abusers (Evading obvious velocity signals)
    for i in range(num_abuse_low_slow):
        acc_id = f"ACC_SLOW_{i+1:05d}"

        # Older seasoned account age to blend with legit customers
        account_age_days = int(rng.uniform(45, 220))
        order_count = int(rng.uniform(6, 22))

        average_order_value = float(np.round(rng.normal(loc=90.0, scale=25.0), 2))
        average_order_value = max(35.0, average_order_value)
        total_spend = float(np.round(order_count * average_order_value, 2))

        # Moderate return rates (35% - 55%) that create realistic overlap with heavy legitimate returners
        raw_return_rate = float(rng.uniform(0.35, 0.58))
        return_count = max(1, int(order_count * raw_return_rate))
        return_rate = float(np.round(return_count / order_count, 4))

        refund_count = max(1, int(return_count * rng.uniform(0.75, 0.95)))
        refund_rate = float(np.round(refund_count / order_count, 4))

        high_value_order_count = int(order_count * rng.uniform(0.15, 0.40))

        # Ordinary hardware/IP count
        device_count = int(rng.choice([1, 2, 3], p=[0.40, 0.45, 0.15]))
        ip_count = int(rng.choice([1, 2, 3, 4], p=[0.35, 0.45, 0.15, 0.05]))
        payment_instrument_count = int(rng.choice([1, 2, 3], p=[0.45, 0.40, 0.15]))

        # Moderate suspicious activity indicator in the overlapping 0.35 - 0.65 band
        suspicious_activity_score = float(np.round(rng.beta(a=4.5, b=4.5), 4))

        device_type = str(rng.choice(["mobile_ios", "desktop_chrome", "mobile_android"], p=[0.40, 0.35, 0.25]))
        primary_payment_method = str(rng.choice(["credit_card", "paypal", "virtual_card", "debit_card"], p=[0.45, 0.30, 0.15, 0.10]))

        records.append({
            ID_COLUMN: acc_id,
            "order_count": order_count,
            "return_count": return_count,
            "refund_count": refund_count,
            "total_spend": total_spend,
            "average_order_value": average_order_value,
            "account_age_days": account_age_days,
            "device_count": device_count,
            "ip_count": ip_count,
            "payment_instrument_count": payment_instrument_count,
            "return_rate": return_rate,
            "refund_rate": refund_rate,
            "high_value_order_count": high_value_order_count,
            "suspicious_activity_score": suspicious_activity_score,
            "device_type": device_type,
            "primary_payment_method": primary_payment_method,
            TARGET_COLUMN: 1,
        })

    df = pd.DataFrame(records)
    df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
    return df


def save_dataset(df: pd.DataFrame, output_path: str) -> str:
    """Save dataframe to specified CSV path, ensuring parent directories exist."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
