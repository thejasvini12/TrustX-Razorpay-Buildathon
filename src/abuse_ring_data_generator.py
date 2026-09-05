"""Synthetic Graph & Identity Network Data Generator for Abuse-Ring Sentinel.

Generates realistic relational entity-linkage datasets:
1. data/ring_accounts.csv: Account attributes linked to cluster_id.
2. data/ring_entity_edges.csv: Bipartite interaction event log (Devices, IPs, Cards, Addresses).
3. data/ring_clusters.csv: Ground-truth connected component records.
4. data/ring_account_network_features.csv: Graph topological and behavioral coordination features.

Models both:
- Positive Abuse Rings (Synthetic Identity, Card Testing, Promo Farming, Wardrobing Mule).
- Benign Hard Negatives (Campus IP, Coworking Wi-Fi, Family Household, Apartment Building, Public Kiosk, Partial Overlap).
- Out-of-Distribution Stress Topologies (Star, Daisy-Chain, Slow-Drip Rings).
- Clean Solo Accounts.
"""

import os
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Set
import numpy as np
import pandas as pd


CLUSTER_TYPES_ABUSE: List[str] = [
    "SYNTHETIC_IDENTITY_RING",
    "CARD_TESTING_SYNDICATE",
    "PROMO_FARMING_RING",
    "WARDROBING_MULE_CLUSTER",
    "SLOW_DRIP_COORDINATED_RING",
]

CLUSTER_TYPES_BENIGN: List[str] = [
    "CAMPUS_SHARED_IP",
    "COWORKING_PUBLIC_WIFI",
    "FAMILY_HOUSEHOLD",
    "APARTMENT_BUILDING_ADDR",
    "PUBLIC_KIOSK_DEVICE",
    "PARTIAL_NETWORK_OVERLAP",
    "STAR_TOPOLOGY_BENIGN",
    "SINGLETON_CLEAN",
]


