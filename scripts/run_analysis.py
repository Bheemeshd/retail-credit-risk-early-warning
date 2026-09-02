#!/usr/bin/env python3
"""Train, evaluate, score, and build analytical artifacts."""

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from credit_risk.modeling import train_and_score  # noqa: E402
from credit_risk.reporting import generate_reports  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=REPO_ROOT / "data" / "processed" / "credit_risk.db")
    parser.add_argument("--artifact-dir", type=Path, default=REPO_ROOT / "artifacts")
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / "reports")
    args = parser.parse_args()
    metrics = train_and_score(args.database, args.artifact_dir)
    report = generate_reports(args.database, args.artifact_dir, args.report_dir)
    print(json.dumps({"holdout": metrics["holdout"], "report": report}, indent=2))


if __name__ == "__main__":
    main()

