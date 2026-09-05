"""Account Store & Profile Registry for AI-RISK Account Investigation.

Provides:
- In-memory indexed registry of synthetic merchant accounts from data/synthetic_accounts.csv.
- Pre-registered benchmark and demo accounts (ACC_MERCHANT_90210, ACC_SYNTH_*).
- Deterministic calculation of derived features (return_rate, refund_rate, average_order_value).
- Single source of truth for account profile retrieval.
"""

import os
import csv
import logging
from typing import Dict, Any, List, Optional

from src.live_activity import get_live_activity_store

logger = logging.getLogger("ai_risk_account_store")

# Canonical benchmark profiles guaranteed to be available even if CSV is truncated
BENCHMARK_PROFILES: Dict[str, Dict[str, Any]] = {
    "ACC_MERCHANT_90210": {
        "account_id": "ACC_MERCHANT_90210",
        "account_age_days": 180,
        "order_count": 12,
        "return_count": 1,
        "refund_count": 0,
        "total_spend": 650.0,
        "average_order_value": 54.17,
        "device_count": 1,
        "ip_count": 2,
        "payment_instrument_count": 1,
        "high_value_order_count": 1,
        "suspicious_activity_score": 0.05,
        "device_type": "desktop_chrome",
        "primary_payment_method": "credit_card",
    },
    "ACC_SYNTH_LEGIT_8821": {
        "account_id": "ACC_SYNTH_LEGIT_8821",
        "account_age_days": 340,
        "order_count": 26,
        "return_count": 1,
        "refund_count": 0,
        "total_spend": 1580.0,
        "average_order_value": 60.77,
        "device_count": 1,
        "ip_count": 2,
        "payment_instrument_count": 1,
        "high_value_order_count": 2,
        "suspicious_activity_score": 0.02,
        "device_type": "desktop_chrome",
        "primary_payment_method": "credit_card",
    },
    "ACC_SYNTH_WARDROBE_4410": {
        "account_id": "ACC_SYNTH_WARDROBE_4410",
        "account_age_days": 85,
        "order_count": 18,
        "return_count": 14,
        "refund_count": 12,
        "total_spend": 2900.0,
        "average_order_value": 161.11,
        "device_count": 2,
        "ip_count": 3,
        "payment_instrument_count": 2,
        "high_value_order_count": 6,
        "suspicious_activity_score": 0.38,
        "device_type": "mobile_ios",
        "primary_payment_method": "paypal",
    },
    "ACC_SYNTH_PROMO_BOT_9104": {
        "account_id": "ACC_SYNTH_PROMO_BOT_9104",
        "account_age_days": 2,
        "order_count": 3,
        "return_count": 0,
        "refund_count": 0,
        "total_spend": 42.0,
        "average_order_value": 14.0,
        "device_count": 6,
        "ip_count": 9,
        "payment_instrument_count": 4,
        "high_value_order_count": 0,
        "suspicious_activity_score": 0.86,
        "device_type": "emulator_bot",
        "primary_payment_method": "virtual_card",
    },
    "ACC_SYNTH_HIGH_RISK_9901": {
        "account_id": "ACC_SYNTH_HIGH_RISK_9901",
        "account_age_days": 8,
        "order_count": 20,
        "return_count": 18,
        "refund_count": 17,
        "total_spend": 3200.0,
        "average_order_value": 160.0,
        "device_count": 6,
        "ip_count": 7,
        "payment_instrument_count": 5,
        "high_value_order_count": 14,
        "suspicious_activity_score": 0.96,
        "device_type": "emulator_bot",
        "primary_payment_method": "crypto_gift_card",
    },
}


