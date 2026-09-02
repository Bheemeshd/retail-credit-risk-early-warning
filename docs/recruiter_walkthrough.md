# Three-minute recruiter walkthrough

## 0:00–0:30 — Frame the business problem

“This project supports a retail-bank credit-risk team that needs to spot emerging stress in its
existing loan book and allocate a limited manual-review capacity. I use synthetic data so the work
is safe to publish, and I label every performance figure accordingly.”

## 0:30–1:10 — Show the data and SQL layer

Open **docs/architecture.md**, **sql/schema.sql**, and **sql/portfolio_analysis.sql**.

“The grain is one account per month. I created customer, loan, performance, and score tables with
keys and checks; reusable views define portfolio KPIs, product risk, and the review queue. The SQL
also calculates delinquency roll rates with window functions.”

## 1:10–1:55 — Explain analytical validity

Open **docs/methodology.md**, **reports/model_card.md**, and
**artifacts/charts/holdout_calibration.svg**.

“The baseline is interpretable logistic regression. I avoid a random split: training is followed by
a three-month embargo and then a future holdout, matching the forward-label horizon. Preprocessing
and thresholds use training data only. I report discrimination, precision-recall, calibration, and
a capacity-based queue metric.”

## 1:55–2:35 — Demonstrate the product

Run **make dashboard** and open the portfolio and action-queue tabs.

“Managers can see exposure and arrears movement; analysts can filter and download a ranked queue
with behavioral reason indicators; reviewers can inspect holdout metrics and governance limits.”

## 2:35–3:00 — Close on engineering and judgment

Open **tests/** and **.github/workflows/ci.yml**.

“The same seed reproduces the source, ETL replaces the database atomically, tests check data grain,
foreign keys, leakage exclusions, split boundaries, scores, and artifact validity, and CI executes
the pipeline. I explicitly distinguish a strong portfolio demonstration from a production-ready
bank model.”

