from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = WORKSPACE_ROOT / ".deps"
if str(DEPS_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPS_ROOT))

import pandas as pd

from tw_valuation_models.dataset import (
    _convert_roc_date,
    _deduplicate_buffett3_financials,
    _detect_financial_tickers,
    _fetch_dividend_history_official_v2,
    _fetch_monthly_revenue_official,
    _fetch_official_financial_statements,
    _fetch_valuation_snapshot_official,
    _extract_ticker_from_row,
    _load_yfinance_fallback_fundamentals,
)


class DatasetHelpersTests(unittest.TestCase):
    def test_fetch_twse_openapi_json_decodes_utf8_payload_with_non_utf8_response_encoding(self) -> None:
        from tw_valuation_models import dataset as dataset_module

        original_get = dataset_module.requests.get

        class FakeResponse:
            def __init__(self) -> None:
                self.content = '[{"公司代號":"2330","公司名稱":"台積電"}]'.encode("utf-8")
                self.encoding = "ISO-8859-1"
                self.apparent_encoding = "utf-8"

            def raise_for_status(self) -> None:
                return None

            def json(self) -> list[dict[str, str]]:
                return [{"Ã¥Â…Â¬Ã¥ÂÂ¸Ã¤Â»Â£Ã¨Â™ÂŸ": "2330"}]

        dataset_module.requests.get = lambda *args, **kwargs: FakeResponse()
        try:
            rows = dataset_module._fetch_twse_openapi_json("https://example.com/mock.json")
        finally:
            dataset_module.requests.get = original_get

        self.assertEqual(rows[0]["公司代號"], "2330")
        self.assertEqual(rows[0]["公司名稱"], "台積電")

    def test_convert_roc_date(self) -> None:
        self.assertEqual(_convert_roc_date("1150514"), "2026-05-14")
        self.assertEqual(_convert_roc_date("115/05/14"), "2026-05-14")
        self.assertEqual(_convert_roc_date("2026/05/14"), "2026-05-14")

    def test_detect_financial_tickers(self) -> None:
        universe_df = pd.DataFrame(
            [
                {"ticker": "2330", "industry": "半導體"},
                {"ticker": "2881", "industry": "金融保險"},
                {"ticker": "2603", "industry": "航運"},
            ]
        )
        detected = _detect_financial_tickers(universe_df, {"2330", "2881", "2603"})
        self.assertEqual(detected, {"2881"})

    def test_extract_ticker_from_row_requires_code_like_key(self) -> None:
        self.assertEqual(_extract_ticker_from_row({"股利年度": "2881"}), "")
        self.assertEqual(_extract_ticker_from_row({"Code": "2330"}), "2330")

    def test_fetch_valuation_snapshot_official_normalizes_rows(self) -> None:
        from tw_valuation_models import dataset as dataset_module

        original = dataset_module._fetch_twse_openapi_json
        dataset_module._fetch_twse_openapi_json = lambda url: [
            {
                "證券代號": "2330",
                "資料日期": "1150514",
                "本益比": "34.27",
                "股價淨值比": "10.86",
                "殖利率(%)": "0.97",
            },
            {
                "證券代號": "2881",
                "資料日期": "1150514",
                "本益比": "12.21",
                "股價淨值比": "1.50",
                "殖利率(%)": "4.49",
            },
        ]
        try:
            df = _fetch_valuation_snapshot_official({"2330"})
        finally:
            dataset_module._fetch_twse_openapi_json = original
        self.assertEqual(list(df["ticker"]), ["2330"])
        self.assertAlmostEqual(float(df.iloc[0]["pb_ratio"]), 10.86)
        self.assertEqual(df.iloc[0]["date"], "2026-05-14")

    def test_fetch_monthly_revenue_official_normalizes_rows(self) -> None:
        from tw_valuation_models import dataset as dataset_module

        original = dataset_module._fetch_twse_openapi_json
        dataset_module._fetch_twse_openapi_json = lambda url: [
            {
                "公司代號": "2330",
                "公司名稱": "台積電",
                "資料年月": "11504",
                "營業收入-當月營收": "349,567,890",
                "營業收入-去年同月增減(%)": "17.50",
            },
            {
                "公司代號": "2881",
                "公司名稱": "富邦金",
                "資料年月": "11504",
                "營業收入-當月營收": "12,345",
                "營業收入-去年同月增減(%)": "5.00",
            },
        ]
        try:
            df = _fetch_monthly_revenue_official(["2330"], months=15)
        finally:
            dataset_module._fetch_twse_openapi_json = original
        self.assertEqual(list(df["stock_id"]), ["2330"])
        self.assertEqual(df.iloc[0]["period"], "2026-04-01")
        self.assertAlmostEqual(float(df.iloc[0]["revenue_yoy"]), 17.50)

    def test_fetch_dividend_history_official_v2_captures_stock_dividend_components(self) -> None:
        from tw_valuation_models import dataset as dataset_module

        original = dataset_module._fetch_twse_openapi_json
        dataset_module._fetch_twse_openapi_json = lambda url: [
            {
                "公司代號": "2881",
                "股利年度": "114",
                "股東配發-盈餘分配之現金股利(元/股)": "4.25",
                "股東配發-盈餘轉增資配股(元/股)": "0.25",
                "董事會（擬議）股利分派日": "1140502",
            }
        ]
        try:
            df = _fetch_dividend_history_official_v2({"2881"})
        finally:
            dataset_module._fetch_twse_openapi_json = original

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["ticker"], "2881")
        self.assertAlmostEqual(float(df.iloc[0]["cash_dividend"]), 4.25)
        self.assertAlmostEqual(float(df.iloc[0]["stock_dividend"]), 0.25)
        self.assertAlmostEqual(float(df.iloc[0]["total_dividend"]), 4.50)

    def test_fetch_official_financial_statements_merges_income_and_balance(self) -> None:
        from tw_valuation_models import dataset as dataset_module

        original = dataset_module._fetch_twse_openapi_json

        def fake_fetch(url: str) -> list[dict[str, object]]:
            if "t187ap06" in url:
                return [
                    {
                        "公司代號": "2330",
                        "出表日期": "115/03/31",
                        "年度": "115",
                        "季別": "1",
                        "營業收入": "1000",
                        "本期淨利（淨損）": "300",
                        "營業利益（損失）": "400",
                        "基本每股盈餘（元）": "12.34",
                        "權益報酬率(%)": "25.5",
                    }
                ]
            return [
                {
                    "公司代號": "2330",
                    "出表日期": "115/03/31",
                    "年度": "115",
                    "季別": "1",
                    "權益總額": "2000",
                    "資產總額": "5000",
                    "負債總額": "3000",
                    "流動資產": "1800",
                    "流動負債": "1200",
                    "每股參考淨值": "50.5",
                    "現金及約當現金": "600",
                    "長期借款": "400",
                }
            ]

        dataset_module._fetch_twse_openapi_json = fake_fetch
        try:
            df = _fetch_official_financial_statements(
                tickers=["2330"],
                income_url="mock_t187ap06",
                balance_url="mock_t187ap07",
                source_label="general",
            )
        finally:
            dataset_module._fetch_twse_openapi_json = original
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["fiscal_period"], "Q1")
        self.assertAlmostEqual(float(df.iloc[0]["eps"]), 12.34)
        self.assertAlmostEqual(float(df.iloc[0]["book_value_per_share"]), 50.5)

    def test_load_yfinance_fallback_fundamentals_normalizes_annual(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_root = Path(temp_dir)
            fundamentals_root = dataset_root / "fundamentals"
            fundamentals_root.mkdir(parents=True)
            pd.DataFrame(
                [
                    {
                        "date": "2025-12-31",
                        "revenue": 1000,
                        "net_income": 300,
                        "operating_income": 400,
                        "equity": 2000,
                        "total_assets": 5000,
                        "total_liabilities": 3000,
                        "current_assets": 1800,
                        "current_liabilities": 1200,
                        "shares_outstanding": 100,
                        "eps": 3.0,
                        "book_value_per_share": 20.0,
                        "roe": 15.0,
                    }
                ]
            ).to_csv(fundamentals_root / "2330_annual.csv", index=False)
            df = _load_yfinance_fallback_fundamentals(dataset_root, ["2330"], "annual")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["ticker"], "2330")
        self.assertEqual(df.iloc[0]["fiscal_period"], "FY")
        self.assertEqual(df.iloc[0]["source_name"], "yfinance.fallback.annual")

    def test_deduplicate_buffett3_financials_prefers_twse_source(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "ticker": "2330",
                    "report_date": "2026-03-31",
                    "fiscal_year": 2026,
                    "fiscal_period": "Q1",
                    "revenue": 1000.0,
                    "net_income": None,
                    "operating_income": None,
                    "operating_cash_flow": None,
                    "capital_expenditure": None,
                    "free_cash_flow": None,
                    "equity": None,
                    "total_assets": None,
                    "total_liabilities": None,
                    "current_assets": None,
                    "current_liabilities": None,
                    "shares_outstanding": None,
                    "eps": None,
                    "book_value_per_share": None,
                    "roe": None,
                    "cash_and_equivalents": None,
                    "total_debt": None,
                    "source_name": "yfinance.fallback.quarterly",
                },
                {
                    "ticker": "2330",
                    "report_date": "2026-03-31",
                    "fiscal_year": 2026,
                    "fiscal_period": "Q1",
                    "revenue": 2000.0,
                    "net_income": None,
                    "operating_income": None,
                    "operating_cash_flow": None,
                    "capital_expenditure": None,
                    "free_cash_flow": None,
                    "equity": None,
                    "total_assets": None,
                    "total_liabilities": None,
                    "current_assets": None,
                    "current_liabilities": None,
                    "shares_outstanding": None,
                    "eps": None,
                    "book_value_per_share": None,
                    "roe": None,
                    "cash_and_equivalents": None,
                    "total_debt": None,
                    "source_name": "twse.general.income",
                },
            ]
        )
        deduped = _deduplicate_buffett3_financials(df)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped.iloc[0]["source_name"], "twse.general.income")
        self.assertAlmostEqual(float(deduped.iloc[0]["revenue"]), 2000.0)


if __name__ == "__main__":
    unittest.main()
