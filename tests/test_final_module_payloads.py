from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = WORKSPACE_ROOT / ".deps"
if str(DEPS_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPS_ROOT))

from tw_valuation_models.config import DEFAULT_SHARED_DATA_ROOT, WorkspacePaths
from tw_valuation_models.final_module_payloads import build_final_module_payloads


class FinalModulePayloadTests(unittest.TestCase):
    def test_build_final_module_payloads_creates_2330_outputs(self) -> None:
        paths = WorkspacePaths(
            workspace_root=WORKSPACE_ROOT,
            shared_data_root=DEFAULT_SHARED_DATA_ROOT,
        )
        summary = build_final_module_payloads(paths, tickers=["2330"])

        self.assertEqual(summary["payload_count"], 1)
        independent_path = paths.final_module_independent_ai_root / "2330.json"
        commentary_path = paths.final_module_commentary_root / "2330.json"
        self.assertTrue(independent_path.exists())
        self.assertTrue(commentary_path.exists())

        independent_payload = json.loads(independent_path.read_text(encoding="utf-8"))
        commentary_payload = json.loads(commentary_path.read_text(encoding="utf-8"))

        self.assertEqual(independent_payload["ticker"], "2330")
        self.assertEqual(commentary_payload["ticker"], "2330")
        self.assertEqual(independent_payload["valuation_method_primary"], "成長型本益比法")
        self.assertIn("高品質公司", commentary_payload["final_conclusion"]["summary"])
        self.assertIn(
            commentary_payload["final_conclusion"]["valuation_label"],
            {"低估", "合理", "高估"},
        )

    def test_build_final_module_payloads_uses_on_demand_result_for_non_top100_ticker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            paths = WorkspacePaths(
                workspace_root=workspace_root,
                shared_data_root=workspace_root / "shared",
            )

            results_root = paths.artifacts_root / "results"
            results_root.mkdir(parents=True, exist_ok=True)
            (results_root / "top100_model_results.csv").write_text(
                "ticker,name,price,buffett3_intrinsic,imfs_intrinsic,hybrid_target,quant_score,buffett3_type\n",
                encoding="utf-8",
            )
            (results_root / "buffett3_payloads").mkdir(parents=True, exist_ok=True)
            (results_root / "buffett3_payloads" / "9999.json").write_text(
                json.dumps(
                    {
                        "ticker": "9999",
                        "company_name": "Test Co",
                        "classification": "financial",
                        "rating": "合理",
                        "signal": "hold",
                        "normalized_inputs": {
                            "normalized_eps": 5.0,
                            "normalized_bvps": 50.0,
                            "normalized_dividend_capacity_per_share": 3.0,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            paths.on_demand_results_root.mkdir(parents=True, exist_ok=True)
            (paths.on_demand_results_root / "9999.json").write_text(
                json.dumps(
                    {
                        "ticker": "9999",
                        "row": {
                            "ticker": "9999",
                            "name": "Test Co",
                            "price": 60.0,
                            "buffett3_intrinsic": 55.0,
                            "imfs_intrinsic": 58.0,
                            "hybrid_target": 57.0,
                            "quant_score": 52.0,
                            "buffett3_type": "financial",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            paths.final_module_normalized_root.mkdir(parents=True, exist_ok=True)
            for filename, header in {
                "institutional_consensus.csv": "ticker,target_price,rating_normalized\n",
                "news_commentary.csv": "ticker,sentiment,theme\n",
                "public_commentary.csv": "ticker,sentiment,stance\n",
            }.items():
                (paths.final_module_normalized_root / filename).write_text(
                    header,
                    encoding="utf-8",
                )

            summary = build_final_module_payloads(paths, tickers=["9999"])

            self.assertEqual(summary["payload_count"], 1)
            independent_payload = json.loads(
                (paths.final_module_independent_ai_root / "9999.json").read_text(encoding="utf-8")
            )
            commentary_payload = json.loads(
                (paths.final_module_commentary_root / "9999.json").read_text(encoding="utf-8")
            )
            self.assertEqual(independent_payload["ticker"], "9999")
            self.assertEqual(commentary_payload["ticker"], "9999")
            self.assertEqual(independent_payload["industry_bucket"], "金融股")
            self.assertIn("Test Co", commentary_payload["final_conclusion"]["summary"])

    def test_build_final_module_payloads_can_use_on_demand_result_without_top100_results_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            paths = WorkspacePaths(
                workspace_root=workspace_root,
                shared_data_root=workspace_root / "shared",
            )

            results_root = paths.artifacts_root / "results"
            (results_root / "buffett3_payloads").mkdir(parents=True, exist_ok=True)
            (results_root / "buffett3_payloads" / "2330.json").write_text(
                json.dumps(
                    {
                        "ticker": "2330",
                        "company_name": "TSMC",
                        "classification": "high_quality_compounder",
                        "rating": "昂貴",
                        "signal": "hold",
                        "normalized_inputs": {
                            "normalized_eps": 50.0,
                            "normalized_fcf_per_share": 30.0,
                            "normalized_dividend_capacity_per_share": 10.0,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            paths.on_demand_results_root.mkdir(parents=True, exist_ok=True)
            (paths.on_demand_results_root / "2330.json").write_text(
                json.dumps(
                    {
                        "ticker": "2330",
                        "row": {
                            "ticker": "2330",
                            "name": "TSMC",
                            "price": 1000.0,
                            "buffett3_intrinsic": 800.0,
                            "imfs_intrinsic": None,
                            "hybrid_target": None,
                            "quant_score": None,
                            "buffett3_type": "high_quality_compounder",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            paths.final_module_normalized_root.mkdir(parents=True, exist_ok=True)
            for filename, header in {
                "institutional_consensus.csv": "ticker,target_price,rating_normalized\n",
                "news_commentary.csv": "ticker,sentiment,theme\n",
                "public_commentary.csv": "ticker,sentiment,stance\n",
            }.items():
                (paths.final_module_normalized_root / filename).write_text(
                    header,
                    encoding="utf-8",
                )

            summary = build_final_module_payloads(paths, tickers=["2330"])

            self.assertEqual(summary["payload_count"], 1)
            self.assertTrue((paths.final_module_independent_ai_root / "2330.json").exists())
            self.assertTrue((paths.final_module_commentary_root / "2330.json").exists())


if __name__ == "__main__":
    unittest.main()
