# Analytical methodology

## 1. Objective and unit of analysis

The objective is to prioritize existing retail-credit accounts for human early-warning review.
The prediction unit is a loan at a monthly snapshot; the demonstration target is whether a
synthetic 90+ DPD/default-like event occurs in the following three months.

This is portfolio monitoring, not application underwriting. The appropriate operational question
is “which accounts should an analyst review first under finite capacity?” rather than “which
customers should receive credit?”

## 2. Synthetic design

The generator creates customers, loans, and monthly behavior from a fixed seed. Outcomes are drawn
from a documented nonlinear risk function influenced by behavioral stress signals, including
delinquency, missed payments, payment ratio, utilization, bureau score, DTI, income shock, and
hardship. This produces realistic-looking variation without copying or claiming real bank data.

Designed signal means observed performance is expected. Synthetic results prove that code and
evaluation connect correctly; they do not prove transportability, fairness, causal effect, or
commercial value.

## 3. Data preparation and features

The semantic SQL view joins account-month behavior with account context. The model consumes twelve
transparent features:

- bureau score;
- days past due;
- utilization;
- payment ratio;
- missed payments over three months;
- debt-to-income percentage;
- income-drop and hardship flags;
- account age;
- log outstanding balance;
- APR; and
- credit-card indicator.

Identifiers, month, target, region, birth year, employment status, home ownership, income, purpose,
and original principal are excluded. Scaling statistics are fitted on training rows only.

## 4. Leakage controls

| Risk | Control in this project |
| --- | --- |
| Target accidentally enters features | Fixed feature allowlist and test assertion |
| Scaling uses future data | Means and standard deviations fitted on training rows only |
| Threshold tuned on holdout | Top-decile and tier cutoffs come from training scores only |
| Forward-label windows overlap | Three-month embargo before three-month holdout |
| Identifier memorization | Customer and loan identifiers excluded |
| Random-split optimism | Chronological partition, not random row split |

The same loan can appear in older training snapshots and later holdout snapshots, which matches a
live portfolio-monitoring setting. This introduces within-account correlation; uncertainty and
account-level resampling would need attention in formal validation.

## 5. Model

The baseline is L2-regularized logistic regression fitted with iteratively reweighted least
squares. It outputs a probability-like score and signed coefficients per training-standard-
deviation increase. Logistic regression is used because it is reproducible, compact, inspectable,
and sufficient to demonstrate ranking and calibration without implying that complexity is better.

Coefficient signs are descriptive associations in designed synthetic data, not causal effects.
Correlated features can redistribute coefficients, and a coefficient is not an adverse-action
reason by itself.

## 6. Validation

For the default 21 months:

- months 1–15: training;
- months 16–18: embargo matching the three-month target horizon; and
- months 19–21: temporal holdout.

Reported holdout measures:

| Measure | Interpretation |
| --- | --- |
| ROC-AUC | Pairwise ranking discrimination across all thresholds |
| Average precision | Precision-recall summary, useful for an uncommon event |
| Brier score | Mean squared probability error; lower is better |
| Log loss | Penalizes confident wrong probabilities |
| Top-decile precision | Event rate among accounts selected by a train-derived cutoff |
| Top-decile recall | Share of all holdout events covered by that queue |
| Lift | Queue event rate divided by holdout portfolio event rate |
| Calibration bins | Mean prediction versus observed synthetic target by score group |

No single metric approves a model. Real validation also requires benchmark comparison,
uncertainty, stability, calibration by segment, sensitivity, back-testing, overrides, data-quality
failure tests, fairness/proxy analysis, operational impacts, and independent challenge.

## 7. Queue and KPI logic

The operational cutoff is the 90th percentile of training scores, representing a fixed review
capacity. Relative tiers use training score percentiles. The dashboard also exposes delinquency,
bureau, missed-payment, income-shock, hardship, and balance indicators so reviewers see context.

Portfolio KPIs are calculated independently of model scores. DPD 30+ is an account incidence rate,
not balance-weighted delinquency. Exposure by tier is separately aggregated to show concentration.

## 8. Responsible deployment checklist

Before any real pilot:

1. define target, eligibility, exclusions, cure, and outcome-maturity policy;
2. reconcile sources and KPIs to controlled totals;
3. establish lawful basis, purpose limitation, minimization, retention, access, and audit controls;
4. review protected attributes, proxies, disparate impact, reason quality, and segment calibration;
5. validate independently and approve thresholds, overrides, and human-review procedures;
6. run shadow mode and measure customer, cure, queue, and operational outcomes;
7. monitor data drift, score drift, calibration, ranking, stability, coverage, overrides, and incidents;
8. assign accountable owners, review frequency, breach thresholds, escalation, and retirement rules.

