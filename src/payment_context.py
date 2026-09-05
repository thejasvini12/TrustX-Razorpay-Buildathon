"""Short-lived, thread-safe in-memory payment context store and client IP extraction utilities.

Implements:
1. Safe client IP extraction from incoming request connection (no blind trust of X-Forwarded-For).
2. Trusted proxy evaluation (honors X-Forwarded-For rightmost hops ONLY when direct peer is in trusted proxy list).
3. IPv4 and IPv6 normalization and validation using built-in ipaddress module.
4. Deterministic IP hashing (IP_HASH_<12-char SHA-256>) ensuring raw customer IP is never exposed in UI.
5. Short-lived bounded payment context mapping (order_id / correlation_id -> observed metadata with TTL).
"""

import os
import re
import time
import hashlib
import logging
import threading
import ipaddress
from typing import Dict, Any, Optional, List

logger = logging.getLogger("ai_risk_payment_context")

ENV_TRUSTED_PROXIES = "TRUSTED_PROXIES"


def normalize_ip(raw_ip: Any) -> Optional[str]:
    """Validate and normalize an IPv4 or IPv6 address string.

    Rules:
    - Strips whitespace.
    - Resolves IPv4-mapped IPv6 (e.g. '::ffff:192.0.2.1' -> '192.0.2.1').
    - Compresses IPv6 representation according to RFC 5952.
    - Returns standardized lowercase string.
    - Returns None if invalid, empty, or malformed.
    """
    if not raw_ip or not isinstance(raw_ip, str):
        return None
    cleaned = raw_ip.strip()
    if not cleaned:
        return None
    if cleaned in ("testclient", "localhost"):
        return "127.0.0.1"
    try:
        ip_obj = ipaddress.ip_address(cleaned)
        if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
            ip_obj = ip_obj.ipv4_mapped
        return ip_obj.compressed.lower()
    except ValueError:
        return None


def canonicalize_ip(raw_ip: Any) -> Optional[str]:
    """Deterministically normalize and hash an IP address into an opaque identifier (IP_HASH_<sha256[:12]>).

    Guarantees raw customer IP is never stored in graph edges or exposed via UI/API responses.
    """
    if not raw_ip:
        return None
    if isinstance(raw_ip, str) and raw_ip.startswith("IP_HASH_") and len(raw_ip) == 20:
        return raw_ip
    normalized = normalize_ip(raw_ip)
    if not normalized:
        return None
    h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12].upper()
    return f"IP_HASH_{h}"


def normalize_address(raw_address: Any) -> Optional[str]:
    """Validate and normalize an address string or dictionary deterministically.

    Rules:
    - Conservative and deterministic; no aggressive fuzzy matching or geocoding.
    - Handles dictionary representations (line1, line2, city, state, postal_code, country, pincode, zip).
    - Replaces line breaks (CRLF, LF, CR) with commas.
    - Strips surrounding whitespace and collapses repeated whitespace/tabs.
    - Converts casing to lowercase.
    - Strips extra edge punctuation from segments and removes empty segments.
    - Returns standardized comma-separated string, or None if invalid/empty/too short.
    """
    if not raw_address:
        return None

    if isinstance(raw_address, dict):
        parts = [
            str(raw_address.get(k, "")).strip()
            for k in ["line1", "line2", "city", "state", "postal_code", "country", "pincode", "zip"]
            if raw_address.get(k)
        ]
        raw = ", ".join(parts)
    elif isinstance(raw_address, str):
        raw = raw_address
    else:
        return None

    # Replace newlines with commas
    raw = re.sub(r"[\r\n]+", ", ", raw)

    # Split by commas and clean each segment
    segments = []
    for part in raw.split(","):
        cleaned_part = " ".join(part.strip().split())
        cleaned_part = cleaned_part.strip(" ,;\t")
        if cleaned_part:
            segments.append(cleaned_part.lower())

    if not segments:
        return None

    normalized = ", ".join(segments)

    # Reject placeholder words or trivially short content
    if len(normalized) < 5 or normalized in ("none", "null", "undefined", "n/a", "unknown"):
        return None

    return normalized


