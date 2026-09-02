# Architecture and lineage

## System context

This case study models a monthly portfolio-monitoring workflow. The synthetic generator stands in
for governed source systems; SQLite stands in for an analytical warehouse; Streamlit and Markdown
reports stand in for business-intelligence and decision-support outputs.

~~~mermaid
flowchart TB
    subgraph Source["Synthetic source zone"]
        G["Seeded generator"]
        C["customers.csv"]
        L["loans.csv"]
        P["monthly_performance.csv"]
        M["manifest.json"]
        G --> C
        G --> L
        G --> P
        G --> M
    end

    subgraph Warehouse["SQLite analytical layer"]
        D1["customers"]
        D2["loans"]
        F["monthly_performance"]
        S["model_scores"]
        V["semantic views"]
        D1 --> D2 --> F
        F --> V
        S --> V
    end

    subgraph Analytics["Analytics and validation"]
        Q["SQL portfolio analysis"]
        E["Feature matrix"]
        T["Train · embargo · holdout"]
        R["Logistic model"]
        A["Metrics and coefficients"]
        E --> T --> R --> A
    end

    subgraph Delivery["Decision support"]
        UI["Streamlit command center"]
        ER["Executive summary"]
        MC["Model card"]
        CH["Static SVG charts"]
    end

    C --> D1
    L --> D2
    P --> F
    M --> Warehouse
    V --> Q
    V --> E
    R --> S
    Q --> UI
    S --> UI
    A --> MC
    Q --> ER
    A --> CH
~~~

## Grain and keys

- **customers:** one row per synthetic customer; primary key customer_id.
- **loans:** one row per synthetic account; primary key loan_id; many-to-one to customer.
- **monthly_performance:** one row per loan and snapshot month; composite primary key.
- **model_scores:** one score per loan and snapshot month; composite foreign key to performance.

## Pipeline sequence

1. The seed fixes all pseudorandom draws.
2. The generator writes complete CSV files and a provenance manifest.
3. ETL creates a temporary SQLite database, enforces checks and foreign keys, loads data, builds
   views, runs foreign-key validation, commits, and atomically replaces the prior database.
4. Modeling reads only the semantic feature view, applies a temporal split, fits on training data,
   evaluates on holdout data, and writes scores back to SQLite.
5. Reporting reads the database plus model artifacts to create charts and Markdown outputs.
6. Streamlit queries the same persisted semantic layer used by the reports.

## Controls demonstrated

| Layer | Control |
| --- | --- |
| Source | Seed and generation manifest; explicit public-safe provenance |
| Contract | Required CSV headers; numeric ranges; minimum months and accounts |
| Warehouse | Primary and foreign keys; check constraints; indexed query columns |
| ETL | Transaction, rollback, foreign-key check, atomic replacement |
| Modeling | Target excluded from features; train-only scaling and thresholds; temporal embargo |
| Delivery | Synthetic-data labels; intended-use boundary; model and report versioning |
| CI | Determinism, integrity, split, artifact, and end-to-end smoke tests |

## Production migration

For an actual bank, replace CSV simulation with approved source contracts and orchestration;
replace SQLite with a governed warehouse; add reconciliation to finance/risk control totals;
implement outcome maturity; register datasets and models; add access controls, encryption,
monitoring, approval gates, audit evidence, and incident/change processes.

