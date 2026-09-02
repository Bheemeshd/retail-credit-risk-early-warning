import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from credit_risk.data_generator import generate_portfolio
from credit_risk.etl import build_database


class EtlTests(unittest.TestCase):
    def test_database_loads_expected_grain_and_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            raw = root / "raw"
            database = root / "credit_risk.db"
            generate_portfolio(raw, n_loans=80, n_months=9, seed=9)
            counts = build_database(raw, database, REPO_ROOT / "sql")

            self.assertEqual(counts["loans"], 80)
            self.assertEqual(counts["monthly_performance"], 720)
            with sqlite3.connect(database) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 66)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM loans").fetchone()[0], 80)
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM monthly_performance").fetchone()[0], 720
                )
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                month_count = connection.execute(
                    "SELECT COUNT(*) FROM vw_monthly_portfolio_kpis"
                ).fetchone()[0]
                self.assertEqual(month_count, 9)
                duplicate_grain = connection.execute(
                    """
                    SELECT COUNT(*) - COUNT(DISTINCT loan_id || '|' || snapshot_month)
                    FROM monthly_performance
                    """
                ).fetchone()[0]
                self.assertEqual(duplicate_grain, 0)


if __name__ == "__main__":
    unittest.main()

