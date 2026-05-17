from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = WORKSPACE_ROOT / ".deps"
if str(DEPS_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPS_ROOT))

import app


class ArtifactConsistencyTests(unittest.TestCase):
    def test_buffett3_results_match_saved_payloads(self) -> None:
        results_path = WORKSPACE_ROOT / "artifacts" / "results" / "top100_model_results.csv"
        payload_dir = WORKSPACE_ROOT / "artifacts" / "results" / "buffett3_payloads"
        checked = 0

        with results_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                ticker = str(row["ticker"])
                payload_path = payload_dir / f"{ticker}.json"
                self.assertTrue(payload_path.exists(), f"Missing Buffett 3.0 payload for ticker {ticker}")

                payload = json.loads(payload_path.read_text(encoding="utf-8"))
                row_fair = float(row["buffett3_intrinsic"])
                payload_fair = float(payload["final_fair_value_per_share"])
                self.assertAlmostEqual(
                    row_fair,
                    payload_fair,
                    places=6,
                    msg=f"Buffett 3.0 fair value drift for ticker {ticker}",
                )
                self.assertEqual(
                    row["buffett3_type"],
                    str(payload["classification"]),
                    f"Buffett 3.0 classification drift for ticker {ticker}",
                )
                checked += 1

        self.assertEqual(checked, 100)

    def test_buffett3_loader_exposes_compatibility_fields_for_all_saved_payloads(self) -> None:
        payload_dir = WORKSPACE_ROOT / "artifacts" / "results" / "buffett3_payloads"
        payload_files = sorted(payload_dir.glob("*.json"))
        self.assertEqual(len(payload_files), 100)

        for payload_path in payload_files:
            ticker = payload_path.stem
            payload = app.load_buffett3_payload(ticker)
            self.assertEqual(
                payload.get("company_type"),
                payload.get("classification"),
                f"Loader did not backfill company_type for ticker {ticker}",
            )
            self.assertIsNotNone(
                payload.get("blended_fair_value"),
                f"Loader did not backfill blended_fair_value for ticker {ticker}",
            )
            self.assertIsNotNone(
                payload.get("final_fair_value"),
                f"Loader did not backfill final_fair_value for ticker {ticker}",
            )
            self.assertIsNotNone(
                payload.get("rating"),
                f"Loader did not derive a Buffett 3.0 rating for ticker {ticker}",
            )

    def test_cyclical_payloads_publish_ev_ebitda_blockers_from_real_source_coverage(self) -> None:
        results_path = WORKSPACE_ROOT / "artifacts" / "results" / "top100_model_results.csv"
        payload_dir = WORKSPACE_ROOT / "artifacts" / "results" / "buffett3_payloads"
        cyclical_tickers: list[str] = []

        with results_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["buffett3_type"] == "cyclical":
                    cyclical_tickers.append(str(row["ticker"]))

        self.assertGreater(len(cyclical_tickers), 0)

        for ticker in cyclical_tickers:
            payload = json.loads((payload_dir / f"{ticker}.json").read_text(encoding="utf-8"))
            normalized_inputs = payload.get("normalized_inputs", {})
            blockers = normalized_inputs.get("cyclical_ev_ebitda_blockers", [])
            coverage = normalized_inputs.get("source_field_coverage", {})
            ev_leg = next(
                leg for leg in payload.get("valuation_legs", []) if leg.get("name") == "normalized_ev_ebitda"
            )

            self.assertIn("total_debt_missing_in_source_tables", blockers)
            self.assertIn("cash_and_equivalents_missing_in_source_tables", blockers)
            self.assertIn("clean_ebitda_series_not_available_in_current_dataset", blockers)
            self.assertEqual(coverage.get("annual_total_debt_non_null_rows"), 0)
            self.assertEqual(coverage.get("annual_cash_and_equivalents_non_null_rows"), 0)
            self.assertEqual(coverage.get("quarterly_total_debt_non_null_rows"), 0)
            self.assertEqual(coverage.get("quarterly_cash_and_equivalents_non_null_rows"), 0)
            self.assertIn("cyclical_model_uses_partial_leg_set", payload.get("manual_review_flags", []))
            self.assertNotIn("some_valuation_legs_not_ready", payload.get("manual_review_flags", []))
            self.assertIn("total_debt_missing_in_source_tables", ev_leg.get("notes", []))
            self.assertIn("cash_and_equivalents_missing_in_source_tables", ev_leg.get("notes", []))

    def test_compounder_payload_2330_keeps_dividend_leg_ready_when_dividend_history_exists(self) -> None:
        payload_path = WORKSPACE_ROOT / "artifacts" / "results" / "buffett3_payloads" / "2330.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        dividend_leg = next(
            leg for leg in payload.get("valuation_legs", []) if leg.get("name") == "dividend_yield_or_ddm"
        )

        self.assertEqual(payload.get("classification"), "high_quality_compounder")
        self.assertGreater(payload.get("input_snapshot", {}).get("dividend_row_count", 0), 0)
        self.assertEqual(dividend_leg.get("status"), "ready")
        self.assertIsNotNone(dividend_leg.get("blended_value"))
        self.assertNotIn("leg_has_missing_required_inputs", dividend_leg.get("notes", []))
        self.assertNotIn("dividend_history_missing_or_proxy_used", payload.get("data_quality_flags", []))

    def test_buffett_three_payloads_do_not_publish_negative_ready_equity_values(self) -> None:
        payload_dir = WORKSPACE_ROOT / "artifacts" / "results" / "buffett3_payloads"

        for payload_path in payload_dir.glob("*.json"):
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            fair_value = payload.get("final_fair_value")
            if fair_value is not None:
                self.assertGreaterEqual(float(fair_value), 0.0, payload_path.name)
            for leg in payload.get("valuation_legs", []):
                if leg.get("status") == "ready" and leg.get("blended_value") is not None:
                    self.assertGreaterEqual(float(leg["blended_value"]), 0.0, f"{payload_path.name}:{leg.get('name')}")


if __name__ == "__main__":
    unittest.main()