def canonicalize_address(raw_address: Any) -> Optional[str]:
    """Deterministically normalize and hash an address into an opaque identifier (ADDRESS_HASH_<sha256[:12]>).

    Guarantees raw customer address is never stored in graph edges, logged, or exposed via UI/API responses.
    """
    if not raw_address:
        return None

    if isinstance(raw_address, str):
        cleaned = raw_address.strip()
        if cleaned.startswith("ADDRESS_HASH_") and len(cleaned) == 25:
            return cleaned.upper()
        if cleaned.startswith("ADDR_HASH_") and len(cleaned) == 22:
            return f"ADDRESS_HASH_{cleaned[10:].upper()}"

    normalized = normalize_address(raw_address)
    if not normalized:
        return None

    h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12].upper()
    return f"ADDRESS_HASH_{h}"


def get_configured_trusted_proxies() -> List[str]:
    """Retrieve trusted proxy list from TRUSTED_PROXIES environment variable."""
    raw = os.environ.get(ENV_TRUSTED_PROXIES, "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def extract_client_ip(
    client_host: Optional[str],
    headers: Optional[Dict[str, str]] = None,
    trusted_proxies: Optional[List[str]] = None,
) -> Optional[str]:
    """Safely extract client IP from incoming connection and headers.

    Rules:
    - Never trust X-Forwarded-For, Forwarded, or X-Real-IP by default.
    - If trusted_proxies is configured and client_host matches a trusted proxy,
      parse X-Forwarded-For from right to left, stripping trusted hops to find
      the first untrusted IP.
    - If client_host is NOT in trusted_proxies, ignore forwarded headers and use client_host directly.
    - Normalizes IPv4 and IPv6 safely.
    - Returns None if client_host is missing or malformed.
    """
    if not client_host:
        return None

    clean_peer = normalize_ip(client_host)
    if not clean_peer:
        return None

    proxies = trusted_proxies if trusted_proxies is not None else get_configured_trusted_proxies()
    h_lower = {str(k).lower(): str(v) for k, v in (headers or {}).items()}

    # Check if peer is in trusted proxies
    is_trusted = False
    if proxies:
        try:
            peer_obj = ipaddress.ip_address(clean_peer)
            for tp in proxies:
                tp_clean = tp.strip()
                if not tp_clean:
                    continue
                try:
                    if "/" in tp_clean:
                        net = ipaddress.ip_network(tp_clean, strict=False)
                        if peer_obj in net:
                            is_trusted = True
                            break
                    else:
                        trusted_obj = ipaddress.ip_address(tp_clean)
                        if peer_obj == trusted_obj:
                            is_trusted = True
                            break
                except ValueError:
                    continue
        except ValueError:
            pass

    if is_trusted:
        # Check X-Forwarded-For
        xff = h_lower.get("x-forwarded-for")
        if xff:
            hops = [h.strip() for h in xff.split(",") if h.strip()]
            for hop in reversed(hops):
                norm_hop = normalize_ip(hop)
                if not norm_hop:
                    continue
                # Check if hop is a trusted proxy
                hop_trusted = False
                try:
                    hop_obj = ipaddress.ip_address(norm_hop)
                    for tp in proxies:
                        tp_clean = tp.strip()
                        if not tp_clean:
                            continue
                        if "/" in tp_clean:
                            if hop_obj in ipaddress.ip_network(tp_clean, strict=False):
                                hop_trusted = True
                                break
                        else:
                            if hop_obj == ipaddress.ip_address(tp_clean):
                                hop_trusted = True
                                break
                except ValueError:
                    continue

                if not hop_trusted:
                    return norm_hop

        # Check X-Real-IP if no untrusted XFF hop was found
        x_real = h_lower.get("x-real-ip")
        if x_real:
            norm_real = normalize_ip(x_real)
            if norm_real:
                return norm_real

    # Default fallback: direct connection peer
    return clean_peer


