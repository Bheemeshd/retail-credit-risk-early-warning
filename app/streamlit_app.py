"""Interactive early-warning command center backed by the project SQLite database."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
DATABASE = REPO_ROOT / "data" / "processed" / "credit_risk.db"
METRICS_FILE = REPO_ROOT / "artifacts" / "model_metrics.json"

st.set_page_config(page_title="Retail Credit Risk EWS", page_icon="🏦", layout="wide")


@st.cache_data(show_spinner=False)
def query(sql: str, parameters: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(DATABASE) as connection:
        return pd.read_sql_query(sql, connection, params=parameters)


def format_eur(value: float) -> str:
    if value >= 1_000_000:
        return f"€{value / 1_000_000:,.1f}m"
    return f"€{value:,.0f}"


st.title("Retail Credit Risk · Early-Warning Command Center")
st.caption(
    "Public-safe portfolio demonstration built entirely from deterministic synthetic data. "
    "Scores prioritize analyst review; they are not credit decisions."
)

if not DATABASE.exists() or not METRICS_FILE.exists():
    st.error("Generated data is not available. From the repository root, run: `make pipeline`.")
    st.stop()

months = query("SELECT DISTINCT snapshot_month FROM model_scores ORDER BY snapshot_month DESC")["snapshot_month"].tolist()
products = query("SELECT DISTINCT product_type FROM loans ORDER BY product_type")["product_type"].tolist()

with st.sidebar:
    st.header("Portfolio filters")
    selected_month = st.selectbox("Snapshot", months)
    selected_products = st.multiselect("Product", products, default=products)
    selected_tiers = st.multiselect(
        "Risk tier", ["Critical", "High", "Monitor", "Low"], default=["Critical", "High", "Monitor", "Low"]
    )
    st.divider()
    st.caption("Synthetic data · Model v1 · Monthly monitoring")

if not selected_products or not selected_tiers:
    st.warning("Select at least one product and one risk tier.")
    st.stop()

product_marks = ",".join("?" for _ in selected_products)
tier_marks = ",".join("?" for _ in selected_tiers)
parameters = (selected_month, *selected_products, *selected_tiers)
filtered_sql = f"""
    SELECT q.*, p.default_next_3m
    FROM vw_scored_ews_queue AS q
    JOIN monthly_performance AS p
      ON q.loan_id = p.loan_id AND q.snapshot_month = p.snapshot_month
    WHERE q.snapshot_month = ?
      AND q.product_type IN ({product_marks})
      AND q.risk_tier IN ({tier_marks})
