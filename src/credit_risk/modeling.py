"""Interpretable logistic early-warning model and evaluation utilities."""

from __future__ import annotations

import csv
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np


MODEL_VERSION = "logistic-ews-v1"
FEATURE_NAMES = [
    "bureau_score",
    "days_past_due",
    "utilization_pct",
    "payment_ratio",
    "missed_payments_3m",
    "dti_pct",
    "income_drop_flag",
    "hardship_flag",
    "account_age_months",
    "log_outstanding_balance_eur",
    "apr_pct",
    "is_revolving",
]


@dataclass
class LogisticModel:
    """Minimal, serializable logistic regression with standardized features."""

    feature_names: Sequence[str]
    means: np.ndarray
    scales: np.ndarray
    coefficients: np.ndarray
    intercept: float

    def predict_proba(self, matrix: np.ndarray) -> np.ndarray:
        standardized = (matrix - self.means) / self.scales
        logits = self.intercept + standardized @ self.coefficients
        return _sigmoid(logits)

    def to_dict(self) -> Dict[str, object]:
        return {
            "model_version": MODEL_VERSION,
            "model_type": "L2-regularized logistic regression",
            "feature_names": list(self.feature_names),
            "means": self.means.tolist(),
            "scales": self.scales.tolist(),
            "coefficients": self.coefficients.tolist(),
            "intercept": self.intercept,
            "important_note": (
                "Demonstration model trained on synthetic data. Scores support prioritization only "
                "and must not be used for lending or adverse-action decisions."
            ),
        }


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -35, 35)
    return 1.0 / (1.0 + np.exp(-clipped))


def _fit_logistic(
    matrix: np.ndarray,
    target: np.ndarray,
    l2_strength: float = 0.035,
    max_iterations: int = 40,
) -> LogisticModel:
    means = matrix.mean(axis=0)
    scales = matrix.std(axis=0)
    scales = np.where(scales < 1e-8, 1.0, scales)
    standardized = (matrix - means) / scales
    design = np.column_stack([np.ones(len(standardized)), standardized])
    beta = np.zeros(design.shape[1], dtype=float)
    penalty_mask = np.ones_like(beta)
    penalty_mask[0] = 0.0

    for _ in range(max_iterations):
        probabilities = _sigmoid(design @ beta)
        weights = np.clip(probabilities * (1 - probabilities), 1e-6, None)
        gradient = design.T @ (probabilities - target) / len(target)
        gradient += l2_strength * penalty_mask * beta
        hessian = design.T @ (design * weights[:, None]) / len(target)
        hessian += l2_strength * np.diag(penalty_mask)
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        beta -= step
        if float(np.linalg.norm(step)) < 1e-7:
            break

    return LogisticModel(
        feature_names=FEATURE_NAMES,
        means=means,
        scales=scales,
        coefficients=beta[1:],
        intercept=float(beta[0]),
    )


def _auc(target: np.ndarray, scores: np.ndarray) -> float:
    positives = int(target.sum())
    negatives = len(target) - positives
    if positives == 0 or negatives == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=float)
    start = 0
    while start < len(scores):
        end = start + 1
        while end < len(scores) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average_rank
        start = end
    positive_rank_sum = float(ranks[target == 1].sum())
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _average_precision(target: np.ndarray, scores: np.ndarray) -> float:
    positives = int(target.sum())
    if positives == 0:
        return float("nan")
    order = np.argsort(-scores, kind="mergesort")
    sorted_target = target[order]
    cumulative_positives = np.cumsum(sorted_target)
    precision = cumulative_positives / np.arange(1, len(target) + 1)
    return float(precision[sorted_target == 1].sum() / positives)


def _safe_float(value: float) -> float | None:
    return None if math.isnan(value) or math.isinf(value) else round(float(value), 6)


def _calibration_bins(target: np.ndarray, scores: np.ndarray, bin_count: int = 10) -> List[Dict[str, object]]:
    order = np.argsort(scores)
    bins: List[Dict[str, object]] = []
    for index, positions in enumerate(np.array_split(order, bin_count), start=1):
        if not len(positions):
            continue
        bins.append(
            {
                "bin": index,
                "count": int(len(positions)),
                "mean_predicted_probability": round(float(scores[positions].mean()), 6),
                "observed_target_rate": round(float(target[positions].mean()), 6),
            }
        )
    return bins


