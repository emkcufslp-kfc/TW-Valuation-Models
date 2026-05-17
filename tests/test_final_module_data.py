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

from tw_valuation_models.config import WorkspacePaths
from tw_valuation_models.csv_utils import read_csv_rows
from tw_valuation_models.final_module_data import (
    build_final_module_snapshot,
    fetch_final_module_sources,
    refresh_live_final_module_context,
)


class FinalModuleDataTests(unittest.TestCase):
    def test_fetch_final_module_sources_saves_raw_html_under_shared_data_root(self) -> None:
        from tw_valuation_models import final_module_data as module

        original_get = module.requests.get

        class FakeResponse:
            def __init__(self, url: str) -> None:
                self.content = f"<html><body>{url}</body></html>".encode("utf-8")
                self.headers = {"content-type": "text/html; charset=utf-8"}

            def raise_for_status(self) -> None:
                return None

        module.requests.get = lambda url, **kwargs: FakeResponse(url)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                paths = WorkspacePaths(workspace_root=root, shared_data_root=root / "shared")
                summary = fetch_final_module_sources(paths, tickers=["2330"])
                self.assertTrue(
                    (paths.final_module_shared_root / "latest_fetch_summary.json").exists()
                )
                for record in summary["results"]:
                    raw_path = Path(record["raw_file"])
                    self.assertTrue(raw_path.exists())
                    self.assertIn("2330", raw_path.as_posix())
                    self.assertEqual(
                        raw_path.read_text(encoding="utf-8"),
                        f"<html><body>{record['url']}</body></html>",
                    )
        finally:
            module.requests.get = original_get

        self.assertEqual(summary["error_count"], 0)
        self.assertGreater(summary["downloaded_count"], 0)

    def test_build_final_module_snapshot_writes_normalized_tables_and_market_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = WorkspacePaths(workspace_root=root, shared_data_root=root / "shared")
            summary = build_final_module_snapshot(paths, tickers=["2330", "2881"])

            self.assertEqual(summary["counts"]["market_view_snapshot"], 2)
            institutional_rows = read_csv_rows(
                paths.final_module_normalized_root / "institutional_consensus.csv"
            )
            news_rows = read_csv_rows(paths.final_module_normalized_root / "news_commentary.csv")
            public_rows = read_csv_rows(paths.final_module_normalized_root / "public_commentary.csv")
            market_rows = read_csv_rows(
                paths.final_module_normalized_root / "market_view_snapshot.csv"
            )
            artifacts_summary = json.loads(
                (paths.final_module_artifacts_root / "summary.json").read_text(encoding="utf-8")
            )

        self.assertGreater(len(institutional_rows), 0)
        self.assertGreater(len(news_rows), 0)
        self.assertGreater(len(public_rows), 0)
        self.assertEqual({row["ticker"] for row in market_rows}, {"2330", "2881"})
        self.assertTrue(any(row["divergence_summary"] for row in market_rows))
        self.assertIn("target_price", institutional_rows[0])
        self.assertEqual(artifacts_summary["counts"]["market_view_snapshot"], 2)

    def test_refresh_live_final_module_context_replaces_selected_ticker_rows(self) -> None:
        from tw_valuation_models import final_module_data as module

        original_get = module.requests.get

        class FakeResponse:
            def __init__(self, url: str) -> None:
                self.content = f"<html><head><title>{url}</title></head><body>{url}</body></html>".encode("utf-8")
                self.headers = {"content-type": "text/html; charset=utf-8"}

            def raise_for_status(self) -> None:
                return None

        module.requests.get = lambda url, **kwargs: FakeResponse(url)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                paths = WorkspacePaths(workspace_root=root, shared_data_root=root / "shared")
                paths.final_module_normalized_root.mkdir(parents=True, exist_ok=True)
                (paths.final_module_normalized_root / "institutional_consensus.csv").write_text(
                    "ticker,as_of_date,source_name,institution_name,report_date,rating_raw,rating_normalized,target_price,target_price_low,target_price_high,eps_fy1,eps_fy2,thesis_summary,url,raw_file,is_stale,ingested_at\n2330,2026-05-01,old,old,2026-05-01,old,hold,0,0,0,0,0,old,http://old,,false,2026-05-01T00:00:00+00:00\n",
                    encoding="utf-8",
                )
                (paths.final_module_normalized_root / "news_commentary.csv").write_text(
                    "ticker,as_of_date,publish_date,source_name,headline,summary,sentiment,theme,is_company_specific,url,raw_file,is_stale,ingested_at\n2330,2026-05-01,2026-05-01,old,old,old,neutral,valuation,true,http://old,,false,2026-05-01T00:00:00+00:00\n",
                    encoding="utf-8",
                )
                (paths.final_module_normalized_root / "public_commentary.csv").write_text(
                    "ticker,as_of_date,publish_date,source_name,channel_type,author_name,headline_or_topic,summary,sentiment,stance,evidence_strength,url,raw_file,is_stale,ingested_at\n2330,2026-05-01,2026-05-01,old,forum,old,old,old,neutral,hold,low,http://old,,false,2026-05-01T00:00:00+00:00\n",
                    encoding="utf-8",
                )
                (paths.final_module_normalized_root / "market_view_snapshot.csv").write_text(
                    "ticker,as_of_date,institution_sentiment_score,public_sentiment_score,institution_avg_target_price,institution_target_count,institution_positive_count,institution_negative_count,public_bullish_count,public_bearish_count,news_bullish_count,news_bearish_count,divergence_flag,divergence_summary,generated_at\n2330,2026-05-01,0,0,0,0,0,0,0,0,0,0,false,old,2026-05-01T00:00:00+00:00\n",
                    encoding="utf-8",
                )

                summary = refresh_live_final_module_context(paths, ["2330"])
                institutional_rows = read_csv_rows(paths.final_module_normalized_root / "institutional_consensus.csv")
                news_rows = read_csv_rows(paths.final_module_normalized_root / "news_commentary.csv")
                public_rows = read_csv_rows(paths.final_module_normalized_root / "public_commentary.csv")
                market_rows = read_csv_rows(paths.final_module_normalized_root / "market_view_snapshot.csv")

                self.assertEqual(summary["error_count"], 0)
                self.assertEqual(len(institutional_rows), 1)
                self.assertEqual(len(news_rows), 1)
                self.assertEqual(len(public_rows), 1)
                self.assertEqual(len(market_rows), 1)
                self.assertEqual(institutional_rows[0]["ticker"], "2330")
                self.assertIn("Yahoo", institutional_rows[0]["source_name"])
        finally:
            module.requests.get = original_get


if __name__ == "__main__":
    unittest.main()
