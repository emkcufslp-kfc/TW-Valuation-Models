from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tw_valuation_models.config import WorkspacePaths
from tw_valuation_models.shared_data import normalize_shared_data, validate_shared_data


class SharedDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        data_root = root / "data"
        (data_root / "fundamentals").mkdir(parents=True)
        (data_root / "raw").mkdir(parents=True)
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        self.paths = WorkspacePaths(workspace_root=self.workspace, shared_data_root=data_root)

        self._write_csv(
            data_root / "fundamentals" / "company_info.csv",
            ["stock_id", "name", "industry", "listing_date", "market"],
            [["2330", "台積電", "半導體", "1994-09-05", "TWSE"]],
        )
        self._write_csv(
            data_root / "fundamentals" / "valuation.csv",
            ["stock_id", "pe_ratio", "pb_ratio", "dividend_yield"],
            [["2330", "18.1", "5.5", "1.2"]],
        )
        self._write_csv(
            data_root / "fundamentals" / "yfinance_fundamentals.csv",
            [
                "stock_id",
                "market_cap",
                "roe",
                "eps",
                "revenue",
                "net_income",
                "total_equity",
                "operating_cf",
                "free_cf",
            ],
            [["2330", "100", "0.2", "10", "1000", "500", "200", "300", "250"]],
        )
        self._write_csv(
            data_root / "raw" / "2330.csv",
            ["Date", "Open", "High", "Low", "Close", "Volume"],
            [["2026-05-13", "950", "960", "945", "955", "1000"]],
        )
        self._write_csv(
            data_root / "raw" / "TAIEX.csv",
            ["Date", "Open", "High", "Low", "Close", "Volume"],
            [["2026-05-13", "21000", "21100", "20900", "21050", "999999"]],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_normalize_and_validate(self) -> None:
        summary = normalize_shared_data(self.paths)
        self.assertEqual(len(summary["tables"]), 5)

        universe_path = self.paths.normalized_root / "universe_snapshot.csv"
        self.assertTrue(universe_path.exists())

        with universe_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["ticker"], "2330")

        validation = validate_shared_data(self.paths)
        self.assertEqual(len(validation["checks"]), 5)
        validation_path = self.paths.validation_root / "validation_summary.json"
        saved = json.loads(validation_path.read_text(encoding="utf-8"))
        self.assertIn("checks", saved)

    def _write_csv(self, path: Path, headers: list[str], rows: list[list[str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
