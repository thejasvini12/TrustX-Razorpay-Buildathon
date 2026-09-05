"""Thread-safe in-memory store for real-time Account Live Activity derived from Razorpay webhooks.

Tracks genuine webhook-derived telemetry per account:
- payment_count: Count of unique successfully captured payments.
- failed_payment_count: Count of unique failed payments.
- payment_volume: Total monetary volume of captured payments.
- last_payment_at: Timestamp of the latest payment event.
- webhook_event_count: Total count of accepted non-duplicate webhook events.
- recent_events: Bounded list (last 20) of event summaries.

Lifecycle & Deduplication Guarantees:
- payment.captured is canonical; authorized + captured counts as exactly one successful payment.
- Duplicate webhooks (same event_id or duplicate captured event) do not increase counts or volume.
- In-memory only for this phase; resets on backend restart.
- Keeps live activity strictly isolated from historical metrics.
"""

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set


class AccountLiveActivityStore:
    """Thread-safe bounded in-memory store tracking real-time account payment activity."""

    def __init__(self, max_recent_events_per_account: int = 20):
        self._lock = threading.Lock()
        self._max_recent = max_recent_events_per_account
        # Map: account_id (str.upper) -> internal state dict
        self._store: Dict[str, Dict[str, Any]] = {}

    def _get_or_create_state(self, account_id: str) -> Dict[str, Any]:
        """Retrieve or initialize account live activity internal state (must be called with lock held)."""
        key = account_id.strip().upper()
        if key not in self._store:
            self._store[key] = {
                "account_id": key,
                "successful_payment_ids": set(),  # Set[str] of captured payment_ids
                "failed_payment_ids": set(),      # Set[str] of failed payment_ids
                "seen_event_ids": set(),          # Set[str] of processed webhook event_ids
                "payment_volume": 0.0,
                "last_payment_at": None,
                "webhook_event_count": 0,
                "recent_events": deque(maxlen=self._max_recent),
                "association_sources": set(),     # Set[str] tracking how payments were associated
            }
        return self._store[key]

    def record_webhook_payment(
        self,
        account_id: str,
        event_id: str,
        event_type: str,
        payment_id: Optional[str],
        amount: Optional[float],
        currency: str = "INR",
        status: str = "unknown",
        association_source: str = "notes",
        timestamp: Optional[str] = None,
    ) -> bool:
        """Record an accepted, non-duplicate Razorpay webhook payment event.

        Args:
            account_id: Target account identifier.
            event_id: Unique webhook event ID.
            event_type: e.g. payment.captured, payment.authorized, payment.failed.
            payment_id: Razorpay payment identifier (pay_xxxx).
            amount: Payment amount in major currency units.
            currency: Three-letter currency code.
            status: Razorpay payment status string.
            association_source: Association method ('notes', 'header_dev_test', 'test_mode_default').
            timestamp: ISO 8601 or unix timestamp string.

        Returns:
            bool: True if live activity was updated, False if duplicate event_id was ignored.
        """
        if not account_id:
            return False

        now_iso = timestamp or datetime.now(timezone.utc).isoformat()
        clean_payment_id = payment_id.strip() if payment_id else None
        valid_amount = max(0.0, float(amount)) if amount is not None else 0.0

        with self._lock:
            state = self._get_or_create_state(account_id)

            # 1. Deduplicate by webhook event_id
            if event_id and event_id in state["seen_event_ids"]:
                return False

            if event_id:
                state["seen_event_ids"].add(event_id)

            state["webhook_event_count"] += 1
            state["last_payment_at"] = now_iso
            state["association_sources"].add(association_source)

            # 2. Canonical Lifecycle Handling
            # payment.captured is canonical completed payment
            if event_type == "payment.captured" or status == "captured":
                if clean_payment_id:
                    if clean_payment_id not in state["successful_payment_ids"]:
                        state["successful_payment_ids"].add(clean_payment_id)
                        state["payment_volume"] = round(state["payment_volume"] + valid_amount, 2)
                else:
                    state["payment_volume"] = round(state["payment_volume"] + valid_amount, 2)

            elif event_type == "payment.failed" or status == "failed":
                if clean_payment_id:
                    state["failed_payment_ids"].add(clean_payment_id)

            elif event_type == "payment.authorized" or status == "authorized":
                # Tracks authorization, but does NOT increment successful payment count or volume
                pass

            # 3. Append to recent events
            event_summary = {
                "event_id": event_id,
                "event_type": event_type,
                "payment_id": clean_payment_id,
                "amount": valid_amount if (amount is not None) else None,
                "currency": currency,
                "status": status,
                "timestamp": now_iso,
                "association_source": association_source,
            }
            state["recent_events"].appendleft(event_summary)
            return True

    def get_live_activity(self, account_id: str) -> Dict[str, Any]:
        """Retrieve live activity for an account, returning default zeroes if no live events exist."""
        if not account_id:
            return self._empty_activity("UNKNOWN")

        key = account_id.strip().upper()
        with self._lock:
            if key not in self._store:
                return self._empty_activity(key)

            state = self._store[key]
            return {
                "account_id": key,
                "payment_count": len(state["successful_payment_ids"]),
                "failed_payment_count": len(state["failed_payment_ids"]),
                "payment_volume": round(state["payment_volume"], 2),
                "last_payment_at": state["last_payment_at"],
                "webhook_event_count": state["webhook_event_count"],
                "recent_events": list(state["recent_events"]),
                "association_sources": list(state["association_sources"]),
            }

    def _empty_activity(self, account_id: str) -> Dict[str, Any]:
        """Return standardized zero-state live activity object."""
        return {
            "account_id": account_id,
            "payment_count": 0,
            "failed_payment_count": 0,
            "payment_volume": 0.0,
            "last_payment_at": None,
            "webhook_event_count": 0,
            "recent_events": [],
            "association_sources": [],
        }

    def reset(self) -> None:
        """Clear all in-memory live activity."""
        with self._lock:
            self._store.clear()


# Global Singleton Store
_live_activity_store: Optional[AccountLiveActivityStore] = None


def get_live_activity_store() -> AccountLiveActivityStore:
    """Retrieve or initialize the global AccountLiveActivityStore singleton."""
    global _live_activity_store
    if _live_activity_store is None:
        _live_activity_store = AccountLiveActivityStore()
    return _live_activity_store
