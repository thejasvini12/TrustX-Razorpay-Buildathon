"""Live Abuse-Ring Attack Simulation Service.

Deterministic execution engine for development, demo, and test evaluation:
  - Scenario A: CLEAN_SHARED_INFRASTRUCTURE (Shared infrastructure alone produces LOW / NO_ACTION)
  - Scenario B: COORDINATED_SUSPICIOUS_CLUSTER (Elevated risk / POSSIBLE_RING / MONITOR)
  - Scenario C: HIGH_CONFIDENCE_ABUSE_RING (Trained model detects syndicate -> HIGH_CONFIDENCE_RING / BLOCK_ENTIRE_RING)
  - Scenario D: BYSTANDER_MIXED_CLUSTER (Core ring flagged, bystander protected as INCIDENTAL_BYSTANDER / LOW)

Strict Guarantees:
  - Zero model alterations (preserves frozen AbuseRingSentinel weights and logic).
  - No hardcoded scores or forced verdicts.
  - Passes through authentic address canonicalization, IP hashing, and deduplicated payment relationships.
  - Raw IP and raw address are never stored in graph or exposed in output.
"""

import time
import hashlib
from typing import Dict, Any, List, Optional

from src.account_store import get_account_store
from src.live_abuse_graph import get_live_abuse_graph_store
from src.abuse_ring_sentinel import get_abuse_ring_sentinel
from src.payment_context import (
    canonicalize_address,
    get_payment_context_store,
)

# Canonical Shared Test Topologies
SHARED_FACILITY_ADDRESS = "742 Evergreen Terrace, Sector 4, Springfield, IL 62704"
SHARED_LAB_DEVICE = "DEV_SHARED_LAB_001"
SHARED_OFFICE_DEVICE = "DEV_FINTECH_HUB_09"


def _hash_ip(ip_str: str) -> str:
    """Deterministic, privacy-safe IP hashing matching live graph convention."""
    digest = hashlib.sha256(f"ai_risk_salt_ip_{ip_str}".encode("utf-8")).hexdigest()[:12].upper()
    return f"IP_HASH_{digest}"


