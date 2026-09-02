# Retail Credit Risk Early-Warning Analytics

> **Portfolio disclosure:** This case study uses deterministic synthetic data only. All customers,
> loans, behaviors, balances, outcomes, and reported metrics are simulated. It demonstrates my
> analytical workflow and does not claim results from a real financial institution.

## At a glance

| Dimension | Detail |
| --- | --- |
| Domain | Retail banking · credit-risk portfolio monitoring |
| Problem | Prioritize existing accounts for early, human-reviewed supportive outreach |
| Data | Synthetic customer, loan, and monthly performance records |
| Stack | Python, NumPy, SQL, SQLite, pandas, Streamlit, GitHub Actions |
| Core methods | KPI design, delinquency roll rates, logistic regression, temporal validation, calibration |
| Deliverables | Reproducible pipeline, database, SQL layer, dashboard, model card, executive summary, tests |

## The business context

Credit-risk teams need to detect deterioration before accounts reach severe delinquency. A flat
arrears list is reactive and can overwhelm review capacity. I designed a monthly early-warning
product that separates two questions:

1. **Portfolio monitoring:** where are exposure, arrears, and risk moving?
2. **Operational prioritization:** which existing accounts should an analyst review first?

The product is deliberately bounded: it supports review and supportive outreach. It does not make
underwriting, pricing, limit, collections-treatment, or adverse-action decisions.

## My approach

### 1. Build a safe analytical source

I created a seed-controlled generator for customers, four loan products, and monthly account
behavior. The data includes balances, delinquency, utilization, payment behavior, bureau score,
affordability, and hardship indicators. A manifest records provenance, seed, scope, period, and
simulated event rate.

### 2. Create a trustworthy SQL layer

I loaded the source into SQLite using an atomic transaction. Primary keys, foreign keys, ranges,
and categorical checks enforce the data contract. Reusable views expose account-month features,
monthly KPIs, product risk, and the scored early-warning queue.

### 3. Define decision-relevant measures

- outstanding exposure;
- DPD 30+ and DPD 90+ incidence;
- delinquency-state roll rates;
- simulated forward target rate;
- score discrimination and calibration;
- top-decile precision, recall, and lift; and
- exposure captured by relative risk tier.

### 4. Validate an interpretable model in time

I fitted an L2-regularized logistic regression using only transparent behavioral and account
features. I excluded identifiers, geography, birth year, employment, home ownership, and the
target. Preprocessing and operating thresholds are learned only from training data.

Instead of a random row split, I used older months for training, a three-month embargo matching the
target horizon, and the final three months as holdout. This reduces future-label overlap and better
represents monthly portfolio scoring.

### 5. Turn analysis into a usable product

The Streamlit command center provides:

- a monthly portfolio pulse;
- exposure and risk trends;
- product and tier breakdowns;
- a filtered, downloadable analyst-review queue;
- holdout discrimination and calibration; and
- visible intended-use, privacy, fairness, and model-risk boundaries.

## Result

The reproducible run creates **52,500 synthetic account-months** and a checked-in SQLite
database. On the purged temporal holdout, the demonstration model reports **ROC-AUC 0.695**,
**average precision 0.253**, **Brier score 0.049**, and **3.08× lift** at the
train-derived top-decile operating point.

These results confirm that the designed synthetic signals, data pipeline, model, and evaluation are
connected. They do **not** estimate production benefit. The honest result of this case study is a
reproducible analytical system and a defensible validation/governance approach.

## Key visual outputs

Add these generated repository assets as image blocks in Notion:

1. **artifacts/dashboard_preview.svg** — end-user product preview
2. **artifacts/charts/portfolio_risk_trend.svg** — arrears and target movement
3. **artifacts/charts/feature_importance.svg** — signed standardized model drivers
4. **artifacts/charts/holdout_calibration.svg** — predicted versus observed synthetic risk
5. **artifacts/charts/latest_risk_tier_exposure.svg** — latest exposure by action tier

## What I would do next in a bank

I would define outcome maturity and exclusions with Credit Risk, reconcile source/KPI controls,
benchmark against current rules, complete independent model validation and fairness/proxy testing,
and launch in shadow mode. The pilot would compare rule-only and model-assisted review under the
same capacity while measuring contact coverage, cure, roll rates, calibration, segment stability,
overrides, complaints, and customer-support outcomes.

## Skills demonstrated

**Business analysis:** problem framing, consumers, KPIs, capacity-aware decision design  
**Data:** synthetic generation, data contracts, dimensional modeling, validation, lineage  
**SQL:** joins, conditional aggregation, CTEs, window functions, ranked queues, reusable views  
**Python:** modular pipeline, feature engineering, interpretable modeling, metrics, static reporting  
**Product:** Streamlit dashboard, downloadable queue, executive memo, model card  
**Engineering:** deterministic builds, automated tests, CI, atomic ETL, versioned artifacts  
**Risk judgment:** leakage controls, temporal validation, limitations, privacy/fairness boundary

## Repository

Replace this line after publishing: **GitHub repository → [add public repository URL]**

## CV bullet

Built an end-to-end synthetic retail-credit early-warning analytics product using Python, SQL,
SQLite, and Streamlit; designed portfolio/roll-rate KPIs, an interpretable logistic model with a
purged temporal holdout, a ranked analyst queue, automated tests, CI, executive reporting, and
documented model-risk and responsible-use controls.
