import json
import sqlite3
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from credit_risk.data_generator import generate_portfolio
from credit_risk.etl import build_database
from credit_risk.modeling import FEATURE_NAMES, train_and_score
from credit_risk.reporting import generate_reports


class ModelingTests(unittest.TestCase):
    def test_temporal_model_outputs_scores_metrics_and_valid_charts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            raw = root / "data" / "raw"
            database = root / "data" / "processed" / "credit_risk.db"
            artifacts = root / "artifacts"
            reports = root / "reports"
            generate_portfolio(raw, n_loans=250, n_months=12, seed=123)
            build_database(raw, database, REPO_ROOT / "sql")
            metrics = train_and_score(database, artifacts)
            report = generate_reports(database, artifacts, reports)

            holdout = metrics["holdout"]
            self.assertGreaterEqual(holdout["roc_auc"], 0)
            self.assertLessEqual(holdout["roc_auc"], 1)
            self.assertGreaterEqual(holdout["brier_score"], 0)
            self.assertEqual(metrics["row_counts"], {"train": 1500, "embargo": 750, "test": 750})
            self.assertLess(metrics["split"]["train_end"], metrics["split"]["test_start"])
            self.assertNotIn("birth_year", FEATURE_NAMES)
            self.assertNotIn("region", FEATURE_NAMES)
            self.assertNotIn("default_next_3m", FEATURE_NAMES)

            with sqlite3.connect(database) as connection:
                score_count = connection.execute("SELECT COUNT(*) FROM model_scores").fetchone()[0]
                self.assertEqual(score_count, 3000)
                tier_count = connection.execute(
                    "SELECT COUNT(DISTINCT risk_tier) FROM model_scores"
                ).fetchone()[0]
                self.assertEqual(tier_count, 4)

            model = json.loads((artifacts / "model.json").read_text(encoding="utf-8"))
            self.assertEqual(model["model_version"], "logistic-ews-v1")
            self.assertEqual(len(model["coefficients"]), len(FEATURE_NAMES))
            self.assertEqual(report["charts"], 5)
            for svg in artifacts.rglob("*.svg"):
                ET.parse(svg)
            self.assertTrue((reports / "executive_summary.md").exists())
            self.assertTrue((reports / "model_card.md").exists())


if __name__ == "__main__":
    unittest.main()

