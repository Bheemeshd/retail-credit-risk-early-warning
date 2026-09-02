# Data dictionary

All records are generated. Currency is EUR. Dates use ISO 8601. Snapshot months are represented by
the first calendar day of each month.

## customers.csv / customers

Grain: one row per synthetic customer.

| Field | Type | Definition | Model use |
| --- | --- | --- | --- |
| customer_id | text | Generated stable customer key | Excluded |
| birth_year | integer | Simulated year of birth | Excluded |
| region | text | North, South, East, West, or Central | Excluded |
| employment_status | text | Salaried, self-employed, retired, or contract | Excluded |
| annual_income_eur | decimal | Simulated gross annual income | Indirectly represented by generated DTI; raw value excluded |
| months_with_bank | integer | Simulated relationship tenure | Excluded |
| home_ownership | text | Owner, mortgage, tenant, or other | Excluded |

## loans.csv / loans

Grain: one row per synthetic loan account.

| Field | Type | Definition | Model use |
| --- | --- | --- | --- |
| loan_id | text | Generated stable account key | Excluded; joins only |
| customer_id | text | Foreign key to customers | Excluded |
| origination_date | date | Simulated account origination month | Used to derive account age only |
| product_type | text | Personal loan, credit card, auto loan, or mortgage | Credit-card indicator only |
| original_principal_eur | decimal | Original amount or revolving limit | Excluded |
| term_months | integer | Contractual or modeled term | Excluded |
| apr_pct | decimal | Annual percentage rate | Included |
| installment_eur | decimal | Scheduled payment or modeled minimum | Used in DTI generation; excluded directly |
| purpose | text | Synthetic product purpose | Excluded |

## monthly_performance.csv / monthly_performance

Grain: one row per loan and snapshot month.

| Field | Type | Definition | Model use |
| --- | --- | --- | --- |
| loan_id | text | Foreign key to loans | Excluded; joins only |
| snapshot_month | date | Observation month | Split key; excluded from features |
| account_age_months | integer | Months from origination to snapshot | Included |
| outstanding_balance_eur | decimal | Month-end outstanding balance | Log-transformed and included |
| days_past_due | integer | Days the account is past its due date | Included |
| utilization_pct | decimal | Simulated revolving-credit utilization indicator | Included |
| payment_ratio | decimal | Actual/scheduled payment proxy, capped at 1.25 | Included |
| missed_payments_3m | integer | Missed-payment indicators in trailing three observations | Included |
| bureau_score | integer | Simulated external credit score, 300–850 | Included |
| dti_pct | decimal | Simulated debt-service-to-income percentage | Included |
| income_drop_flag | binary | Generated recent income shock indicator | Included |
| hardship_flag | binary | Generated hardship-support signal | Included |
| default_next_3m | binary | Simulated forward 90+ DPD/default-like event within three months | **Target only** |

The target is a conditional simulation used to demonstrate a forward-looking analytical workflow.
It is not derived from actual later records and must not be interpreted as a real default.

## model_scores

Grain: one row per loan and snapshot month.

| Field | Type | Definition |
| --- | --- | --- |
| loan_id | text | Synthetic account key |
| snapshot_month | date | Scored observation month |
| predicted_probability | decimal | Logistic model output between zero and one |
| risk_tier | text | Relative band from train-period score percentiles |
| data_split | text | Train, embargo, or test |
| model_version | text | Scoring model identifier |

Risk-tier cutoffs are learned only from training scores: Low below P50, Monitor P50–P80, High
P80–P95, and Critical at or above P95. They are prioritization bands, not regulatory grades.

## Derived views

| View | Purpose |
| --- | --- |
| vw_loan_risk_features | Reusable joined account-month analytical record plus rules-based tier |
| vw_monthly_portfolio_kpis | Monthly active accounts, exposure, arrears, target rate, and score |
| vw_product_risk_summary | Product-by-month exposure and risk view |
| vw_scored_ews_queue | Score-enriched account view with monthly priority rank |