"""
portfolio = query(filtered_sql, parameters)

metrics_columns = st.columns(5)
metrics_columns[0].metric("Accounts", f"{len(portfolio):,}")
metrics_columns[1].metric("Exposure", format_eur(float(portfolio["outstanding_balance_eur"].sum())))
metrics_columns[2].metric("DPD 30+", f"{100 * (portfolio['days_past_due'] >= 30).mean():.2f}%")
metrics_columns[3].metric("Critical / high", f"{100 * portfolio['risk_tier'].isin(['Critical', 'High']).mean():.1f}%")
metrics_columns[4].metric("Avg. score", f"{100 * portfolio['predicted_probability'].mean():.2f}%")

overview_tab, queue_tab, model_tab, governance_tab = st.tabs(
    ["Portfolio overview", "Action queue", "Model performance", "Controls & limitations"]
)

with overview_tab:
    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Portfolio trend")
        trend = query(
            """
            SELECT snapshot_month, dpd30_rate_pct, simulated_default_next_3m_pct
            FROM vw_monthly_portfolio_kpis ORDER BY snapshot_month
            """
        ).set_index("snapshot_month")
        trend.columns = ["DPD 30+ %", "Synthetic 3m target %"]
        st.line_chart(trend)
    with right:
        st.subheader("Selected exposure by tier")
        tier_exposure = (
            portfolio.groupby("risk_tier", as_index=False)["outstanding_balance_eur"]
            .sum()
            .set_index("risk_tier")
        )
        st.bar_chart(tier_exposure, horizontal=True)

    st.subheader("Product risk view")
    product_view = (
        portfolio.groupby("product_type")
        .agg(
            accounts=("loan_id", "count"),
            exposure_eur=("outstanding_balance_eur", "sum"),
            average_score=("predicted_probability", "mean"),
            synthetic_target_rate=("default_next_3m", "mean"),
        )
        .sort_values("exposure_eur", ascending=False)
    )
    st.dataframe(
        product_view.style.format(
            {"exposure_eur": "€{:,.0f}", "average_score": "{:.2%}", "synthetic_target_rate": "{:.2%}"}
        ),
        use_container_width=True,
    )

with queue_tab:
    st.subheader("Ranked analyst-review queue")
    st.info("Review customer context and reason indicators before any outreach. Never use this queue for automated adverse action.")
    queue = portfolio.sort_values(["predicted_probability", "outstanding_balance_eur"], ascending=False).copy()
    queue["predicted_risk_pct"] = 100 * queue["predicted_probability"]
    queue = queue[
        [
            "loan_id",
            "product_type",
            "risk_tier",
            "predicted_risk_pct",
            "outstanding_balance_eur",
            "days_past_due",
            "bureau_score",
            "missed_payments_3m",
            "income_drop_flag",
            "hardship_flag",
        ]
    ].head(200)
    st.dataframe(
        queue.style.format({"predicted_risk_pct": "{:.2f}%", "outstanding_balance_eur": "€{:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download filtered queue (CSV)",
        queue.to_csv(index=False).encode("utf-8"),
        file_name=f"synthetic_ews_queue_{selected_month}.csv",
        mime="text/csv",
    )

with model_tab:
    metrics = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    holdout = metrics["holdout"]
    st.subheader("Purged temporal holdout")
    metric_cols = st.columns(5)
    metric_cols[0].metric("ROC-AUC", f"{holdout['roc_auc']:.3f}")
    metric_cols[1].metric("Average precision", f"{holdout['average_precision']:.3f}")
    metric_cols[2].metric("Brier score", f"{holdout['brier_score']:.3f}")
    metric_cols[3].metric("Top-decile recall", f"{holdout['top_decile']['recall']:.1%}")
    metric_cols[4].metric("Top-decile lift", f"{holdout['top_decile']['lift_vs_portfolio']:.1f}x")
    st.caption(
        f"Train: {metrics['split']['train_start']} to {metrics['split']['train_end']} · "
        f"Embargo: {metrics['split']['embargo_start']} to {metrics['split']['embargo_end']} · "
        f"Holdout: {metrics['split']['test_start']} to {metrics['split']['test_end']}"
    )
    calibration = pd.DataFrame(holdout["calibration_bins"]).set_index("mean_predicted_probability")
    st.subheader("Calibration by equal-count score bin")
    st.line_chart(calibration[["observed_target_rate"]])
    st.warning("These are synthetic-data metrics designed to demonstrate method, not claims about production performance.")

with governance_tab:
    st.subheader("Responsible-use boundary")
    st.markdown(
        """
        - Intended for monthly portfolio monitoring and human-reviewed supportive outreach.
        - Excludes customer ID, region, birth year, employment, and home ownership from modeling.
        - Requires independent validation, fairness/proxy testing, calibration and drift monitoring, data reconciliation, and audit logs before real use.
        - Must not determine approval, pricing, limits, collections treatment, or adverse action.
        - GDPR lawful basis, purpose limitation, minimization, retention, access, explanation, and human-review controls require specialist sign-off.
        """
    )
    st.subheader("Known analytical limitations")
    st.markdown(
        "Synthetic outcomes encode designed relationships; repeated account snapshots are correlated; "
        "macroeconomic and policy shifts are simplified; uncertainty intervals and cost optimization are out of scope."
    )

