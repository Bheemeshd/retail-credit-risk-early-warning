# Analysis workflow

This repository intentionally uses tested Python modules and SQL files as the canonical analysis
rather than placing business logic in an opaque notebook state.

For an interview walkthrough:

1. run **scripts/run_pipeline.py** to reproduce all inputs and outputs;
2. inspect **sql/portfolio_analysis.sql** for decision-focused SQL;
3. inspect **src/credit_risk/modeling.py** for features, split, fit, and metrics;
4. open the SVGs in **artifacts/charts/** and Markdown in **reports/**; and
5. launch **app/streamlit_app.py** for interactive exploration.

This scripts-first structure makes the same logic available to CI, reporting, and the dashboard
and avoids notebook-only code drift.

