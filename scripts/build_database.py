#!/usr/bin/env python3
"""Build and validate the SQLite analytical layer."""

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from credit_risk.etl import build_database  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--database", type=Path, default=REPO_ROOT / "data" / "processed" / "credit_risk.db")
    args = parser.parse_args()
    counts = build_database(args.raw_dir, args.database, REPO_ROOT / "sql")
    print(json.dumps({"database": str(args.database), "loaded_rows": counts}, indent=2))


if __name__ == "__main__":
    main()

