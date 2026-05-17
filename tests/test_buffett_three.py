from __future__ import annotations

import sys
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = WORKSPACE_ROOT / ".deps"
if str(DEPS_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPS_ROOT))

import pandas as pd

from tw_valuation_models.models.buffett_three import classify_company, run_buffett_three_valuation


class BuffettThreeTests(unittest.TestCase):
    def test_classify_company(self) -> None:
        self.assertEqual(classify_company(ticker="2881", company_name="富邦金", industry="金融保險")[0], "financial")
        self.assertEqual(classify_company(ticker="2603", company_name="長榮", industry="航運")[0], "cyclical")
        self.assertEqual(
            classify_company(ticker="2412", company_name="中華電", industry="通信網路")[0],
            "defensive_dividend",
        )
        self.assertEqual(classify_company(ticker="1101", company_name="台泥", industry="水泥工業")[0], "cyclical")
        self.assertEqual(classify_company(ticker="1301", company_name="台塑", industry="塑膠工業")[0], "cyclical")
        self.assertEqual(
            classify_company(ticker="3008", company_name="大立光電", industry="農業科技")[0],
            "high_quality_compounder",
        )
        self.assertEqual(
            classify_company(ticker="1795", company_name="美時化學製藥", industry="電子通路")[0],
            "high_quality_compounder",
        )
        self.assertEqual(
            classify_company(ticker="1476", company_name="儒鴻", industry="紡織纖維")[0],
            "high_quality_compounder",
        )
        self.assertEqual(
            classify_company(ticker="2207", company_name="和泰車", industry="汽車工業")[0],
            "high_quality_compounder",
        )
        self.assertEqual(
            classify_company(ticker="2409", company_name="友達光電", industry="農業科技")[0],
            "cyclical",
        )
        self.assertEqual(
            classify_company(ticker="2408", company_name="南亞科技", industry="其他電子業")[0],
            "cyclical",
        )

    def test_run_buffett_three_valuation_compounder(self) -> None:
        annual_df = pd.DataFrame(
            [
                {
                    "ticker": "2330",
                    "report_date": "2023-12-31",
                    "eps": 32.0,
                    "free_cash_flow": 800.0,
                    "shares_outstanding": 10.0,
                    "book_value_per_share": 120.0,
                    "roe": 23.0,
                    "equity": 1200.0,
                    "total_liabilities": 600.0,
                    "current_assets": 700.0,
                    "current_liabilities": 300.0,
                },
                {
                    "ticker": "2330",
                    "report_date": "2024-12-31",
                    "eps": 35.0,
                    "free_cash_flow": 900.0,
                    "shares_outstanding": 10.0,
                    "book_value_per_share": 135.0,
                    "roe": 24.5,
                    "equity": 1350.0,
                    "total_liabilities": 620.0,
                    "current_assets": 760.0,
                    "current_liabilities": 320.0,
                },
                {
                    "ticker": "2330",
                    "report_date": "2025-12-31",
                    "eps": 40.0,
                    "free_cash_flow": 950.0,
                    "shares_outstanding": 10.0,
                    "book_value_per_share": 150.0,
                    "roe": 25.0,
                    "equity": 1500.0,
                    "total_liabilities": 650.0,
                    "current_assets": 800.0,
                    "current_liabilities": 340.0,
                },
            ]
        )
        quarterly_df = pd.DataFrame(
            [
                {
                    "ticker": "2330",
                    "report_date": "2026-03-31",
                    "eps": 10.0,
                    "current_assets": 820.0,
                    "current_liabilities": 350.0,
                    "equity": 1520.0,
                    "total_liabilities": 660.0,
                }
            ]
        )
        valuation_df = pd.DataFrame(
            [{"ticker": "2330", "date": "2026-05-14", "pe_ratio": 34.27, "pb_ratio": 10.86, "dividend_yield": 0.97}]
        )
        dividend_df = pd.DataFrame(
            [{"ticker": "2330", "fiscal_year": 115, "cash_dividend": 18.0, "announcement_date": "2026-05-12"}]
        )
        monthly_revenue_df = pd.DataFrame(
            [{"stock_id": "2330", "period": "2026-04-01", "revenue_yoy": 17.5}]
        )
        taiex_df = pd.DataFrame(
            {
                "Date": pd.date_range("2025-01-01", periods=220, freq="D"),
                "Close": list(range(220)),
            }
        )
        result = run_buffett_three_valuation(
            ticker="2330",
            company_name="台積電",
            industry="半導體",
            current_price=2270.0,
            annual_df=annual_df,
            quarterly_df=quarterly_df,
            valuation_df=valuation_df,
            dividend_df=dividend_df,
            monthly_revenue_df=monthly_revenue_df,
            taiex_df=taiex_df,
        )
        self.assertEqual(result["classification"], "high_quality_compounder")
        self.assertEqual(result["company_type"], "high_quality_compounder")
        self.assertGreater(result["final_fair_value_per_share"], 0)
        self.assertEqual(result["final_fair_value"], result["final_fair_value_per_share"])
        self.assertEqual(result["blended_fair_value"], result["blended_normalized_valuation"])
        self.assertIn("rating", result)
        self.assertIn("modifiers", result)
        self.assertEqual(len(result["valuation_legs"]), 4)
        dividend_leg = [leg for leg in result["valuation_legs"] if leg["name"] == "dividend_yield_or_ddm"][0]
        self.assertEqual(dividend_leg["status"], "ready")
        self.assertIsNotNone(dividend_leg["blended_value"])
        self.assertNotIn("some_valuation_legs_not_ready", result["manual_review_flags"])

    def test_run_buffett_three_valuation_cyclical_marks_ev_leg_not_ready(self) -> None:
        annual_df = pd.DataFrame(
            [
                {
                    "ticker": "2603",
                    "report_date": "2023-12-31",
                    "eps": 20.0,
                    "free_cash_flow": 400.0,
                    "shares_outstanding": 10.0,
                    "book_value_per_share": 180.0,
                    "roe": 12.0,
                    "equity": 1800.0,
                    "total_liabilities": 900.0,
                    "current_assets": 1000.0,
                    "current_liabilities": 450.0,
                },
                {
                    "ticker": "2603",
                    "report_date": "2024-12-31",
                    "eps": 18.0,
                    "free_cash_flow": 380.0,
                    "shares_outstanding": 10.0,
                    "book_value_per_share": 200.0,
                    "roe": 10.0,
                    "equity": 2000.0,
                    "total_liabilities": 950.0,
                    "current_assets": 1020.0,
                    "current_liabilities": 470.0,
                },
                {
                    "ticker": "2603",
                    "report_date": "2025-12-31",
                    "eps": 12.0,
                    "free_cash_flow": 350.0,
                    "shares_outstanding": 10.0,
                    "book_value_per_share": 220.0,
                    "roe": 8.0,
                    "equity": 2200.0,
                    "total_liabilities": 1000.0,
                    "current_assets": 1030.0,
                    "current_liabilities": 480.0,
                },
            ]
        )
        result = run_buffett_three_valuation(
            ticker="2603",
            company_name="長榮",
            industry="航運",
            current_price=211.5,
            annual_df=annual_df,
            quarterly_df=pd.DataFrame(),
            valuation_df=pd.DataFrame([{"ticker": "2603", "pe_ratio": 6.68, "pb_ratio": 0.81, "dividend_yield": 7.57}]),
            dividend_df=pd.DataFrame([{"ticker": "2603", "fiscal_year": 114, "cash_dividend": 16.0}]),
            monthly_revenue_df=pd.DataFrame([{"stock_id": "2603", "period": "2026-04-01", "revenue_yoy": 4.5}]),
            taiex_df=pd.DataFrame({"Date": pd.date_range("2025-01-01", periods=220, freq="D"), "Close": list(range(220))}),
        )
        ev_leg = [leg for leg in result["valuation_legs"] if leg["name"] == "normalized_ev_ebitda"][0]
        self.assertEqual(result["classification"], "cyclical")
        self.assertIn("rating", result)
        self.assertEqual(ev_leg["status"], "not_ready")
        self.assertIn("cyclical_model_uses_partial_leg_set", result["manual_review_flags"])
        self.assertNotIn("some_valuation_legs_not_ready", result["manual_review_flags"])

    def test_run_buffett_three_valuation_compounder_floors_negative_equity_outputs(self) -> None:
        annual_df = pd.DataFrame(
            [
                {
                    "ticker": "9999",
                    "report_date": "2023-12-31",
                    "eps": -4.0,
                    "free_cash_flow": -120.0,
                    "shares_outstanding": 10.0,
                    "book_value_per_share": 40.0,
                    "roe": -9.0,
                    "equity": 400.0,
                    "total_liabilities": 250.0,
                    "current_assets": 300.0,
                    "current_liabilities": 180.0,
                },
                {
                    "ticker": "9999",
                    "report_date": "2024-12-31",
                    "eps": -3.0,
                    "free_cash_flow": -100.0,
                    "shares_outstanding": 10.0,
                    "book_value_per_share": 42.0,
                    "roe": -7.0,
                    "equity": 420.0,
                    "total_liabilities": 255.0,
                    "current_assets": 305.0,
                    "current_liabilities": 182.0,
                },
                {
                    "ticker": "9999",
                    "report_date": "2025-12-31",
                    "eps": -2.0,
                    "free_cash_flow": -90.0,
                    "shares_outstanding": 10.0,
                    "book_value_per_share": 45.0,
                    "roe": -5.0,
                    "equity": 450.0,
                    "total_liabilities": 260.0,
                    "current_assets": 310.0,
                    "current_liabilities": 185.0,
                },
            ]
        )
        result = run_buffett_three_valuation(
            ticker="9999",
            company_name="測試公司",
            industry="半導體業",
            current_price=100.0,
            annual_df=annual_df,
            quarterly_df=pd.DataFrame(),
            valuation_df=pd.DataFrame([{"ticker": "9999", "pe_ratio": 20.0, "pb_ratio": 2.0, "dividend_yield": 0.0}]),
            dividend_df=pd.DataFrame([{"ticker": "9999", "fiscal_year": 114, "cash_dividend": 0.0}]),
            monthly_revenue_df=pd.DataFrame([{"stock_id": "9999", "period": "2026-04-01", "revenue_yoy": -10.0}]),
            taiex_df=pd.DataFrame({"Date": pd.date_range("2025-01-01", periods=220, freq="D"), "Close": list(range(220))}),
        )
        self.assertEqual(result["classification"], "high_quality_compounder")
        self.assertGreaterEqual(result["final_fair_value_per_share"], 0.0)
        fcf_leg = [leg for leg in result["valuation_legs"] if leg["name"] == "fcf_yield"][0]
        pe_leg = [leg for leg in result["valuation_legs"] if leg["name"] == "normalized_pe"][0]
        residual_leg = [leg for leg in result["valuation_legs"] if leg["name"] == "residual_earnings"][0]
        self.assertEqual(fcf_leg["blended_value"], 0.0)
        self.assertEqual(pe_leg["blended_value"], 0.0)
        self.assertEqual(residual_leg["blended_value"], 0.0)
        self.assertIn("negative_equity_leg_value_floored_to_zero", pe_leg["notes"])
        self.assertIn("negative_equity_leg_value_floored_to_zero", residual_leg["notes"])


if __name__ == "__main__":
    unittest.main()