def _classification_metrics(target: np.ndarray, scores: np.ndarray, threshold: float) -> Dict[str, object]:
    predicted = scores >= threshold
    tp = int(((predicted == 1) & (target == 1)).sum())
    fp = int(((predicted == 1) & (target == 0)).sum())
    tn = int(((predicted == 0) & (target == 0)).sum())
    fn = int(((predicted == 0) & (target == 1)).sum())
    return {
        "threshold_from_train_top_decile": round(float(threshold), 6),
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "precision": round(tp / (tp + fp), 6) if tp + fp else None,
        "recall": round(tp / (tp + fn), 6) if tp + fn else None,
    }


def _evaluate(
    target: np.ndarray,
    scores: np.ndarray,
    train_top_decile_threshold: float,
) -> Dict[str, object]:
    prevalence = float(target.mean())
    selected = scores >= train_top_decile_threshold
    selected_count = int(selected.sum())
    precision_at_cutoff = float(target[selected].mean()) if selected_count else float("nan")
    recall_at_cutoff = float(target[selected].sum() / target.sum()) if target.sum() else float("nan")
    clipped_scores = np.clip(scores, 1e-9, 1 - 1e-9)
    return {
        "rows": int(len(target)),
        "positives": int(target.sum()),
        "target_rate": round(prevalence, 6),
        "roc_auc": _safe_float(_auc(target, scores)),
        "average_precision": _safe_float(_average_precision(target, scores)),
        "brier_score": round(float(np.mean((scores - target) ** 2)), 6),
        "log_loss": round(
            float(-np.mean(target * np.log(clipped_scores) + (1 - target) * np.log(1 - clipped_scores))),
            6,
        ),
        "top_decile": {
            "selected_rows": selected_count,
            "selected_share": round(selected_count / len(target), 6),
            "precision": _safe_float(precision_at_cutoff),
            "recall": _safe_float(recall_at_cutoff),
            "lift_vs_portfolio": _safe_float(precision_at_cutoff / prevalence) if prevalence else None,
        },
        "operating_point": _classification_metrics(target, scores, train_top_decile_threshold),
        "calibration_bins": _calibration_bins(target, scores),
    }


def _load_matrix(database_path: Path) -> Tuple[List[Tuple[object, ...]], np.ndarray, np.ndarray]:
    query = """
        SELECT
            f.loan_id,
            f.snapshot_month,
            f.default_next_3m,
            f.bureau_score,
            f.days_past_due,
            f.utilization_pct,
            f.payment_ratio,
            f.missed_payments_3m,
            f.dti_pct,
            f.income_drop_flag,
            f.hardship_flag,
            f.account_age_months,
            f.outstanding_balance_eur,
            f.apr_pct,
            f.product_type
        FROM vw_loan_risk_features AS f
        ORDER BY f.snapshot_month, f.loan_id
    """
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(query).fetchall()
    if not rows:
        raise ValueError("No analytical rows were found in the database")
    matrix = np.array(
        [
            [
                float(row[3]),
                float(row[4]),
                float(row[5]),
                float(row[6]),
                float(row[7]),
                float(row[8]),
                float(row[9]),
                float(row[10]),
                float(row[11]),
                math.log1p(float(row[12])),
                float(row[13]),
                float(row[14] == "Credit card"),
            ]
            for row in rows
        ],
        dtype=float,
    )
    target = np.array([int(row[2]) for row in rows], dtype=int)
    return rows, matrix, target


def _temporal_split(rows: Sequence[Tuple[object, ...]]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, object]]:
    months = sorted({str(row[1]) for row in rows})
    if len(months) < 9:
        raise ValueError("At least nine snapshot months are required")
    test_months = months[-3:]
    embargo_months = months[-6:-3]
    train_months = months[:-6]
    month_values = np.array([str(row[1]) for row in rows])
    train_mask = np.isin(month_values, train_months)
    embargo_mask = np.isin(month_values, embargo_months)
    test_mask = np.isin(month_values, test_months)
    definition = {
        "strategy": "Purged temporal split",
        "train_start": train_months[0],
        "train_end": train_months[-1],
        "embargo_start": embargo_months[0],
        "embargo_end": embargo_months[-1],
        "test_start": test_months[0],
        "test_end": test_months[-1],
        "target_horizon_months": 3,
        "reason": "Three-month embargo reduces overlap between forward-looking train and holdout labels.",
    }
    return train_mask, embargo_mask, test_mask, definition


