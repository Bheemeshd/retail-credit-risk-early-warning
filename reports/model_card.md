# Model card — logistic-ews-v1

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

- Training: 2024-01-01 through 2025-03-01
- Embargo: 2025-04-01 through 2025-06-01
- Holdout: 2025-07-01 through 2025-09-01
- Forward target horizon: 3 months
- Holdout rows / positives: 7,500 / 431

## Holdout metrics (synthetic)

| Metric | Value |
| --- | --- |
| ROC-AUC | 0.6953 |
| Average precision | 0.2527 |
| Brier score | 0.0485 |
| Log loss | 0.1951 |
| Top-decile recall | 37.59% |
| Top-decile lift | 3.08x |

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
