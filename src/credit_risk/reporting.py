"""Dependency-light SVG charts and recruiter-facing analytical reports."""

from __future__ import annotations

import csv
import html
import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


INK = "#172033"
MUTED = "#667085"
GRID = "#D7DEE8"
NAVY = "#193B67"
TEAL = "#0F8B8D"
AMBER = "#F4A261"
CORAL = "#E76F51"
PALE = "#F4F7FB"


def _write_svg(path: Path, body: str, width: int = 900, height: int = 520) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        "<style>text{font-family:Inter,Arial,sans-serif}</style>"
        f'<rect width="100%" height="100%" fill="white" rx="18"/>{body}</svg>'
    )
    path.write_text(document, encoding="utf-8")


def _text(x: float, y: float, value: object, size: int = 13, color: str = INK, weight: int = 400, anchor: str = "start") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(value))}</text>'
    )


def _money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"€{value / 1_000_000:,.1f}m"
    if abs(value) >= 1_000:
        return f"€{value / 1_000:,.1f}k"
    return f"€{value:,.0f}"


def _trend_chart(path: Path, rows: Sequence[Tuple[object, ...]]) -> None:
    width, height = 900, 500
    left, top, plot_width, plot_height = 75, 85, 770, 330
    series = [
        ("DPD 30+ rate", [float(row[4]) for row in rows], NAVY),
        ("Synthetic 3m target", [float(row[6]) for row in rows], CORAL),
    ]
    maximum = max(max(values) for _, values, _ in series)
    maximum = max(1.0, maximum * 1.18)
    body = _text(46, 42, "Portfolio risk trend", 24, INK, 700)
    body += _text(46, 66, "Monthly arrears and simulated forward outcome (%)", 13, MUTED)
    for tick in range(6):
        y = top + plot_height - tick * plot_height / 5
        value = maximum * tick / 5
        body += f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" stroke="{GRID}"/>'
        body += _text(left - 12, y + 4, f"{value:.1f}%", 11, MUTED, anchor="end")
    x_step = plot_width / max(1, len(rows) - 1)
    for series_index, (name, values, color) in enumerate(series):
        points = []
        for index, value in enumerate(values):
            x = left + index * x_step
            y = top + plot_height - value / maximum * plot_height
            points.append(f"{x:.1f},{y:.1f}")
        body += f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="3"/>'
        body += f'<line x1="{585 + series_index * 145}" y1="43" x2="{610 + series_index * 145}" y2="43" stroke="{color}" stroke-width="4"/>'
        body += _text(615 + series_index * 145, 47, name, 11, MUTED)
    label_indexes = sorted(set([0, len(rows) // 2, len(rows) - 1]))
    for index in label_indexes:
        x = left + index * x_step
        body += _text(x, top + plot_height + 27, str(rows[index][0])[:7], 11, MUTED, anchor="middle")
    body += _text(45, 476, "Source: deterministic synthetic portfolio; not actual bank performance", 11, MUTED)
    _write_svg(path, body, width, height)


def _coefficient_chart(path: Path, coefficient_rows: Sequence[Dict[str, str]]) -> None:
    selected = sorted(coefficient_rows, key=lambda row: abs(float(row["coefficient_per_sd"])), reverse=True)[:10]
    width, height = 900, 570
    left, top, bar_width, row_height = 265, 90, 520, 39
    maximum = max(abs(float(row["coefficient_per_sd"])) for row in selected) or 1
    body = _text(46, 42, "Model drivers", 24, INK, 700)
    body += _text(46, 66, "Standardized logistic coefficients; direction is associative in synthetic data", 13, MUTED)
    for index, row in enumerate(selected):
        value = float(row["coefficient_per_sd"])
        y = top + index * row_height
        width_value = abs(value) / maximum * bar_width
        color = CORAL if value >= 0 else TEAL
        body += _text(left - 15, y + 18, row["feature"].replace("_", " "), 12, INK, anchor="end")
        body += f'<rect x="{left}" y="{y}" width="{bar_width}" height="23" rx="5" fill="{PALE}"/>'
        body += f'<rect x="{left}" y="{y}" width="{width_value:.1f}" height="23" rx="5" fill="{color}"/>'
        body += _text(left + width_value + 8, y + 17, f"{value:+.2f}", 11, INK, 600)
    body += _text(46, 536, "Positive coefficients increase estimated risk; negative coefficients reduce it, holding other features constant.", 11, MUTED)
    _write_svg(path, body, width, height)


def _calibration_chart(path: Path, bins: Sequence[Dict[str, object]]) -> None:
    width, height = 650, 570
    left, top, size = 80, 85, 410
    max_value = max(
        0.10,
        max(float(row["mean_predicted_probability"]) for row in bins),
        max(float(row["observed_target_rate"]) for row in bins),
    ) * 1.10
    body = _text(40, 40, "Holdout calibration", 24, INK, 700)
    body += _text(40, 64, "Equal-count bins on the purged temporal holdout", 13, MUTED)
    for tick in range(6):
        offset = tick * size / 5
        value = max_value * tick / 5
        x = left + offset
        y = top + size - offset
        body += f'<line x1="{left}" y1="{y:.1f}" x2="{left + size}" y2="{y:.1f}" stroke="{GRID}"/>'
        body += f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + size}" stroke="{GRID}"/>'
        body += _text(left - 10, y + 4, f"{value * 100:.0f}%", 10, MUTED, anchor="end")
        body += _text(x, top + size + 22, f"{value * 100:.0f}%", 10, MUTED, anchor="middle")
    body += f'<line x1="{left}" y1="{top + size}" x2="{left + size}" y2="{top}" stroke="{MUTED}" stroke-dasharray="6 6"/>'
    for row in bins:
        predicted = float(row["mean_predicted_probability"])
        observed = float(row["observed_target_rate"])
        x = left + predicted / max_value * size
        y = top + size - observed / max_value * size
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{NAVY}" stroke="white" stroke-width="2"/>'
    body += _text(left + size / 2, 548, "Mean predicted probability", 12, INK, 600, "middle")
    body += f'<text x="20" y="{top + size / 2}" fill="{INK}" font-size="12" font-weight="600" transform="rotate(-90 20 {top + size / 2})" text-anchor="middle">Observed synthetic target rate</text>'
    _write_svg(path, body, width, height)


def _tier_chart(path: Path, tiers: Sequence[Tuple[str, int, float, float]]) -> None:
    width, height = 850, 430
    left, top, plot_width, row_height = 190, 100, 550, 55
    maximum = max(float(row[2]) for row in tiers) or 1
    colors = {"Critical": CORAL, "High": AMBER, "Monitor": NAVY, "Low": TEAL}
    body = _text(42, 42, "Latest-month exposure by risk tier", 24, INK, 700)
    body += _text(42, 67, "Tiers are relative score bands learned from training-period percentiles", 13, MUTED)
    for index, (tier, accounts, exposure, target_rate) in enumerate(tiers):
        y = top + index * row_height
        current_width = exposure / maximum * plot_width
        body += _text(left - 14, y + 23, tier, 13, INK, 600, "end")
        body += f'<rect x="{left}" y="{y}" width="{plot_width}" height="31" rx="7" fill="{PALE}"/>'
        body += f'<rect x="{left}" y="{y}" width="{current_width:.1f}" height="31" rx="7" fill="{colors.get(tier, NAVY)}"/>'
        body += _text(left + current_width + 9, y + 21, f"{_money(exposure)} · {accounts:,} accts · {target_rate:.1f}% target", 11, INK)
    body += _text(42, 390, "Synthetic labels and balances; tiers are for queue prioritization, not automated decisions.", 11, MUTED)
    _write_svg(path, body, width, height)


def _dashboard_preview(
    path: Path,
    latest: Tuple[object, ...],
    holdout: Dict[str, object],
    trend_rows: Sequence[Tuple[object, ...]],
    tiers: Sequence[Tuple[str, int, float, float]],
) -> None:
    width, height = 1200, 720
    body = f'<rect width="1200" height="720" fill="#F2F5FA"/><rect x="0" y="0" width="1200" height="74" fill="{NAVY}"/>'
    body += _text(36, 47, "Retail Credit Risk · Early-Warning Command Center", 25, "white", 700)
    body += _text(1160, 46, str(latest[0])[:7], 13, "white", 600, "end")
    cards = [
        ("Active accounts", f"{int(latest[1]):,}"),
        ("Outstanding exposure", _money(float(latest[2]))),
        ("DPD 30+ rate", f"{float(latest[4]):.2f}%"),
        ("Holdout ROC-AUC", f"{float(holdout['roc_auc']):.3f}"),
    ]
    for index, (label, value) in enumerate(cards):
        x = 30 + index * 290
        body += f'<rect x="{x}" y="98" width="270" height="104" fill="white" rx="14"/>'
        body += _text(x + 20, 129, label, 12, MUTED, 600)
        body += _text(x + 20, 175, value, 28, INK, 700)

    body += '<rect x="30" y="226" width="740" height="450" fill="white" rx="14"/>'
    body += _text(54, 263, "Risk movement", 18, INK, 700)
    left, top, chart_width, chart_height = 75, 300, 640, 270
    values = [float(row[4]) for row in trend_rows]
    maximum = max(values) * 1.2 or 1
    for tick in range(5):
        y = top + tick * chart_height / 4
        body += f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="{GRID}"/>'
    points = []
    for index, value in enumerate(values):
        x = left + index * chart_width / max(1, len(values) - 1)
        y = top + chart_height - value / maximum * chart_height
        points.append(f"{x:.1f},{y:.1f}")
    body += f'<polyline points="{" ".join(points)}" fill="none" stroke="{NAVY}" stroke-width="4"/>'
    body += _text(left, 606, str(trend_rows[0][0])[:7], 11, MUTED)
    body += _text(left + chart_width, 606, str(trend_rows[-1][0])[:7], 11, MUTED, anchor="end")
    body += _text(55, 648, "DPD 30+ rate · synthetic portfolio", 11, MUTED)

    body += '<rect x="795" y="226" width="375" height="450" fill="white" rx="14"/>'
    body += _text(820, 263, "Action queue mix", 18, INK, 700)
    colors = {"Critical": CORAL, "High": AMBER, "Monitor": NAVY, "Low": TEAL}
    total_accounts = sum(int(row[1]) for row in tiers)
    for index, (tier, accounts, exposure, target_rate) in enumerate(tiers):
        y = 305 + index * 78
        share = accounts / total_accounts if total_accounts else 0
        body += _text(820, y, tier, 13, INK, 600)
        body += _text(1140, y, f"{accounts:,} · {share:.0%}", 12, MUTED, anchor="end")
        body += f'<rect x="820" y="{y + 14}" width="320" height="18" fill="{PALE}" rx="6"/>'
        body += f'<rect x="820" y="{y + 14}" width="{320 * share:.1f}" height="18" fill="{colors[tier]}" rx="6"/>'
        body += _text(820, y + 50, f"{_money(exposure)} exposure · {target_rate:.1f}% observed target", 11, MUTED)
    body += _text(820, 640, "Prioritization aid only", 11, CORAL, 700)
    _write_svg(path, body, width, height)


def _markdown_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def generate_reports(database_path: Path, artifact_dir: Path, report_dir: Path) -> Dict[str, object]:
    """Generate static charts, an executive memo, a model card, and SQL extracts."""
    database_path = Path(database_path)
    artifact_dir = Path(artifact_dir)
    report_dir = Path(report_dir)
    chart_dir = artifact_dir / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    metrics = json.loads((artifact_dir / "model_metrics.json").read_text(encoding="utf-8"))
    with (artifact_dir / "model_coefficients.csv").open(newline="", encoding="utf-8") as handle:
        coefficient_rows = list(csv.DictReader(handle))

    with sqlite3.connect(database_path) as connection:
        trend_rows = connection.execute(
            "SELECT * FROM vw_monthly_portfolio_kpis ORDER BY snapshot_month"
        ).fetchall()
        latest = trend_rows[-1]
        latest_month = str(latest[0])
        tiers = connection.execute(
            """
            SELECT q.risk_tier, COUNT(*), SUM(q.outstanding_balance_eur),
                   100.0 * AVG(p.default_next_3m)
            FROM vw_scored_ews_queue AS q
            JOIN monthly_performance AS p
              ON q.loan_id = p.loan_id AND q.snapshot_month = p.snapshot_month
            WHERE q.snapshot_month = ?
            GROUP BY q.risk_tier
            ORDER BY CASE q.risk_tier
                WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Monitor' THEN 3 ELSE 4 END
            """,
            (latest_month,),
        ).fetchall()
        products = connection.execute(
            """
            SELECT product_type, active_accounts, exposure_eur, dpd30_rate_pct, simulated_target_rate_pct
            FROM vw_product_risk_summary WHERE snapshot_month = ? ORDER BY exposure_eur DESC
            """,
            (latest_month,),
        ).fetchall()
        top_queue = connection.execute(
            """
            SELECT monthly_priority_rank, loan_id, product_type, ROUND(outstanding_balance_eur, 0),
                   days_past_due, bureau_score, ROUND(100 * predicted_probability, 2), risk_tier
            FROM vw_scored_ews_queue WHERE snapshot_month = ?
            ORDER BY monthly_priority_rank LIMIT 10
            """,
            (latest_month,),
        ).fetchall()

    holdout = metrics["holdout"]
    _trend_chart(chart_dir / "portfolio_risk_trend.svg", trend_rows)
    _coefficient_chart(chart_dir / "feature_importance.svg", coefficient_rows)
    _calibration_chart(chart_dir / "holdout_calibration.svg", holdout["calibration_bins"])
    _tier_chart(chart_dir / "latest_risk_tier_exposure.svg", tiers)
    _dashboard_preview(artifact_dir / "dashboard_preview.svg", latest, holdout, trend_rows, tiers)

    summary = f"""# Executive summary — Retail Credit Early-Warning Analytics

**Reporting month:** {latest_month[:7]}  
**Data status:** 100% synthetic and public-safe. No real customers, accounts, or bank results.

## Portfolio pulse

- **{int(latest[1]):,} active loan accounts** with **{_money(float(latest[2]))}** outstanding exposure.
- **DPD 30+ rate:** {float(latest[4]):.2f}% at the latest snapshot.
- **Simulated next-three-month target rate:** {float(latest[6]):.2f}% at the latest snapshot.
- **Average bureau score:** {float(latest[7]):.0f}.

## Early-warning model

The interpretable logistic model was evaluated on a future three-month holdout after a
three-month embargo. On this synthetic holdout it achieved **ROC-AUC {float(holdout['roc_auc']):.3f}**,
**average precision {float(holdout['average_precision']):.3f}**, and **Brier score
{float(holdout['brier_score']):.3f}**. At the operating point set from the training-period top
decile, the holdout queue captured **{100 * float(holdout['top_decile']['recall']):.1f}%** of
simulated targets with **{float(holdout['top_decile']['lift_vs_portfolio']):.1f}x lift** versus the
holdout portfolio average.

These values demonstrate analytical workflow, not live model quality. A real deployment would
require representative bank data, outcome maturation, bias and stability reviews, independent
validation, monitoring, controls, and human decision ownership.

## Recommended operating workflow

1. Refresh monthly snapshots and validate source reconciliation.
2. Rank the contact queue by model score, then review reason indicators and exposure.
3. Route customers to supportive outreach or manual review; do not automate adverse action.
4. Track contact coverage, cures, roll rates, calibration, segment stability, and overrides.

## Product view ({latest_month[:7]})

{_markdown_table(
    ['Product', 'Accounts', 'Exposure', 'DPD 30+ %', 'Synthetic target %'],
    [(row[0], f'{int(row[1]):,}', _money(float(row[2])), f'{float(row[3]):.2f}', f'{float(row[4]):.2f}') for row in products]
)}
"""
    (report_dir / "executive_summary.md").write_text(summary, encoding="utf-8")

    model_card = f"""# Model card — {metrics['model_version']}

## Intended use

Monthly prioritization of existing retail-credit accounts for analyst review and supportive
early outreach. This portfolio artifact uses synthetic data only and is not approved for any
real lending, pricing, collections, limit, or adverse-action decision.

## Model and features

L2-regularized logistic regression implemented with iteratively reweighted least squares.
Continuous features are standardized using training-period statistics. Inputs include account
behavior (delinquency, payment ratio, utilization), affordability indicators, balance, bureau
score, APR, account age, and hardship signals. Customer ID, region, age/birth year, employment,
home ownership, and the target are excluded from the model.

## Validation design

- Training: {metrics['split']['train_start']} through {metrics['split']['train_end']}
- Embargo: {metrics['split']['embargo_start']} through {metrics['split']['embargo_end']}
- Holdout: {metrics['split']['test_start']} through {metrics['split']['test_end']}
- Forward target horizon: {metrics['split']['target_horizon_months']} months
- Holdout rows / positives: {holdout['rows']:,} / {holdout['positives']:,}

## Holdout metrics (synthetic)

{_markdown_table(
    ['Metric', 'Value'],
    [
        ('ROC-AUC', f"{float(holdout['roc_auc']):.4f}"),
        ('Average precision', f"{float(holdout['average_precision']):.4f}"),
        ('Brier score', f"{float(holdout['brier_score']):.4f}"),
        ('Log loss', f"{float(holdout['log_loss']):.4f}"),
        ('Top-decile recall', f"{100 * float(holdout['top_decile']['recall']):.2f}%"),
        ('Top-decile lift', f"{float(holdout['top_decile']['lift_vs_portfolio']):.2f}x"),
    ]
)}

## Material limitations

- Synthetic feature/outcome relationships are designed, so performance cannot establish real-world utility.
- Overlapping account snapshots are correlated; uncertainty intervals are not reported.
- The same accounts may appear across time partitions, consistent with portfolio monitoring.
- Calibration and ranking may shift by product, geography, economy, policy, and data quality.
- Fair-lending, GDPR, explainability, privacy, human-oversight, and model-risk requirements need specialist review.
- Risk tiers are relative percentile bands, not absolute probabilities of customer default.

## Minimum production controls

Independent validation; protected-class and proxy testing; stability and calibration monitoring;
data lineage and reconciliation; outcome-maturity controls; champion/challenger comparison;
documented overrides; access control; audit logs; customer-support safeguards; and defined model
owner, approver, review cadence, escalation thresholds, and retirement criteria.
"""
    (report_dir / "model_card.md").write_text(model_card, encoding="utf-8")

    sql_results = f"""# Selected SQL outputs

Generated from the SQLite analytical layer for snapshot **{latest_month[:7]}**.

## Product portfolio

{_markdown_table(
    ['Product', 'Accounts', 'Exposure EUR', 'DPD 30+ %', 'Synthetic target %'],
    [(row[0], int(row[1]), f'{float(row[2]):,.2f}', f'{float(row[3]):.2f}', f'{float(row[4]):.2f}') for row in products]
)}

## Top 10 analyst-review candidates

{_markdown_table(
    ['Rank', 'Synthetic loan', 'Product', 'Exposure EUR', 'DPD', 'Bureau', 'Score %', 'Tier'],
    [(int(row[0]), row[1], row[2], f'{float(row[3]):,.0f}', int(row[4]), int(row[5]), f'{float(row[6]):.2f}', row[7]) for row in top_queue]
)}

Identifiers above refer only to generated records. Scores prioritize review and are not decisions.
"""
    (report_dir / "sql_results.md").write_text(sql_results, encoding="utf-8")
    return {
        "latest_month": latest_month,
        "latest_accounts": int(latest[1]),
        "latest_exposure_eur": float(latest[2]),
        "holdout_roc_auc": float(holdout["roc_auc"]),
        "charts": 5,
    }
