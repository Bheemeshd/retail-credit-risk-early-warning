#!/usr/bin/env python3
"""Run generation, ETL, modeling, evaluation, and report production."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from credit_risk.data_generator import generate_portfolio  # noqa: E402
from credit_risk.etl import build_database  # noqa: E402
from credit_risk.modeling import train_and_score  # noqa: E402
from credit_risk.paths import ensure_directories  # noqa: E402
from credit_risk.reporting import generate_reports  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loans", type=int, default=2500)
    parser.add_argument("--months", type=int, default=21)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-month", type=date.fromisoformat, default=date(2024, 1, 1))
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    ensure_directories(output_root)
    raw_dir = output_root / "data" / "raw"
    database_path = output_root / "data" / "processed" / "credit_risk.db"
    artifact_dir = output_root / "artifacts"
    report_dir = output_root / "reports"

    manifest = generate_portfolio(raw_dir, args.loans, args.months, args.seed, args.start_month)
    loaded = build_database(raw_dir, database_path, REPO_ROOT / "sql")
    metrics = train_and_score(database_path, artifact_dir)
    report = generate_reports(database_path, artifact_dir, report_dir)
    result = {
        "status": "success",
        "output_root": str(output_root),
        "manifest": manifest,
        "loaded_rows": loaded,
        "holdout_metrics": {
            "roc_auc": metrics["holdout"]["roc_auc"],
            "average_precision": metrics["holdout"]["average_precision"],
            "brier_score": metrics["holdout"]["brier_score"],
            "top_decile_recall": metrics["holdout"]["top_decile"]["recall"],
            "top_decile_lift": metrics["holdout"]["top_decile"]["lift_vs_portfolio"],
        },
        "report": report,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