def _calculate_derived_features(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate derived behavioral metrics deterministically."""
    order_count = float(data.get("order_count") or 0.0)
    return_count = float(data.get("return_count") or 0.0)
    refund_count = float(data.get("refund_count") or 0.0)
    total_spend = float(data.get("total_spend") or 0.0)

    # 1. Effective Return Rate
    if order_count > 0:
        return_rate = round(return_count / order_count, 4)
    else:
        return_rate = 0.0

    # 2. Effective Refund Rate
    if order_count > 0:
        refund_rate = round(refund_count / order_count, 4)
    else:
        refund_rate = 0.0

    # 3. Average Order Value
    if order_count > 0 and total_spend > 0:
        average_order_value = round(total_spend / order_count, 2)
    else:
        average_order_value = round(float(data.get("average_order_value") or 0.0), 2)

    result = dict(data)
    result["return_rate"] = return_rate
    result["refund_rate"] = refund_rate
    result["average_order_value"] = average_order_value
    return result


class AccountStore:
    """In-memory indexed store for merchant account profiles."""

    def __init__(self, data_path: str = os.path.join("data", "synthetic_accounts.csv")):
        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._load_accounts(data_path)

    def _load_accounts(self, data_path: str) -> None:
        """Load accounts from dataset file and benchmark profiles."""
        # 1. Load CSV data if present
        if os.path.exists(data_path):
            try:
                with open(data_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        acc_id = row.get("account_id", "").strip()
                        if not acc_id:
                            continue

                        parsed: Dict[str, Any] = {
                            "account_id": acc_id,
                            "order_count": int(float(row.get("order_count") or 0)),
                            "return_count": int(float(row.get("return_count") or 0)),
                            "refund_count": int(float(row.get("refund_count") or 0)),
                            "total_spend": round(float(row.get("total_spend") or 0.0), 2),
                            "average_order_value": round(float(row.get("average_order_value") or 0.0), 2),
                            "account_age_days": int(float(row.get("account_age_days") or 0)),
                            "device_count": int(float(row.get("device_count") or 1)),
                            "ip_count": int(float(row.get("ip_count") or 1)),
                            "payment_instrument_count": int(float(row.get("payment_instrument_count") or 1)),
                            "high_value_order_count": int(float(row.get("high_value_order_count") or 0)),
                            "suspicious_activity_score": round(float(row.get("suspicious_activity_score") or 0.0), 4),
                            "device_type": row.get("device_type") or "desktop_chrome",
                            "primary_payment_method": row.get("primary_payment_method") or "credit_card",
                        }
                        self._accounts[acc_id.upper()] = _calculate_derived_features(parsed)

                logger.info(f"Loaded {len(self._accounts)} accounts from '{data_path}'.")
            except Exception as e:
                logger.error(f"Error loading accounts from '{data_path}': {e}")
        else:
            logger.warning(f"Accounts data file '{data_path}' not found. Using benchmark profiles only.")

        # 2. Register benchmark and demo profiles (overriding or supplementing CSV)
        for key, profile in BENCHMARK_PROFILES.items():
            self._accounts[key.upper()] = _calculate_derived_features(profile)

    def get_account(self, account_id: str, include_live: bool = True) -> Optional[Dict[str, Any]]:
        """Retrieve account profile by identifier (case-insensitive).
        
        Args:
            account_id: Account identifier.
            include_live: Whether to attach live webhook activity.
        
        Returns:
            Dictionary with historical account features and separate live_activity section,
            or None if account not found.
        """
        if not account_id:
            return None
        cleaned_id = account_id.strip().upper()
        profile = self._accounts.get(cleaned_id)
        if profile is None:
            return None

        # Return shallow copy with immutable historical fields and attached live_activity
        result = dict(profile)
        if include_live:
            result["live_activity"] = get_live_activity_store().get_live_activity(cleaned_id)
        return result

    def list_sample_ids(self, limit: int = 10) -> List[str]:
        """Return sample account identifiers for analyst suggestions."""
        # Include primary benchmark accounts first, then general accounts
        priority = [
            "ACC_MERCHANT_90210",
            "ACC_WARD_00001",
            "ACC_LEGIT_STD_01502",
            "ACC_SYNTH_WARDROBE_4410",
            "ACC_SYNTH_PROMO_BOT_9104",
            "ACC_SYNTH_HIGH_RISK_9901",
        ]
        samples: List[str] = [pid for pid in priority if pid in self._accounts]
        for aid in self._accounts:
            if aid not in samples:
                samples.append(aid)
            if len(samples) >= limit:
                break
        return samples[:limit]

    def register_account(self, profile: Dict[str, Any]) -> None:
        """Register or update an account profile in the in-memory registry (for testing/simulation)."""
        acc_id = profile.get("account_id", "").strip().upper()
        if not acc_id:
            return
        self._accounts[acc_id] = _calculate_derived_features(dict(profile))

    def count(self) -> int:
        """Return total number of indexed accounts."""
        return len(self._accounts)


_account_store: Optional[AccountStore] = None


def get_account_store() -> AccountStore:
    """Retrieve or initialize the cached AccountStore singleton."""
    global _account_store
    if _account_store is None:
        _account_store = AccountStore()
    return _account_store
