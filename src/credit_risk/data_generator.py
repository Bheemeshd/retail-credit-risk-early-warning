"""Deterministic synthetic retail-credit portfolio generator.

The generator deliberately creates no real customer data. Relationships and
outcomes are simulated for demonstration, testing, and portfolio use only.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import deque
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence


CUSTOMER_COLUMNS = [
    "customer_id",
    "birth_year",
    "region",
    "employment_status",
    "annual_income_eur",
    "months_with_bank",
    "home_ownership",
]

LOAN_COLUMNS = [
    "loan_id",
    "customer_id",
    "origination_date",
    "product_type",
    "original_principal_eur",
    "term_months",
    "apr_pct",
    "installment_eur",
    "purpose",
]

PERFORMANCE_COLUMNS = [
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
]


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _shift_month(value: date, months: int) -> date:
    absolute = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(absolute, 12)
    return date(year, month_zero + 1, 1)


def _month_sequence(start: date, count: int) -> List[date]:
    return [_shift_month(start, offset) for offset in range(count)]


def _weighted_choice(rng: random.Random, values: Sequence[str], weights: Sequence[float]) -> str:
    return rng.choices(values, weights=weights, k=1)[0]


def _amortizing_payment(principal: float, apr_pct: float, term_months: int) -> float:
    monthly_rate = apr_pct / 1200.0
    if monthly_rate == 0:
        return principal / term_months
    factor = (1 + monthly_rate) ** term_months
    return principal * monthly_rate * factor / (factor - 1)


def _write_csv(path: Path, rows: Iterable[Mapping[str, object]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})


def _build_customers(rng: random.Random, count: int) -> List[MutableMapping[str, object]]:
    regions = ["North", "South", "East", "West", "Central"]
    employment = ["Salaried", "Self-employed", "Retired", "Contract"]
    ownership = ["Owner", "Mortgage", "Tenant", "Other"]
    rows: List[MutableMapping[str, object]] = []

    for index in range(1, count + 1):
        latent_risk = rng.betavariate(2.0, 5.2)
        employment_status = _weighted_choice(rng, employment, [0.61, 0.19, 0.11, 0.09])
        income_multiplier = {
            "Salaried": 1.08,
            "Self-employed": 1.16,
            "Retired": 0.76,
            "Contract": 0.88,
        }[employment_status]
        income = _clamp(rng.lognormvariate(math.log(43_000), 0.46) * income_multiplier, 16_000, 220_000)
        age = int(_clamp(round(rng.normalvariate(44, 13)), 21, 78))
        rows.append(
            {
                "customer_id": f"C{index:06d}",
                "birth_year": 2025 - age,
                "region": _weighted_choice(rng, regions, [0.22, 0.19, 0.20, 0.18, 0.21]),
                "employment_status": employment_status,
                "annual_income_eur": round(income, 2),
                "months_with_bank": rng.randint(6, 240),
                "home_ownership": _weighted_choice(rng, ownership, [0.27, 0.36, 0.31, 0.06]),
                "_latent_risk": latent_risk,
            }
        )
    return rows


def _loan_terms(rng: random.Random, product: str) -> Dict[str, object]:
    if product == "Mortgage":
        principal = rng.uniform(95_000, 420_000)
        term = _weighted_choice(rng, ["180", "240", "300"], [0.25, 0.50, 0.25])
        apr = rng.uniform(1.8, 5.8)
        purpose = "Home purchase"
    elif product == "Auto loan":
        principal = rng.uniform(9_000, 62_000)
        term = _weighted_choice(rng, ["36", "48", "60", "72"], [0.12, 0.28, 0.43, 0.17])
        apr = rng.uniform(3.2, 10.5)
        purpose = "Vehicle purchase"
    elif product == "Credit card":
        principal = rng.uniform(2_000, 24_000)
        term = "60"
        apr = rng.uniform(12.5, 23.9)
        purpose = "Revolving credit"
    else:
        principal = rng.uniform(3_000, 55_000)
        term = _weighted_choice(rng, ["24", "36", "48", "60", "72"], [0.08, 0.23, 0.28, 0.31, 0.10])
        apr = rng.uniform(4.0, 15.8)
        purpose = _weighted_choice(
            rng,
            ["Home improvement", "Debt consolidation", "Major purchase", "Education"],
            [0.31, 0.35, 0.24, 0.10],
        )
    return {
        "principal": principal,
        "term": int(term),
        "apr": apr,
        "purpose": purpose,
    }


def _build_loans(
    rng: random.Random,
    count: int,
    customers: Sequence[MutableMapping[str, object]],
    portfolio_start: date,
) -> List[MutableMapping[str, object]]:
    products = ["Personal loan", "Credit card", "Auto loan", "Mortgage"]
    rows: List[MutableMapping[str, object]] = []
    for index in range(1, count + 1):
        customer = rng.choice(customers)
        product = _weighted_choice(rng, products, [0.35, 0.30, 0.20, 0.15])
        terms = _loan_terms(rng, product)
        principal = float(terms["principal"])
        term = int(terms["term"])
        apr = float(terms["apr"])
        installment = principal * 0.03 if product == "Credit card" else _amortizing_payment(principal, apr, term)
        origination = _shift_month(portfolio_start, -rng.randint(3, min(72, max(4, term // 2))))
        latent = float(customer["_latent_risk"])
        rows.append(
            {
                "loan_id": f"L{index:06d}",
                "customer_id": customer["customer_id"],
                "origination_date": origination.isoformat(),
                "product_type": product,
                "original_principal_eur": round(principal, 2),
                "term_months": term,
                "apr_pct": round(apr, 3),
                "installment_eur": round(installment, 2),
                "purpose": terms["purpose"],
                "_latent_risk": _clamp(latent + rng.normalvariate(0, 0.06), 0.01, 0.98),
                "_income": float(customer["annual_income_eur"]),
                "_external_dti": _clamp(rng.normalvariate(13 + latent * 22, 7), 0, 55),
            }
        )
    return rows


def _build_performance(
    rng: random.Random,
    loans: Sequence[MutableMapping[str, object]],
    months: Sequence[date],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for loan in loans:
        latent = float(loan["_latent_risk"])
        origination = date.fromisoformat(str(loan["origination_date"]))
        previous_dpd = 0
        recent_misses: deque[int] = deque([0, 0, 0], maxlen=3)

        for month_index, snapshot in enumerate(months):
            account_age = (snapshot.year - origination.year) * 12 + snapshot.month - origination.month
            late_cycle_stress = max(0.0, (month_index - len(months) + 6) / 6.0)
            income_drop = int(rng.random() < 0.010 + latent * 0.040 + late_cycle_stress * 0.012)
            hardship = int(rng.random() < 0.007 + latent * 0.025 + income_drop * 0.10)

            delinquency_probability = _clamp(
                0.012 + latent * 0.105 + income_drop * 0.18 + hardship * 0.22 + (0.05 if previous_dpd else 0),
                0,
                0.75,
            )
            if rng.random() < delinquency_probability:
                severity_draw = rng.random() + latent * 0.30 + hardship * 0.20
                if severity_draw > 1.15:
                    dpd = 90
                elif severity_draw > 0.91:
                    dpd = 60
                elif severity_draw > 0.63:
                    dpd = 30
                else:
                    dpd = rng.randint(1, 29)
            elif previous_dpd and rng.random() < 0.38:
                dpd = max(0, previous_dpd - 30)
            else:
                dpd = 0

            missed_this_month = int(dpd >= 15)
            recent_misses.append(missed_this_month)
            missed_3m = sum(recent_misses)
            utilization = _clamp(
                rng.normalvariate(29 + latent * 48 + income_drop * 13 + hardship * 12, 13),
                1,
                100,
            )
            payment_ratio = _clamp(
                rng.normalvariate(1.02 - dpd / 150 - missed_3m * 0.08 - income_drop * 0.12, 0.08),
                0,
                1.25,
            )
            bureau_score = int(
                round(
                    _clamp(
                        rng.normalvariate(
                            766 - latent * 155 - missed_3m * 16 - income_drop * 24 - hardship * 31,
                            21,
                        ),
                        300,
                        850,
                    )
                )
            )
            required_payment_ratio = float(loan["installment_eur"]) * 12 / float(loan["_income"]) * 100
            dti = _clamp(float(loan["_external_dti"]) + required_payment_ratio, 1, 85)

            if loan["product_type"] == "Credit card":
                outstanding = float(loan["original_principal_eur"]) * utilization / 100
            else:
                remaining_ratio = max(0.04, 1 - account_age / int(loan["term_months"]))
                outstanding = float(loan["original_principal_eur"]) * remaining_ratio

            log_odds = (
                -3.80
                + latent * 0.85
                + max(0, 660 - bureau_score) * 0.012
                + (1.30 if dpd >= 30 else 0)
                + (0.85 if dpd >= 60 else 0)
                + missed_3m * 0.42
                + max(0, utilization - 75) * 0.018
                + max(0, 0.90 - payment_ratio) * 2.2
                + max(0, dti - 42) * 0.018
                + income_drop * 0.72
                + hardship * 0.90
                + late_cycle_stress * 0.18
            )
            probability = 1 / (1 + math.exp(-log_odds))
            default_next_3m = int(rng.random() < probability)

            rows.append(
                {
                    "loan_id": loan["loan_id"],
                    "snapshot_month": snapshot.isoformat(),
                    "account_age_months": account_age,
                    "outstanding_balance_eur": round(outstanding, 2),
                    "days_past_due": dpd,
                    "utilization_pct": round(utilization, 2),
                    "payment_ratio": round(payment_ratio, 4),
                    "missed_payments_3m": missed_3m,
                    "bureau_score": bureau_score,
                    "dti_pct": round(dti, 2),
                    "income_drop_flag": income_drop,
                    "hardship_flag": hardship,
                    "default_next_3m": default_next_3m,
                }
            )
            previous_dpd = dpd
    return rows


def generate_portfolio(
    output_dir: Path,
    n_loans: int = 2500,
    n_months: int = 21,
    seed: int = 42,
    start_month: date = date(2024, 1, 1),
) -> Dict[str, object]:
    """Generate and persist a reproducible, public-safe synthetic portfolio."""
    if n_loans < 20:
        raise ValueError("n_loans must be at least 20")
    if n_months < 9:
        raise ValueError("n_months must be at least 9 for a purged temporal split")
    if start_month.day != 1:
        raise ValueError("start_month must be the first day of a month")

    rng = random.Random(seed)
    customer_count = max(10, round(n_loans * 0.82))
    customers = _build_customers(rng, customer_count)
    loans = _build_loans(rng, n_loans, customers, start_month)
    months = _month_sequence(start_month, n_months)
    performance = _build_performance(rng, loans, months)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "customers.csv", customers, CUSTOMER_COLUMNS)
    _write_csv(output_dir / "loans.csv", loans, LOAN_COLUMNS)
    _write_csv(output_dir / "monthly_performance.csv", performance, PERFORMANCE_COLUMNS)

    positives = sum(int(row["default_next_3m"]) for row in performance)
    manifest: Dict[str, object] = {
        "dataset_name": "Synthetic Retail Credit Early-Warning Portfolio",
        "version": "1.0.0",
        "provenance": "Generated locally; contains no real people, accounts, or bank data.",
        "seed": seed,
        "customers": len(customers),
        "loans": len(loans),
        "monthly_snapshots": len(performance),
        "start_month": months[0].isoformat(),
        "end_month": months[-1].isoformat(),
        "simulated_target_rate": round(positives / len(performance), 6),
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    return manifest