def generate_abuse_ring_dataset(
    target_account_count: int = 5000,
    random_seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate normalized relational identity graph datasets and computed network features."""
    rng = np.random.default_rng(random_seed)
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    clusters_records: List[Dict[str, Any]] = []
    accounts_records: List[Dict[str, Any]] = []
    edges_records: List[Dict[str, Any]] = []

    account_counter = 1
    edge_counter = 1
    cluster_counter = 1
    device_counter = 1
    ip_counter = 1
    card_counter = 1
    addr_counter = 1

    # Scenarios distribution plan:
    # ~20% Positive Ring accounts
    # ~40% Benign Hard-Negative accounts (Campus, Coworking, Family, Apartment, Kiosk)
    # ~40% Clean Solo / Small accounts
    
    current_acc_count = 0

    while current_acc_count < target_account_count:
        # Select archetype
        roll = rng.random()
        if roll < 0.08:
            archetype = "SYNTHETIC_IDENTITY_RING"
            is_abuse = 1
            cluster_size = rng.integers(12, 26)
        elif roll < 0.14:
            archetype = "CARD_TESTING_SYNDICATE"
            is_abuse = 1
            cluster_size = rng.integers(20, 36)
        elif roll < 0.19:
            archetype = "PROMO_FARMING_RING"
            is_abuse = 1
            cluster_size = rng.integers(10, 22)
        elif roll < 0.23:
            archetype = "WARDROBING_MULE_CLUSTER"
            is_abuse = 1
            cluster_size = rng.integers(8, 16)
        elif roll < 0.25:
            archetype = "SLOW_DRIP_COORDINATED_RING"
            is_abuse = 1
            cluster_size = rng.integers(10, 18)
        elif roll < 0.35:
            archetype = "CAMPUS_SHARED_IP"
            is_abuse = 0
            cluster_size = rng.integers(30, 65)
        elif roll < 0.44:
            archetype = "COWORKING_PUBLIC_WIFI"
            is_abuse = 0
            cluster_size = rng.integers(20, 45)
        elif roll < 0.54:
            archetype = "FAMILY_HOUSEHOLD"
            is_abuse = 0
            cluster_size = rng.integers(2, 5)
        elif roll < 0.62:
            archetype = "APARTMENT_BUILDING_ADDR"
            is_abuse = 0
            cluster_size = rng.integers(15, 30)
        elif roll < 0.68:
            archetype = "PUBLIC_KIOSK_DEVICE"
            is_abuse = 0
            cluster_size = rng.integers(10, 20)
        elif roll < 0.73:
            archetype = "PARTIAL_NETWORK_OVERLAP"
            is_abuse = 0
            cluster_size = rng.integers(4, 10)
        elif roll < 0.77:
            archetype = "STAR_TOPOLOGY_BENIGN"
            is_abuse = 0
            cluster_size = rng.integers(12, 25)
        else:
            archetype = "SINGLETON_CLEAN"
            is_abuse = 0
            cluster_size = 1

        cluster_id = f"RING_{cluster_counter:05d}"
        cluster_counter += 1

        cluster_created_base = base_time + timedelta(days=int(rng.integers(0, 180)))
        cluster_acc_ids = []
        cluster_devices: Set[str] = set()
        cluster_ips: Set[str] = set()
        cluster_cards: Set[str] = set()
        cluster_addrs: Set[str] = set()

        # Generate accounts and specific network structures for this archetype
        if archetype == "SYNTHETIC_IDENTITY_RING":
            # 1-2 shared emulator devices, 1 shared drop address, pool of virtual cards and proxies
            dev_pool = [f"DEV_EMUL_{device_counter + k:06d}" for k in range(rng.integers(1, 3))]
            device_counter += len(dev_pool)
            addr_pool = [f"ADDR_DROP_{addr_counter:06d}"]
            addr_counter += 1
            ip_pool = [f"IP_PROXY_{ip_counter + k:06d}" for k in range(rng.integers(3, 7))]
            ip_counter += len(ip_pool)
            
            # Burst creation within 2 hours
            time_deltas = [timedelta(minutes=float(rng.uniform(0, 120))) for _ in range(cluster_size)]

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + time_deltas[i]
                card = f"CARD_VIRTUAL_{card_counter:06d}"
                card_counter += 1
                dev = str(rng.choice(dev_pool))
                ip = str(rng.choice(ip_pool))
                addr = addr_pool[0]

                cluster_devices.add(dev)
                cluster_ips.add(ip)
                cluster_cards.add(card)
                cluster_addrs.add(addr)

                order_cnt = int(rng.integers(8, 25))
                ret_cnt = int(rng.integers(2, 6))
                ref_cnt = int(rng.integers(2, 5))
                aov = float(np.round(rng.uniform(85.0, 190.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": ret_cnt,
                    "refund_count": ref_cnt,
                    "return_rate": round(ret_cnt / order_cnt, 4),
                    "refund_rate": round(ref_cnt / order_cnt, 4),
                    "high_value_order_count": int(rng.integers(2, 7)),
                    "suspicious_activity_score": round(float(rng.uniform(0.72, 0.95)), 4),
                    "device_type": "emulator_bot",
                    "primary_payment_method": "virtual_card",
                })

                for etype, eid in [("DEVICE", dev), ("IP", ip), ("PAYMENT", card), ("ADDRESS", addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(days=int(rng.integers(1, 10)))).isoformat(),
                        "interaction_count": int(rng.integers(5, 30)),
                        "event_type": "CHECKOUT" if etype == "PAYMENT" else "LOGIN",
                    })
                    edge_counter += 1

        elif archetype == "CARD_TESTING_SYNDICATE":
            # 1 device farm ID, 1 proxy subnet, rapid low AOV orders, high card churn
            dev = f"DEV_FARM_{device_counter:06d}"
            device_counter += 1
            ip = f"IP_PROXYNET_{ip_counter:06d}"
            ip_counter += 1
            cluster_devices.add(dev)
            cluster_ips.add(ip)

            time_deltas = [timedelta(minutes=float(rng.uniform(0, 45))) for _ in range(cluster_size)]

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + time_deltas[i]
                card = f"CARD_STOLEN_{card_counter:06d}"
                card_counter += 1
                addr = f"ADDR_MULE_{addr_counter + (i % 3):06d}"
                if (i % 3) == 0:
                    addr_counter += 1

                cluster_cards.add(card)
                cluster_addrs.add(addr)

                order_cnt = int(rng.integers(15, 45))
                aov = float(np.round(rng.uniform(4.0, 18.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": 0,
                    "refund_count": 0,
                    "return_rate": 0.0,
                    "refund_rate": 0.0,
                    "high_value_order_count": 0,
                    "suspicious_activity_score": round(float(rng.uniform(0.80, 0.98)), 4),
                    "device_type": "emulator_bot",
                    "primary_payment_method": "credit_card",
                })

                for etype, eid in [("DEVICE", dev), ("IP", ip), ("PAYMENT", card), ("ADDRESS", addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(hours=int(rng.integers(1, 6)))).isoformat(),
                        "interaction_count": int(rng.integers(10, 50)),
                        "event_type": "CHECKOUT",
                    })
                    edge_counter += 1

        elif archetype == "PROMO_FARMING_RING":
            # Shared device, shared single payment method, identical basket value, 1 order per account
            dev = f"DEV_BOT_{device_counter:06d}"
            device_counter += 1
            card = f"CARD_FARMER_{card_counter:06d}"
            card_counter += 1
            ip = f"IP_SUBNET_{ip_counter:06d}"
            ip_counter += 1
            addr = f"ADDR_FARM_{addr_counter:06d}"
            addr_counter += 1

            cluster_devices.add(dev)
            cluster_cards.add(card)
            cluster_ips.add(ip)
            cluster_addrs.add(addr)

            time_deltas = [timedelta(minutes=float(rng.uniform(0, 25))) for _ in range(cluster_size)]

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + time_deltas[i]
                aov = float(np.round(rng.uniform(49.0, 52.0), 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": 1,
                    "total_spend": aov,
                    "average_order_value": aov,
                    "return_count": 0,
                    "refund_count": 0,
                    "return_rate": 0.0,
                    "refund_rate": 0.0,
                    "high_value_order_count": 0,
                    "suspicious_activity_score": round(float(rng.uniform(0.75, 0.92)), 4),
                    "device_type": "desktop_chrome",
                    "primary_payment_method": "virtual_card",
                })

                for etype, eid in [("DEVICE", dev), ("IP", ip), ("PAYMENT", card), ("ADDRESS", addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": created_at.isoformat(),
                        "interaction_count": 1,
                        "event_type": "CHECKOUT",
                    })
                    edge_counter += 1

        elif archetype == "WARDROBING_MULE_CLUSTER":
            # Shared commercial freight forwarding hub address, very high returns (>85%), high spend
            addr = f"ADDR_COMMERCIAL_HUB_{addr_counter:06d}"
            addr_counter += 1
            cluster_addrs.add(addr)

            time_deltas = [timedelta(days=float(rng.uniform(0, 20))) for _ in range(cluster_size)]

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + time_deltas[i]
                dev = f"DEV_PHONE_{device_counter:06d}"
                device_counter += 1
                ip = f"IP_MULE_{ip_counter:06d}"
                ip_counter += 1
                card = f"CARD_LUXURY_{card_counter:06d}"
                card_counter += 1

                cluster_devices.add(dev)
                cluster_ips.add(ip)
                cluster_cards.add(card)

                order_cnt = int(rng.integers(18, 35))
                ret_cnt = int(order_cnt * rng.uniform(0.85, 0.95))
                ref_cnt = int(ret_cnt * rng.uniform(0.90, 1.0))
                aov = float(np.round(rng.uniform(220.0, 480.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": ret_cnt,
                    "refund_count": ref_cnt,
                    "return_rate": round(ret_cnt / order_cnt, 4),
                    "refund_rate": round(ref_cnt / order_cnt, 4),
                    "high_value_order_count": int(rng.integers(10, 22)),
                    "suspicious_activity_score": round(float(rng.uniform(0.68, 0.88)), 4),
                    "device_type": "desktop_chrome",
                    "primary_payment_method": "credit_card",
                })

                for etype, eid in [("DEVICE", dev), ("IP", ip), ("PAYMENT", card), ("ADDRESS", addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(days=int(rng.integers(15, 60)))).isoformat(),
                        "interaction_count": int(rng.integers(10, 40)),
                        "event_type": "REFUND_REQUEST" if etype == "ADDRESS" else "CHECKOUT",
                    })
                    edge_counter += 1

        elif archetype == "SLOW_DRIP_COORDINATED_RING":
            # Coordinated ring created slowly over 6 months to evade time-burst detection
            dev_pool = [f"DEV_SLOW_{device_counter + k:06d}" for k in range(2)]
            device_counter += 2
            card_pool = [f"CARD_SLOW_{card_counter + k:06d}" for k in range(3)]
            card_counter += 3
            addr = f"ADDR_SLOW_{addr_counter:06d}"
            addr_counter += 1

            for dev in dev_pool:
                cluster_devices.add(dev)
            for card in card_pool:
                cluster_cards.add(card)
            cluster_addrs.add(addr)

            time_deltas = [timedelta(days=float(rng.uniform(0, 180))) for _ in range(cluster_size)]

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + time_deltas[i]
                dev = str(rng.choice(dev_pool))
                card = str(rng.choice(card_pool))
                ip = f"IP_SLOW_{ip_counter:06d}"
                ip_counter += 1
                cluster_ips.add(ip)

                order_cnt = int(rng.integers(10, 25))
                ret_cnt = int(rng.integers(4, 10))
                ref_cnt = int(rng.integers(3, 8))
                aov = float(np.round(rng.uniform(90.0, 160.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": ret_cnt,
                    "refund_count": ref_cnt,
                    "return_rate": round(ret_cnt / order_cnt, 4),
                    "refund_rate": round(ref_cnt / order_cnt, 4),
                    "high_value_order_count": int(rng.integers(2, 6)),
                    "suspicious_activity_score": round(float(rng.uniform(0.65, 0.85)), 4),
                    "device_type": "mobile_android",
                    "primary_payment_method": "credit_card",
                })

                for etype, eid in [("DEVICE", dev), ("IP", ip), ("PAYMENT", card), ("ADDRESS", addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(days=int(rng.integers(10, 50)))).isoformat(),
                        "interaction_count": int(rng.integers(5, 25)),
                        "event_type": "CHECKOUT",
                    })
                    edge_counter += 1

        elif archetype == "CAMPUS_SHARED_IP":
            # Many legitimate accounts sharing 1 university NAT IP, diverse personal devices & cards
            shared_ip = f"IP_CAMPUS_NAT_{ip_counter:06d}"
            ip_counter += 1
            cluster_ips.add(shared_ip)

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + timedelta(days=float(rng.uniform(0, 360)))
                dev = f"DEV_STUDENT_{device_counter:06d}"
                device_counter += 1
                card = f"CARD_STUDENT_{card_counter:06d}"
                card_counter += 1
                addr = f"ADDR_DORM_{addr_counter:06d}"
                addr_counter += 1

                cluster_devices.add(dev)
                cluster_cards.add(card)
                cluster_addrs.add(addr)

                order_cnt = int(rng.integers(5, 30))
                ret_cnt = int(order_cnt * rng.uniform(0.02, 0.12))
                ref_cnt = int(ret_cnt * rng.uniform(0.5, 1.0))
                aov = float(np.round(rng.uniform(25.0, 95.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": ret_cnt,
                    "refund_count": ref_cnt,
                    "return_rate": round(ret_cnt / order_cnt, 4),
                    "refund_rate": round(ref_cnt / order_cnt, 4),
                    "high_value_order_count": int(rng.integers(0, 2)),
                    "suspicious_activity_score": round(float(rng.uniform(0.01, 0.08)), 4),
                    "device_type": str(rng.choice(["mobile_ios", "desktop_chrome", "desktop_safari"])),
                    "primary_payment_method": str(rng.choice(["credit_card", "debit_card", "apple_pay"])),
                })

                for etype, eid in [("DEVICE", dev), ("IP", shared_ip), ("PAYMENT", card), ("ADDRESS", addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(days=int(rng.integers(10, 100)))).isoformat(),
                        "interaction_count": int(rng.integers(3, 20)),
                        "event_type": "CHECKOUT",
                    })
                    edge_counter += 1

        elif archetype == "COWORKING_PUBLIC_WIFI":
            # Shared coffee shop / coworking IP, diverse business and personal users
            shared_ip = f"IP_COWORKING_{ip_counter:06d}"
            ip_counter += 1
            cluster_ips.add(shared_ip)

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + timedelta(days=float(rng.uniform(0, 300)))
                dev = f"DEV_LAPTOP_{device_counter:06d}"
                device_counter += 1
                card = f"CARD_CORP_{card_counter:06d}"
                card_counter += 1
                addr = f"ADDR_OFFICE_{addr_counter:06d}"
                addr_counter += 1

                cluster_devices.add(dev)
                cluster_cards.add(card)
                cluster_addrs.add(addr)

                order_cnt = int(rng.integers(8, 40))
                ret_cnt = int(order_cnt * rng.uniform(0.01, 0.08))
                ref_cnt = int(ret_cnt * rng.uniform(0.5, 1.0))
                aov = float(np.round(rng.uniform(40.0, 180.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": ret_cnt,
                    "refund_count": ref_cnt,
                    "return_rate": round(ret_cnt / order_cnt, 4),
                    "refund_rate": round(ref_cnt / order_cnt, 4),
                    "high_value_order_count": int(rng.integers(1, 4)),
                    "suspicious_activity_score": round(float(rng.uniform(0.01, 0.09)), 4),
                    "device_type": str(rng.choice(["desktop_chrome", "desktop_safari", "mobile_ios"])),
                    "primary_payment_method": str(rng.choice(["credit_card", "paypal"])),
                })

                for etype, eid in [("DEVICE", dev), ("IP", shared_ip), ("PAYMENT", card), ("ADDRESS", addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(days=int(rng.integers(15, 120)))).isoformat(),
                        "interaction_count": int(rng.integers(5, 35)),
                        "event_type": "CHECKOUT",
                    })
                    edge_counter += 1

        elif archetype == "FAMILY_HOUSEHOLD":
            # 2-4 family members sharing 1 home address and 1 credit card, but separate phones
            shared_addr = f"ADDR_HOME_{addr_counter:06d}"
            addr_counter += 1
            shared_card = f"CARD_FAMILY_{card_counter:06d}"
            card_counter += 1

            cluster_addrs.add(shared_addr)
            cluster_cards.add(shared_card)

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + timedelta(days=float(rng.uniform(0, 500)))
                dev = f"DEV_PHONE_{device_counter:06d}"
                device_counter += 1
                ip = f"IP_HOME_WIFI_{ip_counter:06d}"
                ip_counter += 1

                cluster_devices.add(dev)
                cluster_ips.add(ip)

                order_cnt = int(rng.integers(12, 50))
                ret_cnt = int(order_cnt * rng.uniform(0.03, 0.15))
                ref_cnt = int(ret_cnt * rng.uniform(0.6, 1.0))
                aov = float(np.round(rng.uniform(50.0, 140.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": ret_cnt,
                    "refund_count": ref_cnt,
                    "return_rate": round(ret_cnt / order_cnt, 4),
                    "refund_rate": round(ref_cnt / order_cnt, 4),
                    "high_value_order_count": int(rng.integers(1, 3)),
                    "suspicious_activity_score": round(float(rng.uniform(0.01, 0.06)), 4),
                    "device_type": str(rng.choice(["mobile_ios", "mobile_android"])),
                    "primary_payment_method": "credit_card",
                })

                for etype, eid in [("DEVICE", dev), ("IP", ip), ("PAYMENT", shared_card), ("ADDRESS", shared_addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(days=int(rng.integers(30, 200)))).isoformat(),
                        "interaction_count": int(rng.integers(8, 40)),
                        "event_type": "CHECKOUT",
                    })
                    edge_counter += 1

        elif archetype == "APARTMENT_BUILDING_ADDR":
            # Shared building address, separate apartment numbers, distinct cards/devices
            shared_building_addr = f"ADDR_APT_BLDG_{addr_counter:06d}"
            addr_counter += 1
            cluster_addrs.add(shared_building_addr)

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + timedelta(days=float(rng.uniform(0, 400)))
                dev = f"DEV_RESIDENT_{device_counter:06d}"
                device_counter += 1
                ip = f"IP_RESIDENT_{ip_counter:06d}"
                ip_counter += 1
                card = f"CARD_RESIDENT_{card_counter:06d}"
                card_counter += 1

                cluster_devices.add(dev)
                cluster_ips.add(ip)
                cluster_cards.add(card)

                order_cnt = int(rng.integers(10, 40))
                ret_cnt = int(order_cnt * rng.uniform(0.02, 0.10))
                ref_cnt = int(ret_cnt * rng.uniform(0.5, 1.0))
                aov = float(np.round(rng.uniform(45.0, 160.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": ret_cnt,
                    "refund_count": ref_cnt,
                    "return_rate": round(ret_cnt / order_cnt, 4),
                    "refund_rate": round(ref_cnt / order_cnt, 4),
                    "high_value_order_count": int(rng.integers(1, 4)),
                    "suspicious_activity_score": round(float(rng.uniform(0.01, 0.07)), 4),
                    "device_type": str(rng.choice(["mobile_ios", "desktop_chrome", "mobile_android"])),
                    "primary_payment_method": str(rng.choice(["credit_card", "debit_card"])),
                })

                for etype, eid in [("DEVICE", dev), ("IP", ip), ("PAYMENT", card), ("ADDRESS", shared_building_addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(days=int(rng.integers(20, 150)))).isoformat(),
                        "interaction_count": int(rng.integers(6, 30)),
                        "event_type": "CHECKOUT",
                    })
                    edge_counter += 1

        elif archetype == "PUBLIC_KIOSK_DEVICE":
            # In-store customer tablet shared across shoppers, distinct cards & addresses
            kiosk_dev = f"DEV_STORE_KIOSK_{device_counter:06d}"
            device_counter += 1
            cluster_devices.add(kiosk_dev)

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + timedelta(days=float(rng.uniform(0, 300)))
                ip = f"IP_STORE_WIFI_{ip_counter:06d}"
                ip_counter += 1
                card = f"CARD_SHOPPER_{card_counter:06d}"
                card_counter += 1
                addr = f"ADDR_SHOPPER_{addr_counter:06d}"
                addr_counter += 1

                cluster_ips.add(ip)
                cluster_cards.add(card)
                cluster_addrs.add(addr)

                order_cnt = int(rng.integers(4, 20))
                ret_cnt = int(order_cnt * rng.uniform(0.02, 0.10))
                ref_cnt = int(ret_cnt * rng.uniform(0.5, 1.0))
                aov = float(np.round(rng.uniform(35.0, 110.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": ret_cnt,
                    "refund_count": ref_cnt,
                    "return_rate": round(ret_cnt / order_cnt, 4),
                    "refund_rate": round(ref_cnt / order_cnt, 4),
                    "high_value_order_count": int(rng.integers(0, 2)),
                    "suspicious_activity_score": round(float(rng.uniform(0.01, 0.08)), 4),
                    "device_type": "mobile_ios",
                    "primary_payment_method": "credit_card",
                })

                for etype, eid in [("DEVICE", kiosk_dev), ("IP", ip), ("PAYMENT", card), ("ADDRESS", addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(days=int(rng.integers(10, 80)))).isoformat(),
                        "interaction_count": int(rng.integers(3, 15)),
                        "event_type": "CHECKOUT",
                    })
                    edge_counter += 1

        elif archetype in ["PARTIAL_NETWORK_OVERLAP", "STAR_TOPOLOGY_BENIGN"]:
            # Coincidental single link (e.g. airport Wi-Fi or corporate expense card)
            central_token = f"CARD_CORP_BENIGN_{card_counter:06d}"
            card_counter += 1
            cluster_cards.add(central_token)

            for i in range(cluster_size):
                acc_id = f"ACC_{account_counter:06d}"
                account_counter += 1
                cluster_acc_ids.append(acc_id)

                created_at = cluster_created_base + timedelta(days=float(rng.uniform(0, 365)))
                dev = f"DEV_USER_{device_counter:06d}"
                device_counter += 1
                ip = f"IP_USER_{ip_counter:06d}"
                ip_counter += 1
                addr = f"ADDR_USER_{addr_counter:06d}"
                addr_counter += 1

                cluster_devices.add(dev)
                cluster_ips.add(ip)
                cluster_addrs.add(addr)

                order_cnt = int(rng.integers(6, 35))
                ret_cnt = int(order_cnt * rng.uniform(0.02, 0.12))
                ref_cnt = int(ret_cnt * rng.uniform(0.5, 1.0))
                aov = float(np.round(rng.uniform(40.0, 150.0), 2))
                spend = float(np.round(order_cnt * aov, 2))

                accounts_records.append({
                    "account_id": acc_id,
                    "cluster_id": cluster_id,
                    "created_at": created_at.isoformat(),
                    "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                    "order_count": order_cnt,
                    "total_spend": spend,
                    "average_order_value": aov,
                    "return_count": ret_cnt,
                    "refund_count": ref_cnt,
                    "return_rate": round(ret_cnt / order_cnt, 4),
                    "refund_rate": round(ref_cnt / order_cnt, 4),
                    "high_value_order_count": int(rng.integers(0, 3)),
                    "suspicious_activity_score": round(float(rng.uniform(0.01, 0.08)), 4),
                    "device_type": str(rng.choice(["desktop_chrome", "mobile_ios"])),
                    "primary_payment_method": "credit_card",
                })

                for etype, eid in [("DEVICE", dev), ("IP", ip), ("PAYMENT", central_token), ("ADDRESS", addr)]:
                    edges_records.append({
                        "edge_id": f"EDGE_{edge_counter:08d}",
                        "account_id": acc_id,
                        "entity_type": etype,
                        "entity_id": eid,
                        "first_seen_at": created_at.isoformat(),
                        "last_seen_at": (created_at + timedelta(days=int(rng.integers(15, 90)))).isoformat(),
                        "interaction_count": int(rng.integers(4, 20)),
                        "event_type": "CHECKOUT",
                    })
                    edge_counter += 1

        else:  # SINGLETON_CLEAN
            acc_id = f"ACC_{account_counter:06d}"
            account_counter += 1
            cluster_acc_ids.append(acc_id)

            created_at = cluster_created_base + timedelta(days=float(rng.uniform(0, 500)))
            dev = f"DEV_SOLO_{device_counter:06d}"
            device_counter += 1
            ip = f"IP_SOLO_{ip_counter:06d}"
            ip_counter += 1
            card = f"CARD_SOLO_{card_counter:06d}"
            card_counter += 1
            addr = f"ADDR_SOLO_{addr_counter:06d}"
            addr_counter += 1

            cluster_devices.add(dev)
            cluster_ips.add(ip)
            cluster_cards.add(card)
            cluster_addrs.add(addr)

            order_cnt = int(rng.integers(5, 45))
            ret_cnt = int(order_cnt * rng.uniform(0.01, 0.15))
            ref_cnt = int(ret_cnt * rng.uniform(0.5, 1.0))
            aov = float(np.round(rng.uniform(35.0, 130.0), 2))
            spend = float(np.round(order_cnt * aov, 2))

            accounts_records.append({
                "account_id": acc_id,
                "cluster_id": cluster_id,
                "created_at": created_at.isoformat(),
                "account_age_days": max(1, (datetime(2026, 8, 1, tzinfo=timezone.utc) - created_at).days),
                "order_count": order_cnt,
                "total_spend": spend,
                "average_order_value": aov,
                "return_count": ret_cnt,
                "refund_count": ref_cnt,
                "return_rate": round(ret_cnt / order_cnt, 4),
                "refund_rate": round(ref_cnt / order_cnt, 4),
                "high_value_order_count": int(rng.integers(0, 3)),
                "suspicious_activity_score": round(float(rng.uniform(0.01, 0.09)), 4),
                "device_type": str(rng.choice(["mobile_ios", "desktop_chrome", "mobile_android"])),
                "primary_payment_method": str(rng.choice(["credit_card", "debit_card", "paypal"])),
            })

            for etype, eid in [("DEVICE", dev), ("IP", ip), ("PAYMENT", card), ("ADDRESS", addr)]:
                edges_records.append({
                    "edge_id": f"EDGE_{edge_counter:08d}",
                    "account_id": acc_id,
                    "entity_type": etype,
                    "entity_id": eid,
                    "first_seen_at": created_at.isoformat(),
                    "last_seen_at": (created_at + timedelta(days=int(rng.integers(20, 200)))).isoformat(),
                    "interaction_count": int(rng.integers(5, 30)),
                    "event_type": "CHECKOUT",
                })
                edge_counter += 1

        # Calculate density approximation
        n_members = len(cluster_acc_ids)
        density = 1.0 if n_members <= 1 else round(float(min(1.0, 4.0 / max(1.0, n_members))), 4)

        clusters_records.append({
            "cluster_id": cluster_id,
            "cluster_type": archetype,
            "member_count": n_members,
            "device_count": len(cluster_devices),
            "ip_count": len(cluster_ips),
            "payment_count": len(cluster_cards),
            "address_count": len(cluster_addrs),
            "density": density,
            "cluster_abuse_label": is_abuse,
        })

        current_acc_count += n_members

    df_accounts = pd.DataFrame(accounts_records)
    df_edges = pd.DataFrame(edges_records)
    df_clusters = pd.DataFrame(clusters_records)

    # -------------------------------------------------------------
    # Compute Network Features (Strictly Zero Target Leakage)
    # -------------------------------------------------------------
    df_features = compute_network_features(df_accounts, df_edges, df_clusters)

    return df_accounts, df_edges, df_clusters, df_features


def compute_network_features(
    df_accounts: pd.DataFrame,
    df_edges: pd.DataFrame,
    df_clusters: pd.DataFrame,
) -> pd.DataFrame:
    """Compute topological, behavioral similarity, and temporal coordination features.
    
    Guaranteed Anti-Leakage: Never uses cluster_abuse_label or is_ring_member_label!
    """
    eps = 1e-4

    # Map cluster metadata
    cluster_meta = df_clusters.set_index("cluster_id").to_dict(orient="index")

    # Group entity occurrences by type to identify shared tokens
    entity_to_accs: Dict[str, Set[str]] = df_edges.groupby("entity_id")["account_id"].apply(set).to_dict()
    acc_to_entities: Dict[str, Dict[str, Set[str]]] = {}
    for row in df_edges.itertuples():
        if row.account_id not in acc_to_entities:
            acc_to_entities[row.account_id] = {"DEVICE": set(), "IP": set(), "PAYMENT": set(), "ADDRESS": set()}
        acc_to_entities[row.account_id][row.entity_type].add(row.entity_id)

    # Cluster-level temporal & behavioral metrics
    cluster_acc_groups = df_accounts.groupby("cluster_id")

    cluster_temporal_stats: Dict[str, Dict[str, float]] = {}
    for cid, group in cluster_acc_groups:
        created_dt = pd.to_datetime(group["created_at"])
        time_span_hours = float((created_dt.max() - created_dt.min()).total_seconds() / 3600.0)

        # Standard deviations / variances
        std_hours = float(np.std([(t - created_dt.min()).total_seconds() / 3600.0 for t in created_dt])) if len(group) > 1 else 100.0
        temporal_coord = float(np.round(1.0 / (1.0 + (std_hours / 12.0)), 4))

        # Behavioral similarity across order count, spend, aov
        aov_mean = float(group["average_order_value"].mean())
        aov_std = float(group["average_order_value"].std()) if len(group) > 1 else 0.0
        tx_pattern_sim = float(np.round(max(0.0, 1.0 - (aov_std / (aov_mean + eps))), 4))

        ret_std = float(group["return_rate"].std()) if len(group) > 1 else 0.0
        ret_sim = float(np.round(max(0.0, 1.0 - (ret_std * 2.5)), 4))

        susp_mean = float(group["suspicious_activity_score"].mean())

        behavior_sim = float(np.round((tx_pattern_sim * 0.5) + (ret_sim * 0.5), 4))

        cluster_temporal_stats[cid] = {
            "time_span_hours": round(time_span_hours, 2),
            "temporal_coord": temporal_coord,
            "tx_pattern_sim": tx_pattern_sim,
            "ret_sim": ret_sim,
            "behavior_sim": behavior_sim,
            "susp_mean": round(susp_mean, 4),
        }

    feature_records = []

    cluster_acc_sets: Dict[str, Set[str]] = df_accounts.groupby("cluster_id")["account_id"].apply(set).to_dict()

    for acc in df_accounts.itertuples():
        cid = acc.cluster_id
        cmeta = cluster_meta[cid]
        cstats = cluster_temporal_stats[cid]
        c_members = cluster_acc_sets[cid]
        a_entities = acc_to_entities.get(acc.account_id, {"DEVICE": set(), "IP": set(), "PAYMENT": set(), "ADDRESS": set()})

        # Count other accounts sharing each entity type
        shared_dev_accs: Set[str] = set()
        for dev in a_entities["DEVICE"]:
            shared_dev_accs.update(entity_to_accs.get(dev, set()))
        shared_dev_count = max(0, len(shared_dev_accs) - 1)

        shared_ip_accs: Set[str] = set()
        for ip in a_entities["IP"]:
            shared_ip_accs.update(entity_to_accs.get(ip, set()))
        shared_ip_count = max(0, len(shared_ip_accs) - 1)

        shared_card_accs: Set[str] = set()
        for card in a_entities["PAYMENT"]:
            shared_card_accs.update(entity_to_accs.get(card, set()))
        shared_card_count = max(0, len(shared_card_accs) - 1)

        shared_addr_accs: Set[str] = set()
        for addr in a_entities["ADDRESS"]:
            shared_addr_accs.update(entity_to_accs.get(addr, set()))
        shared_addr_count = max(0, len(shared_addr_accs) - 1)

        # Weighted entity overlap score (Cards > Devices > Addresses > IPs)
        c_size = cmeta["member_count"]
        weighted_overlap = (
            (shared_card_count * 0.40) +
            (shared_dev_count * 0.30) +
            (shared_addr_count * 0.20) +
            (shared_ip_count * 0.10)
        ) / max(1.0, float(c_size - 1) if c_size > 1 else 1.0)
        entity_overlap_score = float(np.round(np.clip(weighted_overlap, 0.0, 1.0), 4))

        # Distinct other accounts connected via ANY shared entity token (DEVICE, IP, PAYMENT, ADDRESS)
        projected_neighbors: Set[str] = set()
        for etype in ["DEVICE", "IP", "PAYMENT", "ADDRESS"]:
            for token in a_entities[etype]:
                projected_neighbors.update(entity_to_accs.get(token, set()))

        # Remove self and restrict to cluster membership
        projected_neighbors.discard(acc.account_id)
        projected_in_cluster = projected_neighbors.intersection(c_members)

        # Bipartite degree centrality = |N_projected(u)| / max(1, cluster_size - 1)
        bipartite_degree = float(np.round(len(projected_in_cluster) / max(1.0, float(c_size - 1)), 4)) if c_size > 1 else 0.0

        pay_to_dev_ratio = float(np.round(cmeta["payment_count"] / max(1.0, cmeta["device_count"]), 4))
        acc_to_pay_ratio = float(np.round(cmeta["member_count"] / max(1.0, cmeta["payment_count"]), 4))

        # Account target is strictly separate
        is_ring_member = cmeta["cluster_abuse_label"]

        feature_records.append({
            "account_id": acc.account_id,
            "cluster_id": cid,
            "cluster_size": c_size,
            "shared_device_account_count": shared_dev_count,
            "shared_ip_account_count": shared_ip_count,
            "shared_payment_account_count": shared_card_count,
            "shared_address_account_count": shared_addr_count,
            "entity_overlap_score": entity_overlap_score,
            "bipartite_degree_centrality": bipartite_degree,
            "creation_velocity_window_hours": cstats["time_span_hours"],
            "payment_to_device_ratio": pay_to_dev_ratio,
            "account_to_payment_ratio": acc_to_pay_ratio,
            "behavior_similarity_score": cstats["behavior_sim"],
            "temporal_coordination_score": cstats["temporal_coord"],
            "suspicious_behavior_overlap": cstats["susp_mean"],
            "return_behavior_similarity": cstats["ret_sim"],
            "transaction_pattern_similarity": cstats["tx_pattern_sim"],
            "is_ring_member_label": is_ring_member,
        })

    return pd.DataFrame(feature_records)


def regenerate_network_features_only(output_dir: str = "data") -> pd.DataFrame:
    """Recompute ONLY ring_account_network_features.csv from existing raw graph files."""
    path_accounts = os.path.join(output_dir, "ring_accounts.csv")
    path_edges = os.path.join(output_dir, "ring_entity_edges.csv")
    path_clusters = os.path.join(output_dir, "ring_clusters.csv")
    path_features = os.path.join(output_dir, "ring_account_network_features.csv")

    df_accounts = pd.read_csv(path_accounts)
    df_edges = pd.read_csv(path_edges)
    df_clusters = pd.read_csv(path_clusters)

    df_features = compute_network_features(df_accounts, df_edges, df_clusters)
    df_features.to_csv(path_features, index=False)
    return df_features


def save_abuse_ring_datasets(
    output_dir: str = "data",
    num_accounts: int = 5000,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Generate and write the 4 Abuse-Ring dataset files to data/."""
    os.makedirs(output_dir, exist_ok=True)

    df_accounts, df_edges, df_clusters, df_features = generate_abuse_ring_dataset(
        target_account_count=num_accounts,
        random_seed=random_seed,
    )

    path_accounts = os.path.join(output_dir, "ring_accounts.csv")
    path_edges = os.path.join(output_dir, "ring_entity_edges.csv")
    path_clusters = os.path.join(output_dir, "ring_clusters.csv")
    path_features = os.path.join(output_dir, "ring_account_network_features.csv")

    df_accounts.to_csv(path_accounts, index=False)
    df_edges.to_csv(path_edges, index=False)
    df_clusters.to_csv(path_clusters, index=False)
    df_features.to_csv(path_features, index=False)

    summary = {
        "accounts_count": len(df_accounts),
        "clusters_count": len(df_clusters),
        "edges_count": len(df_edges),
        "positive_clusters (abuse rings)": int(df_clusters["cluster_abuse_label"].sum()),
        "negative_clusters (benign/hard neg)": int((df_clusters["cluster_abuse_label"] == 0).sum()),
        "positive_accounts": int(df_features["is_ring_member_label"].sum()),
        "negative_accounts": int((df_features["is_ring_member_label"] == 0).sum()),
        "cluster_type_distribution": df_clusters["cluster_type"].value_counts().to_dict(),
    }

    return summary


if __name__ == "__main__":
    summary = save_abuse_ring_datasets()
    print("Abuse-Ring Datasets Generated Successfully:")
    print(summary)