def execute_simulation_scenario(
    scenario: str,
    client_ip: str = "192.168.1.100",
) -> Dict[str, Any]:
    """Execute a deterministic live attack simulation scenario through the authentic graph & ML pipeline."""
    scenario_upper = scenario.strip().upper()
    graph_store = get_live_abuse_graph_store()
    account_store = get_account_store()
    context_store = get_payment_context_store()

    # 1. Clean reset of live graph
    graph_store.reset()

    # 2. Define Scenario Profiles & Payment Topologies
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if scenario_upper == "CLEAN_SHARED_INFRASTRUCTURE":
        # Two benign accounts sharing lab device + office IP + facility address
        accounts = [
            {
                "account_id": "ACC_MERCHANT_90210",
                "average_order_value": 54.17,
                "return_rate": 0.08,
                "return_count": 1,
                "refund_count": 0,
                "suspicious_activity_score": 0.05,
                "order_count": 12,
                "total_spend": 650.0,
                "account_age_days": 180,
            },
            {
                "account_id": "ACC_WARD_00001",
                "average_order_value": 60.00,
                "return_rate": 0.0,
                "return_count": 0,
                "refund_count": 0,
                "suspicious_activity_score": 0.04,
                "order_count": 10,
                "total_spend": 600.0,
                "account_age_days": 150,
            },
        ]
        payments = [
            {
                "account_id": "ACC_MERCHANT_90210",
                "payment_id": "pay_clean_sim_001",
                "device_id": SHARED_LAB_DEVICE,
                "address": SHARED_FACILITY_ADDRESS,
                "ip": client_ip,
                "status": "captured",
            },
            {
                "account_id": "ACC_WARD_00001",
                "payment_id": "pay_clean_sim_002",
                "device_id": SHARED_LAB_DEVICE,
                "address": SHARED_FACILITY_ADDRESS,
                "ip": client_ip,
                "status": "captured",
            },
        ]

    elif scenario_upper == "COORDINATED_SUSPICIOUS_CLUSTER":
        # 3 accounts with moderate behavioral coordination
        accounts = [
            {
                "account_id": f"ACC_COORD_SUSP_{i:02d}",
                "created_at": now_iso,
                "average_order_value": 200.0 + (i % 2) * 20,
                "return_rate": 0.40,
                "suspicious_activity_score": 0.45,
                "order_count": 10,
                "total_spend": 2000.0,
                "account_age_days": 20,
            }
            for i in range(1, 4)
        ]
        payments = [
            {
                "account_id": f"ACC_COORD_SUSP_{i:02d}",
                "payment_id": f"pay_coord_sim_{i:02d}",
                "device_id": SHARED_OFFICE_DEVICE,
                "address": SHARED_FACILITY_ADDRESS,
                "ip": client_ip,
                "status": "captured",
            }
            for i in range(1, 4)
        ]

    elif scenario_upper == "HIGH_CONFIDENCE_ABUSE_RING":
        # 5 synthetic syndicate accounts with high velocity, rapid creation, and failed payments
        accounts = [
            {
                "account_id": f"ACC_RING_SYND_{i:02d}",
                "created_at": now_iso,
                "average_order_value": 450.0,
                "return_rate": 0.82,
                "suspicious_activity_score": 0.95,
                "order_count": 22,
                "total_spend": 9900.0,
                "account_age_days": 3,
            }
            for i in range(1, 6)
        ]
        payments = []
        synd_addr = "999 Fraudster Alley, Suite 404, Cybercity, 110001"
        synd_dev = "DEV_EMULATOR_BOT_FARM"
        for i in range(1, 6):
            # 1 successful payment + 1 failed payment
            payments.append({
                "account_id": f"ACC_RING_SYND_{i:02d}",
                "payment_id": f"pay_synd_succ_{i:02d}",
                "device_id": synd_dev,
                "address": synd_addr,
                "ip": client_ip,
                "status": "captured",
            })
            payments.append({
                "account_id": f"ACC_RING_SYND_{i:02d}",
                "payment_id": f"pay_synd_fail_{i:02d}",
                "device_id": synd_dev,
                "address": synd_addr,
                "ip": client_ip,
                "status": "failed",
            })

    elif scenario_upper == "BYSTANDER_MIXED_CLUSTER":
        # 4 fraud accounts + 1 benign resident sharing building address & network, distinct device
        accounts = [
            {
                "account_id": f"ACC_RING_CORE_{i:02d}",
                "created_at": now_iso,
                "average_order_value": 450.0,
                "return_rate": 0.85,
                "suspicious_activity_score": 0.95,
                "order_count": 20,
                "total_spend": 9000.0,
            }
            for i in range(1, 5)
        ]
        accounts.append({
            "account_id": "ACC_BYSTANDER_RESIDENT",
            "created_at": now_iso,
            "average_order_value": 40.0,
            "return_rate": 0.0,
            "suspicious_activity_score": 0.02,
            "order_count": 15,
            "total_spend": 600.0,
        })

        apt_address = "Apartment 4B, 100 Oakwood Residency, Bangalore 560001"
        payments = [
            {
                "account_id": f"ACC_RING_CORE_{i:02d}",
                "payment_id": f"pay_byst_core_{i:02d}",
                "device_id": "DEV_FRAUD_PHONE_ALPHA",
                "address": apt_address,
                "ip": client_ip,
                "status": "captured",
            }
            for i in range(1, 5)
        ]
        payments.append({
            "account_id": "ACC_BYSTANDER_RESIDENT",
            "payment_id": "pay_byst_clean_01",
            "device_id": "DEV_BYSTANDER_PERSONAL_IPHONE",
            "address": apt_address,
            "ip": client_ip,
            "status": "captured",
        })
    else:
        valid_scenarios = [
            "CLEAN_SHARED_INFRASTRUCTURE",
            "COORDINATED_SUSPICIOUS_CLUSTER",
            "HIGH_CONFIDENCE_ABUSE_RING",
            "BYSTANDER_MIXED_CLUSTER",
        ]
        raise ValueError(f"Unknown scenario '{scenario}'. Valid options: {valid_scenarios}")

    # 3. Register profiles in AccountStore
    for profile in accounts:
        account_store.register_account(profile)

    # 4. Ingest payments into LiveAbuseGraphStore with canonical IP & Address hashing
    for idx, p in enumerate(payments):
        addr_hash = canonicalize_address(p.get("address")) if p.get("address") else None
        ip_hash = _hash_ip(p.get("ip")) if p.get("ip") else None
        dev_id = p.get("device_id")
        status = p.get("status", "captured")
        acc_id = p.get("account_id")
        pay_id = p.get("payment_id")

        if status == "captured":
            # Emulate authorized + captured lifecycle deduplication
            graph_store.record_webhook_event(
                event_id=f"evt_sim_{idx:03d}_auth",
                event_type="payment.authorized",
                account_id=acc_id,
                payment_id=pay_id,
                device_id=dev_id,
                ip_address=p.get("ip"),
                address_hash=addr_hash,
                status="authorized",
            )
            graph_store.record_webhook_event(
                event_id=f"evt_sim_{idx:03d}_capt",
                event_type="payment.captured",
                account_id=acc_id,
                payment_id=pay_id,
                device_id=dev_id,
                ip_address=p.get("ip"),
                address_hash=addr_hash,
                status="captured",
            )
        else:
            graph_store.record_webhook_event(
                event_id=f"evt_sim_{idx:03d}_fail",
                event_type="payment.failed",
                account_id=acc_id,
                payment_id=pay_id,
                device_id=dev_id,
                ip_address=p.get("ip"),
                address_hash=addr_hash,
                status="failed",
            )

    # 5. Export cluster to canonical AbuseRingRequest schema
    ring_request_data = graph_store.export_cluster_to_abuse_ring_request()

    # 6. Evaluate via frozen AbuseRingSentinel
    sentinel = get_abuse_ring_sentinel()
    evaluation = sentinel.detect(
        accounts=ring_request_data.get("accounts", []),
        edges=ring_request_data.get("edges", []),
        cluster_metadata=ring_request_data.get("cluster_metadata"),
    )

    clusters = graph_store.get_candidate_clusters()
    target_cluster = clusters[0] if clusters else {}

    return {
        "scenario": scenario_upper,
        "is_synthetic_simulation": True,
        "cluster_id": evaluation.get("cluster_id", "EMPTY_CLUSTER"),
        "account_count": len(evaluation.get("account_attribution", [])),
        "entity_count": len(ring_request_data.get("edges", [])),
        "shared_entities": target_cluster.get("shared_entities", []),
        "evaluation": evaluation,
        "cluster_data": ring_request_data,
    }