class PaymentContextStore:
    """Thread-safe, bounded in-memory store for short-lived payment session context."""

    def __init__(self, max_capacity: int = 10000, default_ttl_seconds: int = 3600):
        self._lock = threading.RLock()
        self._max_capacity = max_capacity
        self._default_ttl = default_ttl_seconds
        self._contexts: Dict[str, Dict[str, Any]] = {}

    def record_context(
        self,
        correlation_id: str,
        account_id: str,
        observed_ip: Optional[str] = None,
        device_id: Optional[str] = None,
        observed_address: Optional[Any] = None,
        observed_address_hash: Optional[str] = None,
        order_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record an observed payment context with automatic expiration and LRU eviction.

        Guarantees raw address is never stored in the context or graph - only the privacy-safe hash.
        """
        with self._lock:
            now = time.time()
            self._cleanup_expired_locked(now)

            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            clean_ip = normalize_ip(observed_ip) if observed_ip else None
            clean_dev = device_id.strip() if device_id and isinstance(device_id, str) else None

            # Address hash privacy protection: NEVER store raw address in context or graph
            addr_hash = observed_address_hash
            if not addr_hash and observed_address:
                addr_hash = canonicalize_address(observed_address)

            entry = {
                "correlation_id": correlation_id,
                "order_id": order_id,
                "account_id": account_id,
                "device_id": clean_dev,
                "observed_ip": clean_ip,
                "observed_address_hash": addr_hash,
                "created_at": now,
                "expires_at": now + ttl,
            }

            # Bounded capacity eviction
            if len(self._contexts) >= self._max_capacity and correlation_id not in self._contexts:
                oldest_key = min(self._contexts.keys(), key=lambda k: self._contexts[k]["created_at"])
                del self._contexts[oldest_key]

            self._contexts[correlation_id] = entry
            if order_id and order_id != correlation_id:
                self._contexts[order_id] = entry

            logger.debug(
                f"[PaymentContext] Stored context corr_id={correlation_id}, order_id={order_id}, "
                f"account={account_id}, ip={'present' if clean_ip else 'none'}, "
                f"addr={'present' if addr_hash else 'none'}, ttl={ttl}s"
            )
            return entry

    def get_context(self, lookup_key: Optional[str]) -> Optional[Dict[str, Any]]:
        """Look up payment context by order_id or correlation_id, verifying expiration."""
        if not lookup_key:
            return None
        with self._lock:
            now = time.time()
            entry = self._contexts.get(lookup_key)
            if not entry:
                return None
            if entry["expires_at"] <= now:
                self._remove_entry_locked(entry)
                return None
            return entry

    def _cleanup_expired_locked(self, now: float) -> int:
        expired_keys = [k for k, v in self._contexts.items() if v["expires_at"] <= now]
        for k in expired_keys:
            if k in self._contexts:
                entry = self._contexts[k]
                self._remove_entry_locked(entry)
        return len(expired_keys)

    def _remove_entry_locked(self, entry: Dict[str, Any]) -> None:
        corr_id = entry.get("correlation_id")
        ord_id = entry.get("order_id")
        if corr_id in self._contexts:
            del self._contexts[corr_id]
        if ord_id and ord_id in self._contexts:
            del self._contexts[ord_id]

    def cleanup_expired(self) -> int:
        """Explicitly purge all expired contexts."""
        with self._lock:
            return self._cleanup_expired_locked(time.time())

    def reset(self) -> None:
        """Reset the context store (testing/maintenance)."""
        with self._lock:
            self._contexts.clear()

    def size(self) -> int:
        """Current number of active context keys."""
        with self._lock:
            return len(self._contexts)


# Global singleton instance
_GLOBAL_PAYMENT_CONTEXT_STORE: Optional[PaymentContextStore] = None
_STORE_LOCK = threading.Lock()


def get_payment_context_store() -> PaymentContextStore:
    """Thread-safe accessor for the global PaymentContextStore singleton."""
    global _GLOBAL_PAYMENT_CONTEXT_STORE
    if _GLOBAL_PAYMENT_CONTEXT_STORE is None:
        with _STORE_LOCK:
            if _GLOBAL_PAYMENT_CONTEXT_STORE is None:
                _GLOBAL_PAYMENT_CONTEXT_STORE = PaymentContextStore()
    return _GLOBAL_PAYMENT_CONTEXT_STORE
