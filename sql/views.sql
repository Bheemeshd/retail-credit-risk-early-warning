DROP VIEW IF EXISTS vw_loan_risk_features;
CREATE VIEW vw_loan_risk_features AS
SELECT
    p.loan_id,
    p.snapshot_month,
    l.customer_id,
    l.product_type,
    l.original_principal_eur,
    l.apr_pct,
    l.installment_eur,
    c.region,
    c.employment_status,
    c.annual_income_eur,
    c.home_ownership,
    p.account_age_months,
    p.outstanding_balance_eur,
    p.days_past_due,
    p.utilization_pct,
    p.payment_ratio,
    p.missed_payments_3m,
    p.bureau_score,
    p.dti_pct,
    p.income_drop_flag,
    p.hardship_flag,
    p.default_next_3m,
    CASE
        WHEN p.days_past_due >= 60 OR p.missed_payments_3m >= 2 THEN 'Critical'
        WHEN p.days_past_due >= 30 OR p.hardship_flag = 1 THEN 'High'
        WHEN p.bureau_score < 640 OR p.utilization_pct >= 80 OR p.income_drop_flag = 1 THEN 'Monitor'
        ELSE 'Low'
    END AS rules_based_ews_tier
FROM monthly_performance AS p
JOIN loans AS l ON p.loan_id = l.loan_id
JOIN customers AS c ON l.customer_id = c.customer_id;

DROP VIEW IF EXISTS vw_monthly_portfolio_kpis;
CREATE VIEW vw_monthly_portfolio_kpis AS
SELECT
    snapshot_month,
    COUNT(*) AS active_accounts,
    ROUND(SUM(outstanding_balance_eur), 2) AS exposure_eur,
    ROUND(AVG(days_past_due), 2) AS avg_days_past_due,
    ROUND(100.0 * AVG(CASE WHEN days_past_due >= 30 THEN 1.0 ELSE 0.0 END), 2) AS dpd30_rate_pct,
    ROUND(100.0 * AVG(CASE WHEN days_past_due >= 90 THEN 1.0 ELSE 0.0 END), 2) AS dpd90_rate_pct,
    ROUND(100.0 * AVG(default_next_3m), 2) AS simulated_default_next_3m_pct,
    ROUND(AVG(bureau_score), 1) AS avg_bureau_score
FROM monthly_performance
GROUP BY snapshot_month;

DROP VIEW IF EXISTS vw_product_risk_summary;
CREATE VIEW vw_product_risk_summary AS
SELECT
    p.snapshot_month,
    l.product_type,
    COUNT(*) AS active_accounts,
    ROUND(SUM(p.outstanding_balance_eur), 2) AS exposure_eur,
    ROUND(100.0 * AVG(CASE WHEN p.days_past_due >= 30 THEN 1.0 ELSE 0.0 END), 2) AS dpd30_rate_pct,
    ROUND(100.0 * AVG(p.default_next_3m), 2) AS simulated_target_rate_pct
FROM monthly_performance AS p
JOIN loans AS l ON p.loan_id = l.loan_id
GROUP BY p.snapshot_month, l.product_type;

DROP VIEW IF EXISTS vw_scored_ews_queue;
CREATE VIEW vw_scored_ews_queue AS
SELECT
    s.snapshot_month,
    s.loan_id,
    f.product_type,
    f.outstanding_balance_eur,
    f.days_past_due,
    f.bureau_score,
    f.missed_payments_3m,
    f.income_drop_flag,
    f.hardship_flag,
    s.predicted_probability,
    s.risk_tier,
    s.data_split,
    ROW_NUMBER() OVER (
        PARTITION BY s.snapshot_month
        ORDER BY s.predicted_probability DESC, f.outstanding_balance_eur DESC
    ) AS monthly_priority_rank
FROM model_scores AS s
JOIN vw_loan_risk_features AS f
  ON s.loan_id = f.loan_id AND s.snapshot_month = f.snapshot_month;

