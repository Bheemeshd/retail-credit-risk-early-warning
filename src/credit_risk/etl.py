"""CSV-to-SQLite ETL with schema checks and atomic database replacement."""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from .paths import REPO_ROOT


CUSTOMER_FIELDS = (
    "customer_id",
    "birth_year",
    "region",
    "employment_status",
    "annual_income_eur",
    "months_with_bank",
    "home_ownership",
)
LOAN_FIELDS = (
    "loan_id",
    "customer_id",
    "origination_date",
    "product_type",
    "original_principal_eur",
    "term_months",
    "apr_pct",
    "installment_eur",
    "purpose",
)
PERFORMANCE_FIELDS = (
    "loan_id",
    "snapshot_month",
    "account_age_months",
    "outstanding_balance_eur",
    "days_past_due",
    "utilization_pct",
    "payment_ratio",
    "missed_payments_3m",
    "bureau_score",
    "dti_pct",
    "income_drop_flag",
    "hardship_flag",
    "default_next_3m",
)


def _read_rows(path: Path, fields: Sequence[str]) -> List[Tuple[str, ...]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = set(fields) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
        return [tuple(row[field] for field in fields) for row in reader]


def _insert_many(
    connection: sqlite3.Connection,
    table: str,
    fields: Sequence[str],
    rows: Iterable[Tuple[str, ...]],
) -> None:
    placeholders = ", ".join("?" for _ in fields)
    columns = ", ".join(fields)
    connection.executemany(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        rows,
    )


def build_database(
    raw_dir: Path,
    database_path: Path,
    sql_dir: Path | None = None,
) -> Dict[str, int]:
    """Load generated CSVs into a validated SQLite database."""
    raw_dir = Path(raw_dir)
    database_path = Path(database_path)
    sql_dir = Path(sql_dir) if sql_dir else REPO_ROOT / "sql"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = database_path.with_suffix(database_path.suffix + ".tmp")
    if temporary_path.exists():
        temporary_path.unlink()

    customers = _read_rows(raw_dir / "customers.csv", CUSTOMER_FIELDS)
    loans = _read_rows(raw_dir / "loans.csv", LOAN_FIELDS)
    performance = _read_rows(raw_dir / "monthly_performance.csv", PERFORMANCE_FIELDS)

    connection = sqlite3.connect(temporary_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript((sql_dir / "schema.sql").read_text(encoding="utf-8"))
        _insert_many(connection, "customers", CUSTOMER_FIELDS, customers)
        _insert_many(connection, "loans", LOAN_FIELDS, loans)
        _insert_many(connection, "monthly_performance", PERFORMANCE_FIELDS, performance)

        manifest_path = raw_dir / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            connection.executemany(
                "INSERT OR REPLACE INTO pipeline_metadata VALUES (?, ?)",
                [(str(key), json.dumps(value)) for key, value in manifest.items()],
            )
        connection.executescript((sql_dir / "views.sql").read_text(encoding="utf-8"))

        foreign_key_failures = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_failures:
            raise ValueError(f"Foreign-key validation failed: {foreign_key_failures[:5]}")
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        if connection:
            connection.close()

    os.replace(temporary_path, database_path)
    return {
        "customers": len(customers),
        "loans": len(loans),
        "monthly_performance": len(performance),
    }

