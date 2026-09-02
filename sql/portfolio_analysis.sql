-- 1) Executive KPI trend: volume, exposure, arrears and simulated forward outcome.
SELECT *
FROM vw_monthly_portfolio_kpis
ORDER BY snapshot_month;

-- 2) Product concentration and risk at the latest available month.
WITH latest AS (SELECT MAX(snapshot_month) AS snapshot_month FROM monthly_performance)
SELECT
    product_type,
    active_accounts,
    exposure_eur,
    ROUND(100.0 * exposure_eur / SUM(exposure_eur) OVER (), 2) AS exposure_share_pct,
    dpd30_rate_pct,
    simulated_target_rate_pct
FROM vw_product_risk_summary
WHERE snapshot_month = (SELECT snapshot_month FROM latest)
ORDER BY exposure_eur DESC;

-- 3) Month-to-month delinquency roll rates using a window function.
WITH states AS (
    SELECT
        loan_id,
        snapshot_month,
        CASE
            WHEN days_past_due = 0 THEN 'Current'
            WHEN days_past_due < 30 THEN 'DPD 1-29'
            WHEN days_past_due < 60 THEN 'DPD 30-59'
            WHEN days_past_due < 90 THEN 'DPD 60-89'
            ELSE 'DPD 90+'
        END AS current_state,
        LAG(
            CASE
                WHEN days_past_due = 0 THEN 'Current'
                WHEN days_past_due < 30 THEN 'DPD 1-29'
                WHEN days_past_due < 60 THEN 'DPD 30-59'
                WHEN days_past_due < 90 THEN 'DPD 60-89'
                ELSE 'DPD 90+'
            END
        ) OVER (PARTITION BY loan_id ORDER BY snapshot_month) AS prior_state
    FROM monthly_performance
)
SELECT
    prior_state,
    current_state,
    COUNT(*) AS transitions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY prior_state), 2) AS roll_rate_pct
FROM states
WHERE prior_state IS NOT NULL
GROUP BY prior_state, current_state
ORDER BY prior_state, transitions DESC;

-- 4) Latest model-ranked action queue. Probability is prioritization support,
-- not an automated credit decision.
SELECT
    monthly_priority_rank,
    loan_id,
    product_type,
    ROUND(outstanding_balance_eur, 2) AS exposure_eur,
    days_past_due,
    bureau_score,
    missed_payments_3m,
    ROUND(100.0 * predicted_probability, 2) AS predicted_risk_pct,
    risk_tier
FROM vw_scored_ews_queue
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM model_scores)
ORDER BY monthly_priority_rank
LIMIT 50;

-- 5) Exposure captured by each relative risk tier at the latest month.
SELECT
    q.risk_tier,
    COUNT(*) AS accounts,
    ROUND(SUM(q.outstanding_balance_eur), 2) AS exposure_eur,
    ROUND(100.0 * AVG(p.default_next_3m), 2) AS simulated_target_rate_pct
FROM vw_scored_ews_queue AS q
JOIN monthly_performance AS p
  ON q.loan_id = p.loan_id AND q.snapshot_month = p.snapshot_month
WHERE q.snapshot_month = (SELECT MAX(snapshot_month) FROM model_scores)
GROUP BY q.risk_tier
ORDER BY CASE q.risk_tier
    WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Monitor' THEN 3 ELSE 4 END;
