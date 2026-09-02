PYTHON ?= python3
LOANS ?= 2500
MONTHS ?= 21
SEED ?= 42

.PHONY: help setup generate db model pipeline dashboard test clean

help:
	@echo "Retail Credit Risk Early-Warning Analytics"
	@echo "  make setup      Create .venv and install dependencies"
	@echo "  make pipeline   Generate data, build SQLite, train model, create reports"
	@echo "  make dashboard  Launch the Streamlit dashboard"
	@echo "  make test       Run the standard-library test suite"
	@echo "  make clean      Remove reproducible generated outputs"

setup:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r requirements.txt

generate:
	$(PYTHON) scripts/generate_data.py --loans $(LOANS) --months $(MONTHS) --seed $(SEED)

db:
	$(PYTHON) scripts/build_database.py

model:
	$(PYTHON) scripts/run_analysis.py

pipeline:
	$(PYTHON) scripts/run_pipeline.py --loans $(LOANS) --months $(MONTHS) --seed $(SEED)

dashboard:
	$(PYTHON) -m streamlit run app/streamlit_app.py

test:
	$(PYTHON) -m unittest discover -s tests -v

clean:
	$(PYTHON) scripts/clean_generated.py

