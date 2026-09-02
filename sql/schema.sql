PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    birth_year INTEGER NOT NULL CHECK (birth_year BETWEEN 1920 AND 2010),
    region TEXT NOT NULL,
    employment_status TEXT NOT NULL,
    annual_income_eur REAL NOT NULL CHECK (annual_income_eur > 0),
    months_with_bank INTEGER NOT NULL CHECK (months_with_bank >= 0),
    home_ownership TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    origination_date TEXT NOT NULL,
    product_type TEXT NOT NULL CHECK (
        product_type IN ('Personal loan', 'Credit card', 'Auto loan', 'Mortgage')
    ),
    original_principal_eur REAL NOT NULL CHECK (original_principal_eur > 0),
    term_months INTEGER NOT NULL CHECK (term_months > 0),
    apr_pct REAL NOT NULL CHECK (apr_pct >= 0),
    installment_eur REAL NOT NULL CHECK (installment_eur > 0),
    purpose TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monthly_performance (
    loan_id TEXT NOT NULL REFERENCES loans(loan_id),
    snapshot_month TEXT NOT NULL,
    account_age_months INTEGER NOT NULL CHECK (account_age_months >= 0),
    outstanding_balance_eur REAL NOT NULL CHECK (outstanding_balance_eur >= 0),
    days_past_due INTEGER NOT NULL CHECK (days_past_due BETWEEN 0 AND 180),
    utilization_pct REAL NOT NULL CHECK (utilization_pct BETWEEN 0 AND 100),
    payment_ratio REAL NOT NULL CHECK (payment_ratio BETWEEN 0 AND 1.5),
    missed_payments_3m INTEGER NOT NULL CHECK (missed_payments_3m BETWEEN 0 AND 3),
    bureau_score INTEGER NOT NULL CHECK (bureau_score BETWEEN 300 AND 850),
    dti_pct REAL NOT NULL CHECK (dti_pct BETWEEN 0 AND 100),
    income_drop_flag INTEGER NOT NULL CHECK (income_drop_flag IN (0, 1)),
    hardship_flag INTEGER NOT NULL CHECK (hardship_flag IN (0, 1)),
    default_next_3m INTEGER NOT NULL CHECK (default_next_3m IN (0, 1)),
    PRIMARY KEY (loan_id, snapshot_month)
);

CREATE TABLE IF NOT EXISTS model_scores (
    loan_id TEXT NOT NULL,
    snapshot_month TEXT NOT NULL,
    predicted_probability REAL NOT NULL CHECK (predicted_probability BETWEEN 0 AND 1),
    risk_tier TEXT NOT NULL CHECK (risk_tier IN ('Low', 'Monitor', 'High', 'Critical')),
    data_split TEXT NOT NULL CHECK (data_split IN ('train', 'embargo', 'test')),
    model_version TEXT NOT NULL,
    PRIMARY KEY (loan_id, snapshot_month),
    FOREIGN KEY (loan_id, snapshot_month)
        REFERENCES monthly_performance(loan_id, snapshot_month)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pipeline_metadata (
    metadata_key TEXT PRIMARY KEY,
    metadata_value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_loans_customer ON loans(customer_id);
CREATE INDEX IF NOT EXISTS idx_performance_month ON monthly_performance(snapshot_month);
CREATE INDEX IF NOT EXISTS idx_performance_target ON monthly_performance(default_next_3m);
CREATE INDEX IF NOT EXISTS idx_performance_dpd ON monthly_performance(days_past_due);
CREATE INDEX IF NOT EXISTS idx_scores_month_tier ON model_scores(snapshot_month, risk_tier);

