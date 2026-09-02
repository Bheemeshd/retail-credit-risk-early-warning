import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from credit_risk.data_generator import generate_portfolio


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GeneratorTests(unittest.TestCase):
    def test_seed_is_reproducible_and_contract_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            first = Path(temp_directory) / "first"
            second = Path(temp_directory) / "second"
            manifest = generate_portfolio(first, n_loans=40, n_months=9, seed=77)
            generate_portfolio(second, n_loans=40, n_months=9, seed=77)

            for file_name in ("customers.csv", "loans.csv", "monthly_performance.csv", "manifest.json"):
                self.assertEqual(file_hash(first / file_name), file_hash(second / file_name))

            self.assertEqual(manifest["loans"], 40)
            self.assertEqual(manifest["monthly_snapshots"], 360)
            self.assertIn("contains no real people", manifest["provenance"])

            with (first / "monthly_performance.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 360)
            self.assertTrue(all(0 <= float(row["utilization_pct"]) <= 100 for row in rows))
            self.assertTrue(all(300 <= int(row["bureau_score"]) <= 850 for row in rows))
            self.assertEqual({row["default_next_3m"] for row in rows} - {"0", "1"}, set())

            parsed_manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed_manifest["seed"], 77)

    def test_invalid_small_configuration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            with self.assertRaises(ValueError):
                generate_portfolio(Path(temp_directory), n_loans=19, n_months=9)
            with self.assertRaises(ValueError):
                generate_portfolio(Path(temp_directory), n_loans=20, n_months=8)


if __name__ == "__main__":
    unittest.main()

