#!/usr/bin/env python3
"""Generate the deterministic synthetic source files."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from credit_risk.data_generator import generate_portfolio  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loans", type=int, default=2500)
    parser.add_argument("--months", type=int, default=21)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-month", type=date.fromisoformat, default=date(2024, 1, 1))
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "data" / "raw")
    args = parser.parse_args()
    manifest = generate_portfolio(args.output_dir, args.loans, args.months, args.seed, args.start_month)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

