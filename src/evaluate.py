"""Model evaluation and metrics calculation for the Merchant Abuse Risk Engine."""

from typing import Dict, Any, List, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
)


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray = None,
) -> Dict[str, Any]:
    """Compute comprehensive evaluation metrics for merchant abuse classification."""
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    # False Positive Rate: FP / (FP + TN)
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    metrics: Dict[str, Any] = {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_positive_rate": fpr,
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
            "matrix": cm.tolist(),
        },
        "total_samples": int(len(y_true)),
        "true_positives_count": int(tp),
        "false_positives_count": int(fp),
    }

    if y_prob is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        except Exception:
            metrics["roc_auc"] = None

    return metrics


def get_feature_importances(
    model_or_pipeline: Union[Pipeline, Any],
    feature_names: List[str] = None,
) -> List[Tuple[str, float]]:
    """Extract and sort feature importances from a trained tree-based model or pipeline."""
    if isinstance(model_or_pipeline, Pipeline):
        preprocessor = model_or_pipeline.named_steps.get("preprocessor")
        classifier = model_or_pipeline.named_steps.get("classifier")
        
        if preprocessor is not None and hasattr(preprocessor, "get_feature_names_out"):
            names = [
                name.replace("num__", "").replace("cat__", "")
                for name in preprocessor.get_feature_names_out()
            ]
        elif feature_names:
            names = feature_names
        else:
            names = [f"feat_{i}" for i in range(len(classifier.feature_importances_))]

        importances = classifier.feature_importances_
    else:
        classifier = model_or_pipeline
        names = feature_names if feature_names else [f"feat_{i}" for i in range(len(classifier.feature_importances_))]
        importances = classifier.feature_importances_

    ranked = sorted(
        zip(names, [float(x) for x in importances]),
        key=lambda x: x[1],
        reverse=True,
    )
    return ranked


def format_metrics_report(metrics: Dict[str, Any], feature_importances: List[Tuple[str, float]] = None) -> str:
    """Generate a clean, ASCII-safe terminal report of model evaluation."""
    cm = metrics["confusion_matrix"]
    lines = [
        "=" * 65,
        "       AI-RISK ENGINE - HELD-OUT TEST EVALUATION REPORT",
        "=" * 65,
        f"Total Test Samples Evaluated : {metrics['total_samples']:,}",
        f"Precision                    : {metrics['precision']:.4f} ({metrics['precision']*100:.2f}%)",
        f"Recall                       : {metrics['recall']:.4f} ({metrics['recall']*100:.2f}%)",
        f"F1 Score                     : {metrics['f1_score']:.4f}",
        f"False Positive Rate (FPR)    : {metrics['false_positive_rate']:.4f} ({metrics['false_positive_rate']*100:.2f}%)",
    ]
    if metrics.get("roc_auc") is not None:
        lines.append(f"ROC-AUC Score                : {metrics['roc_auc']:.4f}")

    lines.extend([
        "-" * 65,
        "CONFUSION MATRIX:",
        f"  [TN] True Negatives  (Legit detected Legit) : {cm['true_negatives']:>5}",
        f"  [FP] False Positives (Legit flagged Abuse) : {cm['false_positives']:>5}",
        f"  [FN] False Negatives (Abuse missed)        : {cm['false_negatives']:>5}",
        f"  [TP] True Positives  (Abuse caught)        : {cm['true_positives']:>5}",
        "-" * 65,
    ])

    if feature_importances:
        lines.append("TOP CONTRIBUTING FEATURES (FEATURE IMPORTANCE):")
        for rank, (feat, score) in enumerate(feature_importances[:15], 1):
            bar = "#" * int(score * 40)
            lines.append(f"  {rank:>2}. {feat:<28} : {score:.4f}  {bar}")
        lines.append("=" * 65)

    return "\n".join(lines)