def _risk_tiers(train_scores: np.ndarray, all_scores: np.ndarray) -> Tuple[np.ndarray, Dict[str, float]]:
    thresholds = {
        "monitor_p50": float(np.quantile(train_scores, 0.50)),
        "high_p80": float(np.quantile(train_scores, 0.80)),
        "critical_p95": float(np.quantile(train_scores, 0.95)),
    }
    tiers = np.full(len(all_scores), "Low", dtype=object)
    tiers[all_scores >= thresholds["monitor_p50"]] = "Monitor"
    tiers[all_scores >= thresholds["high_p80"]] = "High"
    tiers[all_scores >= thresholds["critical_p95"]] = "Critical"
    return tiers, {key: round(value, 8) for key, value in thresholds.items()}


def _persist_scores(
    database_path: Path,
    rows: Sequence[Tuple[object, ...]],
    scores: np.ndarray,
    tiers: np.ndarray,
    splits: np.ndarray,
) -> None:
    score_rows = [
        (str(row[0]), str(row[1]), float(score), str(tier), str(split), MODEL_VERSION)
        for row, score, tier, split in zip(rows, scores, tiers, splits)
    ]
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("DELETE FROM model_scores")
        connection.executemany(
            """
            INSERT INTO model_scores (
                loan_id, snapshot_month, predicted_probability, risk_tier, data_split, model_version
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            score_rows,
        )
        connection.commit()


def _write_outputs(
    artifact_dir: Path,
    rows: Sequence[Tuple[object, ...]],
    target: np.ndarray,
    scores: np.ndarray,
    tiers: np.ndarray,
    splits: np.ndarray,
    model: LogisticModel,
    metrics: Dict[str, object],
) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    with (artifact_dir / "model.json").open("w", encoding="utf-8") as handle:
        json.dump(model.to_dict(), handle, indent=2)
        handle.write("\n")
    with (artifact_dir / "model_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
        handle.write("\n")

    with (artifact_dir / "model_coefficients.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["feature", "coefficient_per_sd", "odds_ratio_per_sd", "training_mean", "training_sd"])
        for name, coefficient, mean, scale in zip(
            model.feature_names, model.coefficients, model.means, model.scales
        ):
            writer.writerow(
                [
                    name,
                    round(float(coefficient), 8),
                    round(float(math.exp(coefficient)), 8),
                    round(float(mean), 6),
                    round(float(scale), 6),
                ]
            )

    with (artifact_dir / "scored_snapshots.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["loan_id", "snapshot_month", "actual_synthetic_target", "predicted_probability", "risk_tier", "data_split"]
        )
        for row, actual, score, tier, split in zip(rows, target, scores, tiers, splits):
            writer.writerow([row[0], row[1], int(actual), round(float(score), 8), tier, split])


def train_and_score(database_path: Path, artifact_dir: Path) -> Dict[str, object]:
    """Fit on past observations, evaluate on a purged holdout, and persist scores."""
    database_path = Path(database_path)
    artifact_dir = Path(artifact_dir)
    rows, matrix, target = _load_matrix(database_path)
    train_mask, embargo_mask, test_mask, split_definition = _temporal_split(rows)

    train_target = target[train_mask]
    test_target = target[test_mask]
    if len(np.unique(train_target)) < 2 or len(np.unique(test_target)) < 2:
        raise ValueError("Training and holdout samples must each contain positive and negative outcomes")

    model = _fit_logistic(matrix[train_mask], train_target)
    all_scores = model.predict_proba(matrix)
    train_scores = all_scores[train_mask]
    test_scores = all_scores[test_mask]
    top_decile_threshold = float(np.quantile(train_scores, 0.90))
    tiers, tier_thresholds = _risk_tiers(train_scores, all_scores)
    splits = np.full(len(rows), "embargo", dtype=object)
    splits[train_mask] = "train"
    splits[test_mask] = "test"

    metrics: Dict[str, object] = {
        "model_version": MODEL_VERSION,
        "data_notice": "All observations and outcomes are synthetic; metrics are demonstrative, not production evidence.",
        "split": split_definition,
        "row_counts": {
            "train": int(train_mask.sum()),
            "embargo": int(embargo_mask.sum()),
            "test": int(test_mask.sum()),
        },
        "training_target_rate": round(float(train_target.mean()), 6),
        "holdout": _evaluate(test_target, test_scores, top_decile_threshold),
        "risk_tier_thresholds_from_training_scores": tier_thresholds,
    }

    _persist_scores(database_path, rows, all_scores, tiers, splits)
    _write_outputs(artifact_dir, rows, target, all_scores, tiers, splits, model, metrics)
    return metrics

