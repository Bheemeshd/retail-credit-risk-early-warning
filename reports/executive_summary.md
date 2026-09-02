# Executive summary — Retail Credit Early-Warning Analytics

**Reporting month:** 2025-09  
**Data status:** 100% synthetic and public-safe. No real customers, accounts, or bank results.

## Portfolio pulse

- **2,500 active loan accounts** with **€88.4m** outstanding exposure.
- **DPD 30+ rate:** 3.12% at the latest snapshot.
- **Simulated next-three-month target rate:** 6.04% at the latest snapshot.
- **Average bureau score:** 719.

## Early-warning model

The interpretable logistic model was evaluated on a future three-month holdout after a
three-month embargo. On this synthetic holdout it achieved **ROC-AUC 0.695**,
**average precision 0.253**, and **Brier score
0.049**. At the operating point set from the training-period top
decile, the holdout queue captured **37.6%** of
simulated targets with **3.1x lift** versus the
holdout portfolio average.

These values demonstrate analytical workflow, not live model quality. A real deployment would
require representative bank data, outcome maturation, bias and stability reviews, independent
validation, monitoring, controls, and human decision ownership.

## Recommended operating workflow

1. Refresh monthly snapshots and validate source reconciliation.
2. Rank the contact queue by model score, then review reason indicators and exposure.
3. Route customers to supportive outreach or manual review; do not automate adverse action.
4. Track contact coverage, cures, roll rates, calibration, segment stability, and overrides.

## Product view (2025-09)

| Product | Accounts | Exposure | DPD 30+ % | Synthetic target % |
| --- | --- | --- | --- | --- |
| Mortgage | 346 | €69.9m | 2.31 | 5.78 |
| Personal loan | 897 | €7.6m | 4.01 | 5.24 |
| Auto loan | 521 | €6.5m | 2.50 | 6.72 |
| Credit card | 736 | €4.3m | 2.85 | 6.66 |
