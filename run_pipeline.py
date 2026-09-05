"""End-to-End Execution Script for Milestone 1 ML Risk Engine.

Runs:
1. Synthetic data generation with reproducible seed.
2. Train/Test split & training of unified Preprocessing + RandomForest Pipeline.
3. Strict evaluation on held-out test set (Precision, Recall, F1, CM, FPR).
4. Feature importance display.
5. Complete Pipeline persistence in models/.
6. Prediction demonstrations on brand-new, unseen account records and edge cases.
"""

import os
import json
import pandas as pd
from src.train import train_pipeline
from src.risk_scorer import predict_account_risk


def run_pipeline():
    print("=" * 75)
    print("   AI-RISK: PRODUCTION-GRADE MERCHANT ABUSE RISK ENGINE (MILESTONE 1)")
    print("=" * 75)

    # 1. Execute Training and Evaluation Pipeline
    pipeline, test_metrics = train_pipeline(
        model_output_dir="models",
        data_output_dir="data",
        test_size=0.20,
        random_state=42,
        num_synthetic_samples=5000,
    )

    # 2. Run Predictions on COMPLETELY NEW & UNSEEN Test Cases
    print("\n" + "=" * 75)
    print("   PREDICTING ON COMPLETELY NEW, UNSEEN ACCOUNT INPUTS & EDGE CASES")
    print("=" * 75)

    unseen_accounts = [
        # Case A: Clean, Normal Legitimate Customer (Unseen ID & Values)
        {
            "account_id": "ACC_NEW_LEGIT_099",
            "order_count": 14,
            "return_count": 1,
            "refund_count": 1,
            "total_spend": 820.0,
            "average_order_value": 58.57,
            "account_age_days": 210,
            "device_count": 1,
            "ip_count": 2,
            "payment_instrument_count": 1,
            "return_rate": 0.0714,
            "refund_rate": 0.0714,
            "high_value_order_count": 1,
            "suspicious_activity_score": 0.04,
            "device_type": "mobile_ios",
            "primary_payment_method": "apple_pay",
        },
        # Case B: High-Risk Syndicate Account (Unseen Ring Member)
        {
            "account_id": "ACC_NEW_RING_EXPL_777",
            "order_count": 18,
            "return_count": 15,
            "refund_count": 14,
            "total_spend": 2800.0,
            "average_order_value": 155.55,
            "account_age_days": 12,
            "device_count": 5,
            "ip_count": 6,
            "payment_instrument_count": 5,
            "return_rate": 0.8333,
            "refund_rate": 0.7778,
            "high_value_order_count": 11,
            "suspicious_activity_score": 0.94,
            "device_type": "emulator_bot",
            "primary_payment_method": "virtual_card",
        },
        # Case C: Edge Case - Missing Fields & Unknown Categoricals
        {
            "account_id": "ACC_NEW_INCOMPLETE_501",
            "order_count": 5,
            "total_spend": 300.0,
            # Missing return_count, refund_count, account_age_days, etc.
            "device_type": "smart_tv_tizen",  # Unknown category
            "primary_payment_method": "biometric_palm",  # Unknown category
        },
        # Case D: Edge Case - Inconsistent Counts & Negative Values
        {
            "account_id": "ACC_NEW_INVALID_999",
            "order_count": 4,
            "return_count": 9,   # Inconsistent: returns > orders
            "refund_count": 8,   # Inconsistent: refunds > orders
            "total_spend": -200.0,  # Invalid negative
            "account_age_days": -10,  # Invalid negative
            "return_rate": 2.25, # Out of [0, 1] range
            "refund_rate": 2.0,  # Out of [0, 1] range
            "suspicious_activity_score": 0.88,
        },
        # Case E: Edge Case - Extreme Out-of-Range Inputs
        {
            "account_id": "ACC_NEW_EXTREME_123",
            "order_count": 500,
            "return_count": 450,
            "refund_count": 420,
            "total_spend": 50_000_000.0,  # $50 Million spend
            "account_age_days": 99_999,   # Extreme age
            "device_count": 9999,
            "suspicious_activity_score": 0.99,
        },
    ]

    results = predict_account_risk(unseen_accounts)

    for i, res in enumerate(results, 1):
        print(f"\n[{i}] Account ID           : {res['account_id']}")
        print(f"    Risk Score (0-100)   : {res['risk_score']}/100")
        print(f"    Risk Level           : {res['risk_level']}")
        print(f"    Abuse Probability    : {res['risk_probability']:.2%}")
        print(f"    Data Quality Score   : {res['data_quality_score']:.2f}/1.00")
        print(f"    Recommended Action   : {res['recommended_action']}")
        print(f"    Risk Factors         : {', '.join(res['risk_factors'])}")
        if res['warnings']:
            print(f"    Warnings ({len(res['warnings'])})      : {'; '.join(res['warnings'])}")
        else:
            print("    Warnings             : None (Clean input)")

    print("\n" + "=" * 75)
    print("   ALL PIPELINE CHECKS AND UNSEEN INFERENCE TESTS COMPLETED!")
    print("=" * 75)


if __name__ == "__main__":
    run_pipeline()
