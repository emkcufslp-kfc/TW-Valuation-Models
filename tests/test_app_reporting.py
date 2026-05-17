from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = WORKSPACE_ROOT / ".deps"
if str(DEPS_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPS_ROOT))

import pandas as pd

import app
from tw_valuation_models.config import WorkspacePaths


class AppReportingTests(unittest.TestCase):
    def test_load_results_falls_back_to_on_demand_demo_without_normalized_shared_data(self) -> None:
        original_paths = app.PATHS
        original_results_path = app.RESULTS_PATH
        original_summary_path = app.SUMMARY_PATH
        original_ensure_outputs = app.ensure_outputs
        app.load_results.clear()
        try:
            with TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                on_demand_root = root / "artifacts" / "runtime" / "on_demand" / "model_results"
                on_demand_root.mkdir(parents=True, exist_ok=True)
                dataset_root = root / "artifacts" / "runtime" / "on_demand" / "datasets" / "2330"
                payload = {
                    "generated_at": "2026-05-18T00:00:00+08:00",
                    "ticker": "2330",
                    "dataset_root": str(dataset_root),
                    "row": {
                        "ticker": "2330",
                        "name": "TSMC",
                        "industry": "Semiconductor",
                        "market_cap": 1,
                        "price": 1000.0,
                        "dataset_root": str(dataset_root),
                    },
                }
                (on_demand_root / "2330.json").write_text(
                    json.dumps(payload, ensure_ascii=False),
                    encoding="utf-8",
                )
                app.PATHS = WorkspacePaths(workspace_root=root)
                app.RESULTS_PATH = root / "artifacts" / "results" / "top100_model_results.csv"
                app.SUMMARY_PATH = root / "artifacts" / "results" / "top100_model_results_summary.json"
                app.ensure_outputs = lambda: None

                results_df, dataset, result_summary = app.load_results()

                self.assertEqual(results_df.iloc[0]["ticker"], "2330")
                self.assertTrue(result_summary["demo_mode"])
                self.assertEqual(dataset["top100_universe"].iloc[0]["ticker"], "2330")
        finally:
            app.PATHS = original_paths
            app.RESULTS_PATH = original_results_path
            app.SUMMARY_PATH = original_summary_path
            app.ensure_outputs = original_ensure_outputs
            app.load_results.clear()
    def test_should_refresh_final_ai_only_on_transition_into_final_ai_page(self) -> None:
        self.assertTrue(app.should_refresh_final_ai("Final AI 專區", "主頁總覽"))
        self.assertFalse(app.should_refresh_final_ai("Final AI 專區", "Final AI 專區"))
        self.assertFalse(app.should_refresh_final_ai("主頁總覽", "Final AI 專區"))

    def test_choose_focus_model_prefers_buffett3_but_preserves_explicit_choice(self) -> None:
        self.assertEqual(
            app.choose_focus_model(["buffett_v1", "buffett3", "imfs"]),
            "buffett3",
        )
        self.assertEqual(
            app.choose_focus_model(["buffett_v1", "buffett3", "imfs"], "imfs"),
            "imfs",
        )
        self.assertEqual(
            app.choose_focus_model(["buffett_v1", "imfs"]),
            "buffett_v1",
        )

    def test_buffett3_label_helpers_render_strings_and_new_flags(self) -> None:
        self.assertEqual(app.format_buffett3_type("defensive_dividend"), "防禦收益股")
        self.assertEqual(
            app.format_buffett3_label("negative_equity_leg_value_floored_to_zero"),
            "負值股權支線已保守下限為 0",
        )
        self.assertEqual(
            app.join_buffett3_labels("latest_quarter_eps_positive,monthly_revenue_yoy_supportive"),
            "最新季 EPS 為正、月營收年增支持",
        )
        self.assertEqual(
            app.join_buffett3_labels("industry_or_ticker_matches_financial_rules"),
            "產業或代號符合金融股規則",
        )

    def test_build_data_diagnostic_snapshot_uses_manifest_truth(self) -> None:
        dataset = {
            "monthly_revenue": pd.DataFrame(
                [
                    {"stock_id": "2330", "period": "2026-04-01"},
                    {"stock_id": "2330", "period": "2026-03-01"},
                ]
            )
        }
        diagnostics = {
            "dataset_summary": {
                "summary": {"top100_count": 100},
                "buffett3_official": {"official_statement_tickers": ["2330", "2881"]},
            },
            "buffett3_manifest": {
                "financial_tickers": ["2881"],
                "entries": [
                    {
                        "domain": "monthly_revenue_history",
                        "covered_tickers": ["2330"],
                        "missing_tickers": ["2881"],
                    },
                    {
                        "domain": "annual_fundamentals_official",
                        "covered_tickers": ["2330", "2881"],
                    },
                    {
                        "domain": "quarterly_fundamentals_official",
                        "covered_tickers": ["2330", "2881"],
                    },
                    {
                        "domain": "valuation_snapshot_current",
                        "covered_tickers": ["2330", "2881"],
                    },
                    {
                        "domain": "dividend_history",
                        "covered_tickers": ["2330", "2881"],
                    },
                ],
            },
            "validation_summary": {
                "checks": [
                    {"table": "valuation_snapshot", "status": "warning"},
                    {"table": "price_daily", "status": "ok"},
                ]
            },
            "normalization_summary": {
                "tables": [
                    {"name": "fundamentals_snapshot", "status": "warning"},
                    {"name": "benchmark_daily", "status": "ok"},
                ]
            },
        }

        compounder_snapshot = app.build_data_diagnostic_snapshot(dataset, diagnostics, "2330")
        financial_snapshot = app.build_data_diagnostic_snapshot(dataset, diagnostics, "2881")

        self.assertEqual(compounder_snapshot["monthly_revenue_covered_count"], 1)
        self.assertEqual(compounder_snapshot["ticker_monthly_revenue_rows"], 2)
        self.assertTrue(compounder_snapshot["ticker_has_monthly_revenue"])
        self.assertEqual(compounder_snapshot["ticker_statement_route"], "general")
        self.assertEqual(compounder_snapshot["validation_warning_tables"], ["valuation_snapshot"])
        self.assertEqual(compounder_snapshot["normalization_warning_tables"], ["fundamentals_snapshot"])

        self.assertFalse(financial_snapshot["ticker_has_monthly_revenue"])
        self.assertEqual(financial_snapshot["monthly_revenue_missing_financials"], ["2881"])
        self.assertEqual(financial_snapshot["ticker_statement_route"], "financial")
        self.assertTrue(financial_snapshot["ticker_has_annual_statement"])
        self.assertTrue(financial_snapshot["ticker_has_quarterly_statement"])

    def test_build_data_diagnostic_snapshot_prefers_manifest_for_ticker_monthly_coverage(self) -> None:
        dataset = {
            "monthly_revenue": pd.DataFrame(
                [
                    {"stock_id": "9999", "period": "2026-04-01"},
                ]
            )
        }
        diagnostics = {
            "dataset_summary": {
                "summary": {"top100_count": 100},
                "buffett3_official": {"official_statement_tickers": ["2330"]},
            },
            "buffett3_manifest": {
                "financial_tickers": [],
                "entries": [
                    {
                        "domain": "monthly_revenue_history",
                        "covered_tickers": ["2330"],
                        "missing_tickers": [],
                    },
                    {"domain": "annual_fundamentals_official", "covered_tickers": ["2330"]},
                    {"domain": "quarterly_fundamentals_official", "covered_tickers": ["2330"]},
                    {"domain": "valuation_snapshot_current", "covered_tickers": ["2330"]},
                    {"domain": "dividend_history", "covered_tickers": ["2330"]},
                ],
            },
            "validation_summary": {"checks": []},
            "normalization_summary": {"tables": []},
        }

        snapshot = app.build_data_diagnostic_snapshot(dataset, diagnostics, "2330")

        self.assertEqual(snapshot["ticker_monthly_revenue_rows"], 0)
        self.assertTrue(snapshot["ticker_has_monthly_revenue"])

    def test_get_model_payload_buffett3_falls_back_to_payload_snapshot(self) -> None:
        row = pd.Series(
            {
                "ticker": "2330",
                "name": "台積電",
                "price": 2270.0,
                "buffett3_intrinsic": None,
                "buffett3_mos": None,
                "buffett3_signal": "",
                "buffett3_type": None,
                "data_warnings": "{}",
            }
        )
        original_loader = app.load_buffett3_payload
        app.load_buffett3_payload = lambda ticker: {
            "classification": "high_quality_compounder",
            "company_type": "high_quality_compounder",
            "final_fair_value": 799.566,
            "rating": "昂貴",
        }
        try:
            payload = app.get_model_payload(row, "buffett3")
        finally:
            app.load_buffett3_payload = original_loader

        self.assertEqual(payload["rating"], "非常昂貴")
        self.assertEqual(payload["fair_value_text"], "799.57")
        self.assertIn("高品質複利股", payload["summary"])

    def test_build_model_ranking_comparison_reports_pairwise_overlap(self) -> None:
        results_df = pd.DataFrame(
            [
                {"ticker": "A", "name": "Alpha", "buffett3_mos": 20.0, "quant_score": 50.0, "hybrid_return_pct": 8.0},
                {"ticker": "B", "name": "Beta", "buffett3_mos": 15.0, "quant_score": 80.0, "hybrid_return_pct": 3.0},
                {"ticker": "C", "name": "Gamma", "buffett3_mos": 10.0, "quant_score": 70.0, "hybrid_return_pct": 9.0},
            ]
        )

        comparison = app.build_model_ranking_comparison(results_df, top_n=2)

        self.assertEqual(comparison["top_n"], 2)
        self.assertEqual(comparison["models"]["buffett3"]["rankings"][0]["ticker"], "A")
        self.assertEqual(comparison["models"]["quant"]["rankings"][0]["ticker"], "B")
        self.assertEqual(comparison["models"]["hybrid"]["rankings"][0]["ticker"], "C")
        self.assertTrue(any(item["overlap_count"] >= 1 for item in comparison["pairwise_overlap"]))

    def test_build_report_includes_provenance_and_buffett3_detail(self) -> None:
        row = pd.Series(
            {
                "ticker": "2881",
                "name": "富邦金",
                "industry": "金融保險",
                "buffett3_intrinsic": 71.153,
                "buffett3_mos": -24.7854,
                "buffett3_signal": "避開",
                "buffett3_type": "financial",
                "imfs_intrinsic": None,
                "imfs_gap_pct": None,
                "imfs_model": "RULE_OF_40",
                "imfs_route": "B",
                "imfs_quality_score": 42.0,
                "imfs_premium_eligible": False,
                "imfs_est_revenue_growth_pct": 12.0,
                "imfs_est_profit_margin_pct": 18.0,
                "imfs_justified_pe": 18.0,
                "imfs_signal": "觀察",
                "quant_score": 48.0,
                "quant_action": "觀察",
                "quant_signal": "觀察",
                "hybrid_target": 80.0,
                "hybrid_return_pct": 5.0,
                "hybrid_signal": "觀察",
                "buffett_v1_intrinsic": 65.0,
                "buffett_v1_mos": -10.0,
                "buffett_v1_signal": "觀察",
                "buffett_v2_intrinsic": 68.0,
                "buffett_v2_mos": -6.0,
                "buffett_v2_signal": "觀察",
                "data_warnings": json.dumps(
                    {
                        "buffett3": ["current_ratio_missing"],
                        "imfs": [],
                    },
                    ensure_ascii=False,
                ),
            }
        )
        diagnostics = {
            "buffett3_manifest": {
                "generated_at": "2026-05-15T15:44:27+00:00",
                "financial_tickers": ["2881"],
                "entries": [
                    {
                        "domain": "monthly_revenue_history",
                        "source_name": "monthly.csv",
                        "target_path": "artifacts/datasets/top100/buffett3_monthly_revenue_history.csv",
                        "row_count": 95,
                        "requested_tickers": ["2881"],
                        "covered_tickers": [],
                        "missing_tickers": ["2881"],
                    },
                    {
                        "domain": "annual_fundamentals_official",
                        "source_name": "annual.csv",
                        "target_path": "artifacts/datasets/top100/buffett3_annual_fundamentals.csv",
                        "row_count": 83,
                        "requested_tickers": ["2881"],
                        "covered_tickers": ["2881"],
                        "missing_tickers": [],
                    },
                ],
            },
        }
        data_snapshot = {
            "top100_count": 100,
            "monthly_revenue_covered_count": 95,
            "monthly_revenue_missing_count": 5,
            "monthly_revenue_missing_tickers": ["2881", "2882", "2885", "2887", "2891"],
            "monthly_revenue_missing_financials": ["2881", "2882", "2885", "2887", "2891"],
            "ticker_monthly_revenue_rows": 0,
            "ticker_has_monthly_revenue": False,
            "ticker_statement_route": "financial",
            "ticker_has_annual_statement": True,
            "ticker_has_quarterly_statement": True,
            "official_statement_ticker_count": 83,
            "valuation_covered_count": 100,
            "dividend_covered_count": 100,
            "validation_warning_tables": ["universe_snapshot", "valuation_snapshot", "fundamentals_snapshot"],
            "normalization_warning_tables": ["valuation_snapshot", "fundamentals_snapshot"],
        }

        original_loader = app.load_buffett3_payload
        app.load_buffett3_payload = lambda ticker: {
            "classification": "financial",
            "classification_reason": "industry_or_ticker_matches_financial_rules",
            "company_type": "financial",
            "blended_fair_value": 73.49,
            "final_fair_value": 71.153,
            "rating": "昂貴",
            "normalized_inputs": {
                "cyclical_ev_ebitda_blockers": [],
                "source_field_coverage": {
                    "annual_total_debt_non_null_rows": 0,
                    "annual_cash_and_equivalents_non_null_rows": 0,
                },
            },
            "data_quality_flags": ["current_ratio_missing"],
            "manual_review_flags": [],
        }
        try:
            report = json.loads(
                app.build_report(
                    row,
                    ["buffett3", "imfs"],
                    {"summary": {"top100_count": 100}},
                    "2026/05/16 07:52",
                    diagnostics,
                    data_snapshot,
                )
            )
        finally:
            app.load_buffett3_payload = original_loader

        self.assertEqual(report["ticker"], "2881")
        self.assertEqual(report["data_provenance"]["ticker_snapshot"]["ticker_statement_route"], "financial")
        self.assertEqual(
            report["data_provenance"]["buffett3_manifest_generated_at"],
            "2026-05-15T15:44:27+00:00",
        )
        self.assertEqual(
            report["data_provenance"]["manifest_ticker_coverage"]["statement_route"],
            "financial",
        )
        self.assertEqual(
            report["data_provenance"]["manifest_ticker_coverage"]["missing_domains"],
            ["monthly_revenue_history"],
        )
        self.assertEqual(report["buffett3_detail"]["classification"], "financial")
        self.assertAlmostEqual(float(report["buffett3_detail"]["blended_fair_value"]), 73.49)
        self.assertAlmostEqual(float(report["buffett3_detail"]["final_fair_value"]), 71.153)
        self.assertEqual(report["buffett3_detail"]["rating"], "昂貴")
        self.assertEqual(report["buffett3_detail"]["cyclical_ev_ebitda_blockers"], [])
        self.assertEqual(
            report["buffett3_detail"]["source_field_coverage"]["annual_total_debt_non_null_rows"],
            0,
        )
        self.assertEqual(
            report["buffett3_detail"]["reporting_notes"]["takeaways"][0]["topic"],
            "classification",
        )
        self.assertEqual(
            report["buffett3_detail"]["reporting_notes"]["takeaways"][2]["data_quality_flags"],
            ["current_ratio_missing"],
        )
        self.assertIn("buffett3", report["model_payloads"])
        self.assertEqual(report["model_payloads"]["buffett3"]["rating"], "昂貴")


    def test_load_final_module_payload_reads_generated_2330_commentary(self) -> None:
        payload = app.load_final_module_payload("2330", "final_commentary")

        self.assertEqual(payload.get("ticker"), "2330")
        self.assertEqual(payload.get("final_conclusion", {}).get("action_label"), "持有")
        self.assertTrue(payload.get("news_snapshot"))


if __name__ == "__main__":
    unittest.main()
