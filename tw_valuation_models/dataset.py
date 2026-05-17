from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import urllib3
import yfinance as yf
import yfinance.cache as yf_cache

from .config import WorkspacePaths


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _configure_yfinance_cache() -> None:
    cache_root = Path(__file__).resolve().parents[1] / "artifacts" / "runtime" / "yfinance_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_dir = str(cache_root)
    yf.set_tz_cache_location(cache_dir)
    yf_cache._CookieDBManager.set_location(cache_dir)


_configure_yfinance_cache()

TOP100_MONTHS_OF_REVENUE = 15
TWSE_OPENAPI_BASE = "https://openapi.twse.com.tw/v1"
TWSE_BWIBBU_ALL_URL = f"{TWSE_OPENAPI_BASE}/exchangeReport/BWIBBU_ALL"
TWSE_DIVIDEND_URL = f"{TWSE_OPENAPI_BASE}/opendata/t187ap45_L"
TWSE_MONTHLY_REVENUE_URL = f"{TWSE_OPENAPI_BASE}/opendata/t187ap05_L"
TWSE_INCOME_GENERAL_URL = f"{TWSE_OPENAPI_BASE}/opendata/t187ap06_L_ci"
TWSE_BALANCE_GENERAL_URL = f"{TWSE_OPENAPI_BASE}/opendata/t187ap07_L_ci"
TWSE_INCOME_FINANCIAL_URL = f"{TWSE_OPENAPI_BASE}/opendata/t187ap06_L_basi"
TWSE_BALANCE_FINANCIAL_URL = f"{TWSE_OPENAPI_BASE}/opendata/t187ap07_L_basi"
MOPS_MONTHLY_REVENUE_URL_TEMPLATE = (
    "https://mops.twse.com.tw/nas/t21/sii/t21sc03_{roc_year}_{month}_0.html"
)
EMPTY_REVENUE_COLUMNS = [
    "stock_id",
    "stock_name",
    "monthly_revenue",
    "revenue_yoy",
    "year",
    "month",
    "period",
]
EMPTY_FINANCIAL_COLUMNS = [
    "date",
    "revenue",
    "net_income",
    "operating_income",
    "operating_cash_flow",
    "capital_expenditure",
    "free_cash_flow",
    "equity",
    "total_assets",
    "total_liabilities",
    "current_assets",
    "current_liabilities",
    "shares_outstanding",
    "eps",
    "book_value_per_share",
    "roe",
]
BUFFETT3_VALUATION_COLUMNS = [
    "ticker",
    "date",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield",
    "source_name",
]
BUFFETT3_DIVIDEND_COLUMNS = [
    "ticker",
    "fiscal_year",
    "cash_dividend",
    "stock_dividend",
    "total_dividend",
    "announcement_date",
    "source_name",
]
BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS = [
    "ticker",
    "report_date",
    "fiscal_year",
    "fiscal_period",
    "revenue",
    "net_income",
    "operating_income",
    "operating_cash_flow",
    "capital_expenditure",
    "free_cash_flow",
    "equity",
    "total_assets",
    "total_liabilities",
    "current_assets",
    "current_liabilities",
    "shares_outstanding",
    "eps",
    "book_value_per_share",
    "roe",
    "cash_and_equivalents",
    "total_debt",
    "source_name",
]


@dataclass
class DatasetSummary:
    top100_count: int
    downloaded_price_files: int
    reused_price_files: int
    downloaded_fundamental_profiles: int
    reused_fundamental_profiles: int
    monthly_revenue_rows: int
    generated_at: str


def build_top100_dataset(paths: WorkspacePaths, top_n: int = 100) -> dict[str, object]:
    dataset_root = paths.artifacts_root / "datasets" / "top100"
    prices_root = dataset_root / "prices"
    fundamentals_root = dataset_root / "fundamentals"
    prices_root.mkdir(parents=True, exist_ok=True)
    fundamentals_root.mkdir(parents=True, exist_ok=True)

    normalized_root = paths.normalized_root
    if not normalized_root.exists():
        raise FileNotFoundError("Normalize shared data before building the top100 dataset.")

    universe_df = pd.read_csv(normalized_root / "universe_snapshot.csv")
    valuation_df = pd.read_csv(normalized_root / "valuation_snapshot.csv")
    fundamentals_snapshot_df = pd.read_csv(normalized_root / "fundamentals_snapshot.csv")
    universe_df["ticker"] = universe_df["ticker"].map(_normalize_ticker)
    valuation_df["ticker"] = valuation_df["ticker"].map(_normalize_ticker)
    fundamentals_snapshot_df["ticker"] = fundamentals_snapshot_df["ticker"].map(_normalize_ticker)

    top100_df = fundamentals_snapshot_df.copy()
    top100_df["market_cap_num"] = pd.to_numeric(top100_df["market_cap"], errors="coerce")
    top100_df = top100_df.dropna(subset=["market_cap_num"]).sort_values(
        "market_cap_num", ascending=False
    )
    top100_df = top100_df.head(top_n).copy()
    top100_tickers = top100_df["ticker"].map(_normalize_ticker).tolist()

    top100_universe = universe_df[universe_df["ticker"].isin(top100_tickers)].copy()
    top100_universe["market_cap"] = top100_universe["ticker"].map(
        top100_df.set_index("ticker")["market_cap"]
    )
    top100_universe = top100_universe.sort_values("market_cap", ascending=False)
    top100_universe.to_csv(dataset_root / "top100_universe.csv", index=False, encoding="utf-8")

    top100_valuation = valuation_df[valuation_df["ticker"].isin(top100_tickers)].copy()
    top100_valuation.to_csv(
        dataset_root / "top100_valuation_snapshot.csv", index=False, encoding="utf-8"
    )

    top100_fundamentals_snapshot = fundamentals_snapshot_df[
        fundamentals_snapshot_df["ticker"].isin(top100_tickers)
    ].copy()
    top100_fundamentals_snapshot.to_csv(
        dataset_root / "top100_fundamentals_snapshot.csv", index=False, encoding="utf-8"
    )

    downloaded_price_files = 0
    reused_price_files = 0
    price_rows_written = 0
    raw_root = paths.shared_data_root / "raw"
    for ticker in top100_tickers:
        source_price = raw_root / f"{ticker}.csv"
        target_price = prices_root / f"{ticker}.csv"
        if source_price.exists():
            price_df = pd.read_csv(source_price)
            reused_price_files += 1
        elif target_price.exists():
            price_df = pd.read_csv(target_price)
            reused_price_files += 1
        else:
            price_df = _download_price_history(ticker)
            if price_df.empty:
                continue
            downloaded_price_files += 1
        price_df.to_csv(target_price, index=False, encoding="utf-8")
        price_rows_written += len(price_df)

    taiex_source = raw_root / "TAIEX.csv"
    taiex_target = dataset_root / "TAIEX.csv"
    if taiex_source.exists():
        pd.read_csv(taiex_source).to_csv(taiex_target, index=False, encoding="utf-8")
    elif not taiex_target.exists():
        _download_taiex_history().to_csv(taiex_target, index=False, encoding="utf-8")

    annual_financials_index = []
    quarter_financials_index = []
    downloaded_fundamental_profiles = 0
    reused_fundamental_profiles = 0
    for ticker in top100_tickers:
        annual_path = fundamentals_root / f"{ticker}_annual.csv"
        quarterly_path = fundamentals_root / f"{ticker}_quarterly.csv"
        profile_path = fundamentals_root / f"{ticker}_profile.json"

        if annual_path.exists() and quarterly_path.exists() and profile_path.exists():
            annual_df = pd.read_csv(annual_path)
            quarterly_df = pd.read_csv(quarterly_path)
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            reused_fundamental_profiles += 1
        else:
            annual_df, quarterly_df, profile = _download_financial_profile(ticker)
            annual_df.to_csv(annual_path, index=False, encoding="utf-8")
            quarterly_df.to_csv(quarterly_path, index=False, encoding="utf-8")
            profile_path.write_text(
                json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            downloaded_fundamental_profiles += 1
            time.sleep(0.1)

        annual_financials_index.append(
            {"ticker": ticker, "path": str(annual_path), "rows": len(annual_df)}
        )
        quarter_financials_index.append(
            {"ticker": ticker, "path": str(quarterly_path), "rows": len(quarterly_df)}
        )

    annual_index_df = pd.DataFrame(annual_financials_index)
    annual_index_df.to_csv(
        dataset_root / "annual_financials_index.csv", index=False, encoding="utf-8"
    )
    quarterly_index_df = pd.DataFrame(quarter_financials_index)
    quarterly_index_df.to_csv(
        dataset_root / "quarterly_financials_index.csv", index=False, encoding="utf-8"
    )

    monthly_revenue_df = fetch_monthly_revenue_history(top100_tickers, months=TOP100_MONTHS_OF_REVENUE)
    monthly_revenue_df.to_csv(
        dataset_root / "monthly_revenue_history.csv", index=False, encoding="utf-8"
    )

    official_payload = download_buffett3_official_data(
        dataset_root=dataset_root,
        top100_tickers=top100_tickers,
        universe_df=top100_universe,
    )

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    summary = DatasetSummary(
        top100_count=len(top100_tickers),
        downloaded_price_files=downloaded_price_files,
        reused_price_files=reused_price_files,
        downloaded_fundamental_profiles=downloaded_fundamental_profiles,
        reused_fundamental_profiles=reused_fundamental_profiles,
        monthly_revenue_rows=len(monthly_revenue_df),
        generated_at=generated_at,
    )
    payload = {
        "generated_at": generated_at,
        "dataset_root": str(dataset_root),
        "top100_tickers": top100_tickers,
        "summary": summary.__dict__,
        "price_rows_written": price_rows_written,
        "buffett3_official": official_payload,
    }
    (dataset_root / "dataset_summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def build_single_ticker_dataset(paths: WorkspacePaths, ticker: str) -> dict[str, object]:
    ticker = _normalize_ticker(ticker)
    dataset_root = paths.on_demand_datasets_root / ticker
    prices_root = dataset_root / "prices"
    fundamentals_root = dataset_root / "fundamentals"
    prices_root.mkdir(parents=True, exist_ok=True)
    fundamentals_root.mkdir(parents=True, exist_ok=True)

    price_df = _download_price_history(ticker)
    if price_df.empty:
        existing_price = prices_root / f"{ticker}.csv"
        if existing_price.exists():
            price_df = pd.read_csv(existing_price)
    price_df.to_csv(prices_root / f"{ticker}.csv", index=False, encoding="utf-8")

    taiex_target = dataset_root / "TAIEX.csv"
    raw_taiex = paths.shared_data_root / "raw" / "TAIEX.csv"
    if raw_taiex.exists():
        pd.read_csv(raw_taiex).to_csv(taiex_target, index=False, encoding="utf-8")
    else:
        _download_taiex_history().to_csv(taiex_target, index=False, encoding="utf-8")

    annual_df, quarterly_df, profile = _download_financial_profile(ticker)
    annual_path = fundamentals_root / f"{ticker}_annual.csv"
    quarterly_path = fundamentals_root / f"{ticker}_quarterly.csv"
    profile_path = fundamentals_root / f"{ticker}_profile.json"
    annual_df.to_csv(annual_path, index=False, encoding="utf-8")
    quarterly_df.to_csv(quarterly_path, index=False, encoding="utf-8")
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")

    ticker_set = {ticker}
    company_name = str(profile.get("longName") or profile.get("shortName") or ticker)
    industry = str(profile.get("industry") or profile.get("sector") or "")
    universe_df = pd.DataFrame(
        [
            {
                "ticker": ticker,
                "company_name": company_name,
                "industry": industry,
                "market_cap": profile.get("marketCap"),
            }
        ]
    )
    universe_df.to_csv(dataset_root / "top100_universe.csv", index=False, encoding="utf-8")
    pd.DataFrame(
        [
            {
                "ticker": ticker,
                "market_cap": profile.get("marketCap"),
            }
        ]
    ).to_csv(dataset_root / "top100_fundamentals_snapshot.csv", index=False, encoding="utf-8")

    valuation_df = _fetch_valuation_snapshot_official(ticker_set)
    if valuation_df.empty:
        valuation_df = pd.DataFrame(
            [
                {
                    "ticker": ticker,
                    "date": datetime.now(UTC).strftime("%Y-%m-%d"),
                    "pe_ratio": profile.get("trailingPE") or 0.0,
                    "pb_ratio": profile.get("priceToBook") or 0.0,
                    "dividend_yield": (
                        (float(profile.get("dividendYield")) * 100.0)
                        if profile.get("dividendYield") not in (None, "")
                        else 0.0
                    ),
                    "source_name": "yfinance.profile",
                }
            ],
            columns=BUFFETT3_VALUATION_COLUMNS,
        )
    valuation_df.to_csv(dataset_root / "top100_valuation_snapshot.csv", index=False, encoding="utf-8")
    valuation_df.to_csv(dataset_root / "buffett3_valuation_snapshot.csv", index=False, encoding="utf-8")

    dividend_df = _fetch_dividend_history_official_v2(ticker_set)
    dividend_df.to_csv(dataset_root / "buffett3_dividend_history.csv", index=False, encoding="utf-8")

    monthly_revenue_df = _fetch_monthly_revenue_official([ticker], months=TOP100_MONTHS_OF_REVENUE)
    monthly_revenue_df.to_csv(dataset_root / "monthly_revenue_history.csv", index=False, encoding="utf-8")
    monthly_revenue_df.to_csv(
        dataset_root / "buffett3_monthly_revenue_history.csv", index=False, encoding="utf-8"
    )

    financial_tickers = _detect_financial_tickers(universe_df, ticker_set)
    general_tickers = sorted(ticker_set - financial_tickers)
    annual_frames: list[pd.DataFrame] = []
    quarterly_frames: list[pd.DataFrame] = []
    official_statement_tickers: set[str] = set()
    official_annual_tickers: set[str] = set()
    official_quarterly_tickers: set[str] = set()
    manifest: list[dict[str, object]] = []

    manifest.append(
        _manifest_entry(
            domain="valuation_snapshot_current",
            source_name="single_ticker.current",
            target_path=dataset_root / "buffett3_valuation_snapshot.csv",
            row_count=len(valuation_df),
            requested_tickers=[ticker],
            covered_tickers=sorted(set(valuation_df["ticker"].astype(str))) if not valuation_df.empty else [],
        )
    )
    manifest.append(
        _manifest_entry(
            domain="dividend_history",
            source_name="single_ticker.current",
            target_path=dataset_root / "buffett3_dividend_history.csv",
            row_count=len(dividend_df),
            requested_tickers=[ticker],
            covered_tickers=sorted(set(dividend_df["ticker"].astype(str))) if not dividend_df.empty else [],
        )
    )
    manifest.append(
        _manifest_entry(
            domain="monthly_revenue_history",
            source_name="single_ticker.current",
            target_path=dataset_root / "buffett3_monthly_revenue_history.csv",
            row_count=len(monthly_revenue_df),
            requested_tickers=[ticker],
            covered_tickers=(
                sorted(set(monthly_revenue_df["stock_id"].astype(str)))
                if not monthly_revenue_df.empty and "stock_id" in monthly_revenue_df.columns
                else []
            ),
        )
    )

    for label, income_url, balance_url, tickers in [
        ("general", TWSE_INCOME_GENERAL_URL, TWSE_BALANCE_GENERAL_URL, general_tickers),
        ("financial", TWSE_INCOME_FINANCIAL_URL, TWSE_BALANCE_FINANCIAL_URL, sorted(financial_tickers)),
    ]:
        if not tickers:
            continue
        official_financial_df = _fetch_official_financial_statements(
            tickers=tickers,
            income_url=income_url,
            balance_url=balance_url,
            source_label=label,
        )
        if not official_financial_df.empty:
            official_statement_tickers.update(set(official_financial_df["ticker"].astype(str)))
        annual_official = official_financial_df[official_financial_df["fiscal_period"] == "FY"].copy()
        quarterly_official = official_financial_df[
            official_financial_df["fiscal_period"] != "FY"
        ].copy()
        if not annual_official.empty:
            official_annual_tickers.update(set(annual_official["ticker"].astype(str)))
            annual_frames.append(annual_official)
        if not quarterly_official.empty:
            official_quarterly_tickers.update(set(quarterly_official["ticker"].astype(str)))
            quarterly_frames.append(quarterly_official)

    fallback_annual_df = _load_yfinance_fallback_fundamentals(
        dataset_root=dataset_root,
        tickers=sorted(ticker_set - official_annual_tickers),
        frequency="annual",
    )
    fallback_quarterly_df = _load_yfinance_fallback_fundamentals(
        dataset_root=dataset_root,
        tickers=sorted(ticker_set - official_quarterly_tickers),
        frequency="quarterly",
    )

    annual_final = _deduplicate_buffett3_financials(
        pd.concat([*annual_frames, fallback_annual_df], ignore_index=True)
        if annual_frames or not fallback_annual_df.empty
        else pd.DataFrame(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)
    )
    quarterly_final = _deduplicate_buffett3_financials(
        pd.concat([*quarterly_frames, fallback_quarterly_df], ignore_index=True)
        if quarterly_frames or not fallback_quarterly_df.empty
        else pd.DataFrame(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)
    )
    annual_final.to_csv(dataset_root / "buffett3_annual_fundamentals.csv", index=False, encoding="utf-8")
    quarterly_final.to_csv(
        dataset_root / "buffett3_quarterly_fundamentals.csv", index=False, encoding="utf-8"
    )

    manifest.append(
        _manifest_entry(
            domain="annual_fundamentals_official",
            source_name="single_ticker.current",
            target_path=dataset_root / "buffett3_annual_fundamentals.csv",
            row_count=len(annual_final),
            requested_tickers=[ticker],
            covered_tickers=sorted(set(annual_final["ticker"].astype(str))) if not annual_final.empty else [],
        )
    )
    manifest.append(
        _manifest_entry(
            domain="quarterly_fundamentals_official",
            source_name="single_ticker.current",
            target_path=dataset_root / "buffett3_quarterly_fundamentals.csv",
            row_count=len(quarterly_final),
            requested_tickers=[ticker],
            covered_tickers=sorted(set(quarterly_final["ticker"].astype(str))) if not quarterly_final.empty else [],
        )
    )

    manifest_payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "entries": manifest,
        "financial_tickers": sorted(financial_tickers),
    }
    (dataset_root / "buffett3_source_manifest.json").write_text(
        json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_root": str(dataset_root),
        "ticker": ticker,
        "company_name": company_name,
        "industry": industry,
        "summary": {
            "top100_count": 1,
            "downloaded_price_files": 1 if not price_df.empty else 0,
            "reused_price_files": 0,
            "downloaded_fundamental_profiles": 1,
            "reused_fundamental_profiles": 0,
            "monthly_revenue_rows": len(monthly_revenue_df),
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        },
        "top100_tickers": [ticker],
        "buffett3_official": {
            "valuation_rows": len(valuation_df),
            "dividend_rows": len(dividend_df),
            "monthly_revenue_rows": len(monthly_revenue_df),
            "annual_rows": len(annual_final),
            "quarterly_rows": len(quarterly_final),
            "official_statement_tickers": sorted(official_statement_tickers),
            "manifest_path": str(dataset_root / "buffett3_source_manifest.json"),
        },
    }
    (dataset_root / "dataset_summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def load_top100_dataset(paths: WorkspacePaths) -> dict[str, object]:
    dataset_root = paths.artifacts_root / "datasets" / "top100"
    summary_path = dataset_root / "dataset_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError("Top100 dataset summary not found. Run build-top100 first.")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    top100_universe = pd.read_csv(dataset_root / "top100_universe.csv")
    top100_valuation = pd.read_csv(dataset_root / "top100_valuation_snapshot.csv")
    top100_fundamentals_snapshot = pd.read_csv(dataset_root / "top100_fundamentals_snapshot.csv")
    monthly_revenue = pd.read_csv(dataset_root / "monthly_revenue_history.csv")
    return {
        "summary": summary,
        "dataset_root": dataset_root,
        "top100_universe": top100_universe,
        "top100_valuation": top100_valuation,
        "top100_fundamentals_snapshot": top100_fundamentals_snapshot,
        "monthly_revenue": monthly_revenue,
    }


def fetch_monthly_revenue_history(top100_tickers: list[str], months: int = 15) -> pd.DataFrame:
    official = _fetch_monthly_revenue_official(top100_tickers=top100_tickers, months=months)
    if not official.empty:
        return official

    today = pd.Timestamp.today().normalize()
    month_starts = pd.date_range(end=today, periods=months, freq="MS")
    frames: list[pd.DataFrame] = []
    ticker_set = set(top100_tickers)
    for month_start in month_starts:
        roc_year = month_start.year - 1911
        month = month_start.month
        url = MOPS_MONTHLY_REVENUE_URL_TEMPLATE.format(roc_year=roc_year, month=month)
        try:
            response = requests.get(url, timeout=30, verify=False)
            response.raise_for_status()
            response.encoding = "big5"
            if "THE PAGE CANNOT BE ACCESSED" in response.text:
                continue
            tables = pd.read_html(StringIO(response.text))
        except Exception:
            continue

        parsed = pd.DataFrame(columns=EMPTY_REVENUE_COLUMNS)
        for table in tables:
            parsed = _parse_monthly_revenue_table(table, month_start.year, month)
            if not parsed.empty:
                break
        if parsed.empty:
            continue
        parsed = parsed[parsed["stock_id"].isin(ticker_set)].copy()
        if not parsed.empty:
            frames.append(parsed)

    if not frames:
        return pd.DataFrame(columns=EMPTY_REVENUE_COLUMNS)
    return (
        pd.concat(frames, ignore_index=True)
        .sort_values(["stock_id", "period"])
        .drop_duplicates(["stock_id", "period"], keep="last")
        .reset_index(drop=True)
    )


def download_buffett3_official_data(
    dataset_root: Path, top100_tickers: list[str], universe_df: pd.DataFrame
) -> dict[str, object]:
    ticker_set = {_normalize_ticker(ticker) for ticker in top100_tickers}
    financial_tickers = _detect_financial_tickers(universe_df, ticker_set)
    general_tickers = sorted(ticker_set - financial_tickers)
    manifest: list[dict[str, object]] = []

    valuation_df = _fetch_valuation_snapshot_official(ticker_set)
    valuation_path = dataset_root / "buffett3_valuation_snapshot.csv"
    valuation_df.to_csv(valuation_path, index=False, encoding="utf-8")
    manifest.append(
        _manifest_entry(
            domain="valuation_snapshot_current",
            source_name="twse.BWIBBU_ALL",
            target_path=valuation_path,
            row_count=len(valuation_df),
            requested_tickers=sorted(ticker_set),
            covered_tickers=sorted(set(valuation_df["ticker"])) if not valuation_df.empty else [],
        )
    )

    dividend_df = _fetch_dividend_history_official_v2(ticker_set)
    dividend_path = dataset_root / "buffett3_dividend_history.csv"
    dividend_df.to_csv(dividend_path, index=False, encoding="utf-8")
    manifest.append(
        _manifest_entry(
            domain="dividend_history",
            source_name="twse.t187ap45_L",
            target_path=dividend_path,
            row_count=len(dividend_df),
            requested_tickers=sorted(ticker_set),
            covered_tickers=sorted(set(dividend_df["ticker"])) if not dividend_df.empty else [],
        )
    )

    monthly_revenue_df = _fetch_monthly_revenue_official(top100_tickers)
    monthly_revenue_path = dataset_root / "buffett3_monthly_revenue_history.csv"
    monthly_revenue_df.to_csv(monthly_revenue_path, index=False, encoding="utf-8")
    manifest.append(
        _manifest_entry(
            domain="monthly_revenue_history",
            source_name="twse.t187ap05_L",
            target_path=monthly_revenue_path,
            row_count=len(monthly_revenue_df),
            requested_tickers=sorted(ticker_set),
            covered_tickers=sorted(set(monthly_revenue_df["stock_id"])) if not monthly_revenue_df.empty else [],
        )
    )

    annual_frames: list[pd.DataFrame] = []
    quarterly_frames: list[pd.DataFrame] = []
    official_statement_tickers: set[str] = set()
    official_annual_tickers: set[str] = set()
    official_quarterly_tickers: set[str] = set()
    for label, income_url, balance_url, tickers in [
        (
            "general",
            TWSE_INCOME_GENERAL_URL,
            TWSE_BALANCE_GENERAL_URL,
            general_tickers,
        ),
        (
            "financial",
            TWSE_INCOME_FINANCIAL_URL,
            TWSE_BALANCE_FINANCIAL_URL,
            sorted(financial_tickers),
        ),
    ]:
        if not tickers:
            continue
        official_financial_df = _fetch_official_financial_statements(
            tickers=tickers,
            income_url=income_url,
            balance_url=balance_url,
            source_label=label,
        )
        if not official_financial_df.empty:
            official_statement_tickers.update(set(official_financial_df["ticker"]))
        annual_official = official_financial_df[official_financial_df["fiscal_period"] == "FY"].copy()
        quarterly_official = official_financial_df[
            official_financial_df["fiscal_period"] != "FY"
        ].copy()
        if not annual_official.empty:
            official_annual_tickers.update(set(annual_official["ticker"]))
            annual_frames.append(annual_official)
        if not quarterly_official.empty:
            official_quarterly_tickers.update(set(quarterly_official["ticker"]))
            quarterly_frames.append(quarterly_official)

    fallback_annual_df = _load_yfinance_fallback_fundamentals(
        dataset_root=dataset_root,
        tickers=sorted(ticker_set - official_annual_tickers),
        frequency="annual",
    )
    fallback_quarterly_df = _load_yfinance_fallback_fundamentals(
        dataset_root=dataset_root,
        tickers=sorted(ticker_set - official_quarterly_tickers),
        frequency="quarterly",
    )
    if not fallback_annual_df.empty:
        annual_frames.append(fallback_annual_df)
    if not fallback_quarterly_df.empty:
        quarterly_frames.append(fallback_quarterly_df)

    non_empty_annual_frames = [frame for frame in annual_frames if not frame.empty]
    non_empty_quarterly_frames = [frame for frame in quarterly_frames if not frame.empty]
    annual_df = (
        pd.concat(non_empty_annual_frames, ignore_index=True)
        if non_empty_annual_frames
        else pd.DataFrame(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)
    )
    quarterly_df = (
        pd.concat(non_empty_quarterly_frames, ignore_index=True)
        if non_empty_quarterly_frames
        else pd.DataFrame(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)
    )
    annual_path = dataset_root / "buffett3_annual_fundamentals.csv"
    quarterly_path = dataset_root / "buffett3_quarterly_fundamentals.csv"
    annual_df = _deduplicate_buffett3_financials(annual_df)
    quarterly_df = _deduplicate_buffett3_financials(quarterly_df)
    annual_df.to_csv(annual_path, index=False, encoding="utf-8")
    quarterly_df.to_csv(quarterly_path, index=False, encoding="utf-8")
    manifest.append(
        _manifest_entry(
            domain="annual_fundamentals_official",
            source_name="twse.statements+yfinance.fallback",
            target_path=annual_path,
            row_count=len(annual_df),
            requested_tickers=sorted(ticker_set),
            covered_tickers=sorted(set(annual_df["ticker"])) if not annual_df.empty else [],
        )
    )
    manifest.append(
        _manifest_entry(
            domain="quarterly_fundamentals_official",
            source_name="twse.statements+yfinance.fallback",
            target_path=quarterly_path,
            row_count=len(quarterly_df),
            requested_tickers=sorted(ticker_set),
            covered_tickers=sorted(set(quarterly_df["ticker"])) if not quarterly_df.empty else [],
        )
    )

    manifest_path = dataset_root / "buffett3_source_manifest.json"
    manifest_payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "financial_tickers": sorted(financial_tickers),
        "general_tickers": general_tickers,
        "entries": manifest,
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "valuation_rows": len(valuation_df),
        "dividend_rows": len(dividend_df),
        "monthly_revenue_rows": len(monthly_revenue_df),
        "annual_rows": len(annual_df),
        "quarterly_rows": len(quarterly_df),
        "official_statement_tickers": sorted(official_statement_tickers),
        "manifest_path": str(manifest_path),
    }


def read_price_history(dataset_root: Path, ticker: str) -> pd.DataFrame:
    path = dataset_root / "prices" / f"{ticker}.csv"
    return pd.read_csv(path)


def read_annual_financials(dataset_root: Path, ticker: str) -> pd.DataFrame:
    path = dataset_root / "fundamentals" / f"{ticker}_annual.csv"
    return pd.read_csv(path)


def read_quarterly_financials(dataset_root: Path, ticker: str) -> pd.DataFrame:
    path = dataset_root / "fundamentals" / f"{ticker}_quarterly.csv"
    return pd.read_csv(path)


def read_profile(dataset_root: Path, ticker: str) -> dict[str, object]:
    path = dataset_root / "fundamentals" / f"{ticker}_profile.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _download_price_history(ticker: str) -> pd.DataFrame:
    raw = yf.download(
        f"{ticker}.TW",
        start="2015-01-01",
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    if raw.empty:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    raw = raw.reset_index()
    keep = [
        column
        for column in ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        if column in raw.columns
    ]
    return raw[keep]


def _download_taiex_history() -> pd.DataFrame:
    raw = yf.download(
        "^TWII",
        start="2015-01-01",
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.reset_index()
    keep = [
        column
        for column in ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        if column in raw.columns
    ]
    return raw[keep]


def _download_financial_profile(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    ticker_obj = yf.Ticker(f"{ticker}.TW")
    info = ticker_obj.info or {}
    annual = _frame_from_yf_statement(
        ticker_obj.financials, ticker_obj.cashflow, ticker_obj.balance_sheet
    )
    quarterly = _frame_from_yf_statement(
        ticker_obj.quarterly_financials,
        ticker_obj.quarterly_cashflow,
        ticker_obj.quarterly_balance_sheet,
    )

    current_price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
        or info.get("lastClose")
    )
    profile = {
        "ticker": ticker,
        "longName": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector") or "",
        "industry": info.get("industry") or "",
        "sharesOutstanding": info.get("sharesOutstanding"),
        "marketCap": info.get("marketCap"),
        "priceToBook": info.get("priceToBook"),
        "dividendYield": info.get("dividendYield"),
        "trailingPE": info.get("trailingPE"),
        "trailingEps": info.get("trailingEps"),
        "currentPrice": current_price,
        "regularMarketPrice": info.get("regularMarketPrice"),
        "previousClose": info.get("previousClose"),
        "currentRatio": info.get("currentRatio"),
        "debtToEquity": info.get("debtToEquity"),
        "currency": info.get("currency") or "TWD",
        "source": "yfinance",
    }
    return annual, quarterly, profile


def _frame_from_yf_statement(
    income_frame: pd.DataFrame, cashflow_frame: pd.DataFrame, balance_frame: pd.DataFrame
) -> pd.DataFrame:
    if income_frame is None or income_frame.empty:
        return pd.DataFrame(columns=EMPTY_FINANCIAL_COLUMNS)

    income = income_frame.T.copy()
    cashflow = (
        cashflow_frame.T.copy()
        if cashflow_frame is not None and not cashflow_frame.empty
        else pd.DataFrame(index=income.index)
    )
    balance = (
        balance_frame.T.copy()
        if balance_frame is not None and not balance_frame.empty
        else pd.DataFrame(index=income.index)
    )

    def series(frame: pd.DataFrame, *keys: str) -> pd.Series:
        for key in keys:
            if key in frame.columns:
                return pd.to_numeric(frame[key], errors="coerce")
        return pd.Series(index=frame.index, dtype="float64")

    df = pd.DataFrame(index=income.index)
    df.index.name = "date"
    df["revenue"] = series(income, "Total Revenue")
    df["net_income"] = series(income, "Net Income")
    df["operating_income"] = series(income, "Operating Income")
    df["operating_cash_flow"] = series(cashflow, "Operating Cash Flow")
    df["capital_expenditure"] = series(cashflow, "Capital Expenditure")
    df["free_cash_flow"] = df["operating_cash_flow"] - df["capital_expenditure"].abs()
    df["equity"] = series(balance, "Stockholders Equity", "Common Stock Equity")
    df["total_assets"] = series(balance, "Total Assets")
    df["total_liabilities"] = series(balance, "Total Liab", "Total Liabilities Net Minority Interest")
    df["current_assets"] = series(balance, "Current Assets")
    df["current_liabilities"] = series(balance, "Current Liabilities")
    df["shares_outstanding"] = series(balance, "Ordinary Shares Number", "Share Issued")
    df["eps"] = df["net_income"] / df["shares_outstanding"].replace({0: pd.NA})
    df["book_value_per_share"] = df["equity"] / df["shares_outstanding"].replace({0: pd.NA})
    df["roe"] = (df["net_income"] / df["equity"].replace({0: pd.NA})) * 100.0
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return df


def _parse_monthly_revenue_table(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=EMPTY_REVENUE_COLUMNS)

    if isinstance(df.columns, pd.MultiIndex):
        columns = [" ".join(str(part).strip() for part in column if str(part) != "nan") for column in df.columns]
        working = df.copy()
        working.columns = columns
    else:
        working = df.copy()
        working.columns = [str(column).strip() for column in working.columns]

    working = working.dropna(how="all")
    if working.empty:
        return pd.DataFrame(columns=EMPTY_REVENUE_COLUMNS)

    stock_id_col = _find_column(working.columns, [r"stock[_ ]?id", r"公司代號", r"代號", r"證券代號"])
    stock_name_col = _find_column(working.columns, [r"stock[_ ]?name", r"公司名稱", r"名稱"])
    revenue_col = _find_column(working.columns, [r"當月營收", r"本月營收", r"monthly_revenue", r"營業收入"])
    yoy_col = _find_column(working.columns, [r"去年同月增減", r"增減.*%", r"yoy"])

    if stock_id_col is None:
        first_four_digit = [
            column
            for column in working.columns
            if working[column].astype(str).str.fullmatch(r"\d{4}", na=False).sum() >= 5
        ]
        stock_id_col = first_four_digit[0] if first_four_digit else None
    if revenue_col is None:
        numeric_candidates = [
            column
            for column in working.columns
            if pd.to_numeric(
                working[column].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ).notna().sum()
            >= 5
        ]
        revenue_col = numeric_candidates[1] if len(numeric_candidates) >= 2 else (
            numeric_candidates[0] if numeric_candidates else None
        )
    if stock_id_col is None or revenue_col is None:
        return pd.DataFrame(columns=EMPTY_REVENUE_COLUMNS)

    stock_id = working[stock_id_col].astype(str).str.extract(r"(\d{4})", expand=False)
    revenue_series = pd.to_numeric(
        working[revenue_col].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
    yoy_series = (
        pd.to_numeric(
            working[yoy_col].astype(str).str.replace("%", "", regex=False),
            errors="coerce",
        )
        if yoy_col is not None
        else pd.Series(index=working.index, dtype="float64")
    )
    stock_name = (
        working[stock_name_col].astype(str).str.strip()
        if stock_name_col is not None
        else pd.Series([""] * len(working), index=working.index)
    )

    parsed = pd.DataFrame(
        {
            "stock_id": stock_id,
            "stock_name": stock_name,
            "monthly_revenue": revenue_series,
            "revenue_yoy": yoy_series,
            "year": year,
            "month": month,
        }
    )
    parsed = parsed[parsed["stock_id"].str.fullmatch(r"\d{4}", na=False)]
    parsed = parsed.dropna(subset=["monthly_revenue"])
    parsed["period"] = pd.to_datetime(
        parsed["year"].astype(str) + "-" + parsed["month"].astype(str).str.zfill(2) + "-01",
        errors="coerce",
    )
    return parsed.dropna(subset=["period"]).reset_index(drop=True)


def _find_column(columns: pd.Index, patterns: list[str]) -> str | None:
    for column in columns:
        text = str(column).strip().lower()
        normalized = re.sub(r"\s+", "", text)
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE) or re.search(
                pattern, normalized, flags=re.IGNORECASE
            ):
                return column
    return None


def _normalize_ticker(value: object) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(4) if text.isdigit() else text


def _fetch_twse_openapi_json(url: str) -> list[dict[str, object]]:
    response = requests.get(url, timeout=30, verify=False)
    response.raise_for_status()
    raw_bytes = response.content or b""
    candidate_encodings: list[str] = []
    for encoding in ("utf-8-sig", "utf-8", response.encoding, getattr(response, "apparent_encoding", None)):
        if encoding and encoding not in candidate_encodings:
            candidate_encodings.append(encoding)

    for encoding in candidate_encodings:
        try:
            payload = json.loads(raw_bytes.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]

    payload = response.json()
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _fetch_monthly_revenue_official(top100_tickers: list[str], months: int = 15) -> pd.DataFrame:
    try:
        rows = _fetch_twse_openapi_json(TWSE_MONTHLY_REVENUE_URL)
    except Exception:
        return pd.DataFrame(columns=EMPTY_REVENUE_COLUMNS)

    ticker_set = {_normalize_ticker(ticker) for ticker in top100_tickers}
    records: list[dict[str, object]] = []
    for row in rows:
        ticker = _extract_ticker_from_row(row)
        if ticker not in ticker_set:
            continue
        year = _safe_int(
            _first_value(
                row,
                ["出表日期", "資料年月", "年月", "年", "年度", "資料年度"],
            )[:3]
            if isinstance(_first_value(row, ["出表日期", "資料年月", "年月"], default=""), str)
            and len(_first_value(row, ["出表日期", "資料年月", "年月"], default="")) >= 3
            else None
        )
        month_value = _first_value(row, ["資料年月", "年月", "月", "資料月份"])
        month = _extract_month(month_value)
        revenue = _safe_float(
            _first_value(row, ["營業收入-當月營收", "當月營收", "營業收入", "單月營收"])
        )
        yoy = _safe_float(
            _first_value(
                row,
                ["營業收入-去年同月增減(%)", "去年同月增減(%)", "增減(%)", "月增減(%)"],
            )
        )
        if not year or not month or revenue is None:
            continue
        period = pd.Timestamp(year=year + 1911 if year < 1911 else year, month=month, day=1)
        records.append(
            {
                "stock_id": ticker,
                "stock_name": _first_value(row, ["公司名稱", "公司名", "名稱"], default=""),
                "monthly_revenue": revenue,
                "revenue_yoy": yoy,
                "year": period.year,
                "month": period.month,
                "period": period.strftime("%Y-%m-%d"),
            }
        )
    if not records:
        return pd.DataFrame(columns=EMPTY_REVENUE_COLUMNS)
    df = pd.DataFrame(records)
    cutoff = (
        pd.Timestamp.today().normalize().replace(day=1) - pd.DateOffset(months=max(months - 1, 0))
    ).strftime("%Y-%m-%d")
    return (
        df[df["period"] >= cutoff]
        .sort_values(["stock_id", "period"])
        .drop_duplicates(["stock_id", "period"], keep="last")
        .reset_index(drop=True)
    )


def _fetch_valuation_snapshot_official(tickers: set[str]) -> pd.DataFrame:
    try:
        rows = _fetch_twse_openapi_json(TWSE_BWIBBU_ALL_URL)
    except Exception:
        return pd.DataFrame(columns=BUFFETT3_VALUATION_COLUMNS)
    records: list[dict[str, object]] = []
    for row in rows:
        ticker = _extract_ticker_from_row(row)
        if ticker not in tickers:
            continue
        records.append(
            {
                "ticker": ticker,
                "date": _convert_roc_date(_first_value(row, ["Date", "資料日期", "日期"], default="")),
                "pe_ratio": _safe_float(_first_value(row, ["PEratio", "本益比", "PE Ratio"])),
                "pb_ratio": _safe_float(_first_value(row, ["PBratio", "股價淨值比", "PB Ratio"])),
                "dividend_yield": _safe_float(
                    _first_value(row, ["DividendYield", "殖利率(%)", "殖利率", "Dividend Yield"])
                ),
                "source_name": "twse.BWIBBU_ALL",
            }
        )
    return pd.DataFrame(records, columns=BUFFETT3_VALUATION_COLUMNS).sort_values("ticker")


def _fetch_dividend_history_official(tickers: set[str]) -> pd.DataFrame:
    try:
        rows = _fetch_twse_openapi_json(TWSE_DIVIDEND_URL)
    except Exception:
        return pd.DataFrame(columns=BUFFETT3_DIVIDEND_COLUMNS)
    records: list[dict[str, object]] = []
    for row in rows:
        ticker = _extract_ticker_from_row(row)
        if ticker not in tickers:
            continue
        cash_dividend = _safe_float(
            _first_value(
                row,
                [
                    "股東配發-盈餘分配之現金股利(元/股)",
                    "股東配發-法定盈餘公積發放之現金(元/股)",
                    "股東配發-資本公積發放之現金(元/股)",
                    "盈餘分配之現金股利(元/股)",
                    "現金股利(元/股)",
                    "現金股利",
                    "Cash Dividend",
                ],
            )
        )
        stock_dividend = _safe_float(
            _first_value(
                row,
                ["股票股利", "盈餘轉增資配股(元/股)", "股票股利(元/股)", "Stock Dividend"],
            )
        )
        reserve_cash_dividend = _safe_float(
            _first_value(row, ["股東配發-法定盈餘公積發放之現金(元/股)"], default="")
        )
        capital_cash_dividend = _safe_float(
            _first_value(row, ["股東配發-資本公積發放之現金(元/股)"], default="")
        )
        fiscal_year = _safe_int(_first_value(row, ["股利年度", "股利所屬年度", "年度"], default=""))
        records.append(
            {
                "ticker": ticker,
                "fiscal_year": fiscal_year,
                "cash_dividend": (cash_dividend or 0.0)
                + (reserve_cash_dividend or 0.0)
                + (capital_cash_dividend or 0.0),
                "stock_dividend": stock_dividend,
                "total_dividend": (cash_dividend or 0.0)
                + (reserve_cash_dividend or 0.0)
                + (capital_cash_dividend or 0.0)
                + (stock_dividend or 0.0),
                "announcement_date": _convert_roc_date(
                    _first_value(
                        row,
                        ["董事會（擬議）股利分派日", "董事會決議(擬議)日期", "除權除息交易日", "公告日期"],
                        default="",
                    )
                ),
                "source_name": "twse.t187ap45_L",
            }
        )
    df = pd.DataFrame(records, columns=BUFFETT3_DIVIDEND_COLUMNS)
    if df.empty:
        return df
    return (
        df.sort_values(["ticker", "fiscal_year", "announcement_date"], na_position="last")
        .drop_duplicates(["ticker", "fiscal_year"], keep="last")
        .reset_index(drop=True)
    )


def _fetch_dividend_history_official_v2(tickers: set[str]) -> pd.DataFrame:
    try:
        rows = _fetch_twse_openapi_json(TWSE_DIVIDEND_URL)
    except Exception:
        return pd.DataFrame(columns=BUFFETT3_DIVIDEND_COLUMNS)

    cash_keys = [
        "股東配發-盈餘分配之現金股利(元/股)",
        "股東配發-法定盈餘公積發放之現金(元/股)",
        "股東配發-資本公積發放之現金(元/股)",
        "現金股利(元/股)",
        "現金股利",
        "Cash Dividend",
    ]
    stock_keys = [
        "股票股利",
        "股票股利(元/股)",
        "股東配發-盈餘轉增資配股(元/股)",
        "股東配發-法定盈餘公積轉增資配股(元/股)",
        "股東配發-資本公積轉增資配股(元/股)",
        "盈餘轉增資配股(元/股)",
        "法定盈餘公積轉增資配股(元/股)",
        "資本公積轉增資配股(元/股)",
        "Stock Dividend",
    ]
    reserve_cash_keys = ["股東配發-法定盈餘公積發放之現金(元/股)"]
    capital_cash_keys = ["股東配發-資本公積發放之現金(元/股)"]
    fiscal_year_keys = ["股利年度", "股利所屬年度", "年度"]
    announcement_keys = ["董事會（擬議）股利分派日", "董事會決議(擬議)日期", "除權除息交易日", "公告日期"]

    records: list[dict[str, object]] = []
    for row in rows:
        ticker = _extract_ticker_from_row(row)
        if ticker not in tickers:
            continue

        cash_dividend = _safe_float(_first_value(row, cash_keys))
        stock_dividend = _safe_float(_first_value(row, stock_keys))
        reserve_cash_dividend = _safe_float(_first_value(row, reserve_cash_keys, default=""))
        capital_cash_dividend = _safe_float(_first_value(row, capital_cash_keys, default=""))
        fiscal_year = _safe_int(_first_value(row, fiscal_year_keys, default=""))
        records.append(
            {
                "ticker": ticker,
                "fiscal_year": fiscal_year,
                "cash_dividend": (cash_dividend or 0.0)
                + (reserve_cash_dividend or 0.0)
                + (capital_cash_dividend or 0.0),
                "stock_dividend": stock_dividend or 0.0,
                "total_dividend": (cash_dividend or 0.0)
                + (reserve_cash_dividend or 0.0)
                + (capital_cash_dividend or 0.0)
                + (stock_dividend or 0.0),
                "announcement_date": _convert_roc_date(_first_value(row, announcement_keys, default="")),
                "source_name": "twse.t187ap45_L",
            }
        )

    df = pd.DataFrame(records, columns=BUFFETT3_DIVIDEND_COLUMNS)
    if df.empty:
        return df
    return (
        df.sort_values(["ticker", "fiscal_year", "announcement_date"], na_position="last")
        .drop_duplicates(["ticker", "fiscal_year"], keep="last")
        .reset_index(drop=True)
    )


def _fetch_official_financial_statements(
    tickers: list[str], income_url: str, balance_url: str, source_label: str
) -> pd.DataFrame:
    try:
        income_rows = _fetch_twse_openapi_json(income_url)
        balance_rows = _fetch_twse_openapi_json(balance_url)
    except Exception:
        return pd.DataFrame(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)

    income_df = _normalize_official_statement_rows(income_rows, tickers, source_label, "income")
    balance_df = _normalize_official_statement_rows(balance_rows, tickers, source_label, "balance")
    if income_df.empty and balance_df.empty:
        return pd.DataFrame(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)
    if income_df.empty:
        return balance_df.reindex(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)
    if balance_df.empty:
        return income_df.reindex(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)

    merged = income_df.merge(
        balance_df,
        on=["ticker", "report_date", "fiscal_year", "fiscal_period"],
        how="outer",
        suffixes=("_income", "_balance"),
    )
    result = pd.DataFrame(
        {
            "ticker": merged["ticker"],
            "report_date": merged["report_date"],
            "fiscal_year": merged["fiscal_year"],
            "fiscal_period": merged["fiscal_period"],
            "revenue": _coalesce_merged_series(merged, "revenue"),
            "net_income": _coalesce_merged_series(merged, "net_income"),
            "operating_income": _coalesce_merged_series(merged, "operating_income"),
            "operating_cash_flow": _coalesce_merged_series(merged, "operating_cash_flow"),
            "capital_expenditure": _coalesce_merged_series(merged, "capital_expenditure"),
            "free_cash_flow": _coalesce_merged_series(merged, "free_cash_flow"),
            "equity": _coalesce_merged_series(merged, "equity"),
            "total_assets": _coalesce_merged_series(merged, "total_assets"),
            "total_liabilities": _coalesce_merged_series(merged, "total_liabilities"),
            "current_assets": _coalesce_merged_series(merged, "current_assets"),
            "current_liabilities": _coalesce_merged_series(merged, "current_liabilities"),
            "shares_outstanding": _coalesce_merged_series(merged, "shares_outstanding"),
            "eps": _coalesce_merged_series(merged, "eps"),
            "book_value_per_share": _coalesce_merged_series(merged, "book_value_per_share"),
            "roe": _coalesce_merged_series(merged, "roe"),
            "cash_and_equivalents": _coalesce_merged_series(merged, "cash_and_equivalents"),
            "total_debt": _coalesce_merged_series(merged, "total_debt"),
            "source_name": merged.get("source_name_income").fillna(merged.get("source_name_balance")),
        }
    )
    return result.reindex(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS).sort_values(
        ["ticker", "report_date", "fiscal_period"]
    )


def _normalize_official_statement_rows(
    rows: list[dict[str, object]], tickers: list[str], source_label: str, statement_kind: str
) -> pd.DataFrame:
    ticker_set = set(tickers)
    records: list[dict[str, object]] = []
    for row in rows:
        ticker = _extract_ticker_from_row(row)
        if ticker not in ticker_set:
            continue
        report_date = _convert_roc_date(
            _first_value(row, ["出表日期", "資料年月", "年度", "資料日期"], default="")
        )
        fiscal_year = _extract_fiscal_year(row)
        fiscal_period = _extract_fiscal_period(row, report_date)
        base = {
            "ticker": ticker,
            "report_date": report_date,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
            "source_name": f"twse.{source_label}.{statement_kind}",
        }
        if statement_kind == "income":
            revenue = _safe_float(_first_value(row, ["營業收入", "收入", "收益", "利息淨收益"], default=""))
            net_income = _safe_float(_first_value(row, ["本期淨利（淨損）", "本期稅後淨利（淨損）", "本期淨利", "稅後淨利"], default=""))
            operating_income = _safe_float(_first_value(row, ["營業利益（損失）", "營業利益", "營業損益"], default=""))
            eps = _safe_float(_first_value(row, ["基本每股盈餘（元）", "每股盈餘", "基本每股盈餘"], default=""))
            roe = _safe_float(_first_value(row, ["權益報酬率(%)", "ROE(%)", "ROE"], default=""))
            records.append(
                base
                | {
                    "revenue": revenue,
                    "net_income": net_income,
                    "operating_income": operating_income,
                    "operating_cash_flow": None,
                    "capital_expenditure": None,
                    "free_cash_flow": None,
                    "equity": None,
                    "total_assets": None,
                    "total_liabilities": None,
                    "current_assets": None,
                    "current_liabilities": None,
                    "shares_outstanding": None,
                    "eps": eps,
                    "book_value_per_share": None,
                    "roe": roe,
                    "cash_and_equivalents": None,
                    "total_debt": None,
                }
            )
        else:
            equity = _safe_float(_first_value(row, ["權益總額", "權益總計", "股東權益總額", "歸屬於母公司業主之權益合計"], default=""))
            total_assets = _safe_float(_first_value(row, ["資產總額", "資產總計"], default=""))
            total_liabilities = _safe_float(_first_value(row, ["負債總額", "負債總計"], default=""))
            current_assets = _safe_float(_first_value(row, ["流動資產", "流動資產總額"], default=""))
            current_liabilities = _safe_float(_first_value(row, ["流動負債", "流動負債總額"], default=""))
            shares_outstanding = _safe_float(_first_value(row, ["普通股股本", "股本", "普通股股數"], default=""))
            bvps = _safe_float(_first_value(row, ["每股參考淨值", "每股淨值", "BVPS"], default=""))
            cash = _safe_float(_first_value(row, ["現金及約當現金", "現金及約當現金總額"], default=""))
            total_debt = _safe_float(_first_value(row, ["長期借款", "短期借款", "應付公司債"], default=""))
            records.append(
                base
                | {
                    "revenue": None,
                    "net_income": None,
                    "operating_income": None,
                    "operating_cash_flow": None,
                    "capital_expenditure": None,
                    "free_cash_flow": None,
                    "equity": equity,
                    "total_assets": total_assets,
                    "total_liabilities": total_liabilities,
                    "current_assets": current_assets,
                    "current_liabilities": current_liabilities,
                    "shares_outstanding": shares_outstanding,
                    "eps": None,
                    "book_value_per_share": bvps,
                    "roe": None,
                    "cash_and_equivalents": cash,
                    "total_debt": total_debt,
                }
            )
    return pd.DataFrame(records)


def _detect_financial_tickers(universe_df: pd.DataFrame, tickers: set[str]) -> set[str]:
    if universe_df.empty:
        return set()
    working = universe_df.copy()
    working["ticker"] = working["ticker"].map(_normalize_ticker)
    industry_mask = working["industry"].fillna("").astype(str).str.contains("金融|保險|銀行", regex=True)
    ticker_prefix_mask = working["ticker"].fillna("").astype(str).str.fullmatch(r"28\d{2}")
    financial_mask = industry_mask | ticker_prefix_mask
    return set(working.loc[financial_mask & working["ticker"].isin(tickers), "ticker"])


def _manifest_entry(
    domain: str,
    source_name: str,
    target_path: Path,
    row_count: int,
    requested_tickers: list[str] | None = None,
    covered_tickers: list[str] | None = None,
) -> dict[str, object]:
    requested = requested_tickers or []
    covered = covered_tickers or []
    return {
        "domain": domain,
        "source_name": source_name,
        "target_path": str(target_path),
        "row_count": row_count,
        "requested_tickers": requested,
        "covered_tickers": covered,
        "missing_tickers": [ticker for ticker in requested if ticker not in set(covered)],
    }


def _extract_ticker_from_row(row: dict[str, object]) -> str:
    for key in ["公司代號", "證券代號", "Code", "code", "stock_id", "ticker"]:
        if key in row and row[key] is not None:
            value_text = str(row[key]).strip()
            if re.fullmatch(r"\d{4}", value_text):
                return value_text
    for key, value in row.items():
        key_text = str(key).strip()
        value_text = str(value).strip()
        if key_text.endswith("代號") and re.fullmatch(r"\d{4}", value_text):
            return value_text
    return ""


def _first_value(row: dict[str, object], keys: list[str], default: object = "") -> str:
    for key in keys:
        if key in row and row[key] is not None:
            return str(row[key]).strip()
    for actual_key, value in row.items():
        actual = str(actual_key)
        if any(key.lower() in actual.lower() for key in keys):
            return str(value).strip()
    return str(default).strip() if default is not None else ""


def _convert_roc_date(value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""
    digits = re.findall(r"\d+", text)
    if len(digits) == 1 and len(digits[0]) == 7:
        roc = digits[0]
        return f"{int(roc[:3]) + 1911:04d}-{roc[3:5]}-{roc[5:7]}"
    if len(digits) >= 3:
        year = int(digits[0])
        if year < 1911:
            year += 1911
        month = int(digits[1])
        day = int(digits[2])
        return f"{year:04d}-{month:02d}-{day:02d}"
    return text


def _extract_month(value: object) -> int | None:
    text = str(value).strip()
    digits = re.findall(r"\d+", text)
    if not digits:
        return None
    if len(digits) == 1 and len(digits[0]) >= 5:
        return int(digits[0][-2:])
    return int(digits[-1])


def _extract_fiscal_year(row: dict[str, object]) -> int | None:
    for key in ["年度", "年", "資料年度", "出表日期", "資料年月"]:
        value = _first_value(row, [key], default="")
        digits = re.findall(r"\d+", value)
        if not digits:
            continue
        year = int(digits[0][:4] if len(digits[0]) >= 4 else digits[0])
        if year < 1911:
            year += 1911
        return year
    return None


def _extract_fiscal_period(row: dict[str, object], report_date: str) -> str:
    quarter_text = _first_value(row, ["季別", "季度", "季"], default="")
    quarter_digits = re.findall(r"\d+", quarter_text)
    if quarter_digits:
        return f"Q{int(quarter_digits[0])}"
    if report_date:
        month = pd.to_datetime(report_date, errors="coerce").month
        if month in {3, 4, 5}:
            return "Q1"
        if month in {6, 7, 8}:
            return "Q2"
        if month in {9, 10, 11}:
            return "Q3"
        if month == 12 or month == 1:
            return "FY"
    return ""


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"--", "-", "nan", "None"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    match = re.search(r"\d+", text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def _coalesce_merged_series(frame: pd.DataFrame, base_name: str) -> pd.Series:
    direct = frame.get(base_name)
    left = frame.get(f"{base_name}_income")
    right = frame.get(f"{base_name}_balance")
    if direct is not None:
        return direct
    if left is not None and right is not None:
        return left.where(left.notna(), right)
    if left is not None:
        return left
    if right is not None:
        return right
    return pd.Series(index=frame.index, dtype="float64")


def _load_yfinance_fallback_fundamentals(
    dataset_root: Path, tickers: list[str], frequency: str
) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)
    fundamentals_root = dataset_root / "fundamentals"
    suffix = "annual" if frequency == "annual" else "quarterly"
    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        path = fundamentals_root / f"{ticker}_{suffix}.csv"
        if not path.exists():
            continue
        raw_df = pd.read_csv(path)
        if raw_df.empty:
            continue
        frames.append(_normalize_yfinance_fallback_fundamental_frame(raw_df, ticker, frequency))
    if not frames:
        return pd.DataFrame(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def _normalize_yfinance_fallback_fundamental_frame(
    raw_df: pd.DataFrame, ticker: str, frequency: str
) -> pd.DataFrame:
    working = raw_df.copy()
    if "date" not in working.columns:
        working["date"] = ""
    report_dates = pd.to_datetime(working["date"], errors="coerce")
    result = pd.DataFrame(
        {
            "ticker": ticker,
            "report_date": report_dates.dt.strftime("%Y-%m-%d"),
            "fiscal_year": report_dates.dt.year,
            "fiscal_period": report_dates.dt.month.map(_month_to_fiscal_period),
            "revenue": pd.to_numeric(working.get("revenue"), errors="coerce"),
            "net_income": pd.to_numeric(working.get("net_income"), errors="coerce"),
            "operating_income": pd.to_numeric(working.get("operating_income"), errors="coerce"),
            "operating_cash_flow": pd.to_numeric(working.get("operating_cash_flow"), errors="coerce"),
            "capital_expenditure": pd.to_numeric(working.get("capital_expenditure"), errors="coerce"),
            "free_cash_flow": pd.to_numeric(working.get("free_cash_flow"), errors="coerce"),
            "equity": pd.to_numeric(working.get("equity"), errors="coerce"),
            "total_assets": pd.to_numeric(working.get("total_assets"), errors="coerce"),
            "total_liabilities": pd.to_numeric(working.get("total_liabilities"), errors="coerce"),
            "current_assets": pd.to_numeric(working.get("current_assets"), errors="coerce"),
            "current_liabilities": pd.to_numeric(working.get("current_liabilities"), errors="coerce"),
            "shares_outstanding": pd.to_numeric(working.get("shares_outstanding"), errors="coerce"),
            "eps": pd.to_numeric(working.get("eps"), errors="coerce"),
            "book_value_per_share": pd.to_numeric(working.get("book_value_per_share"), errors="coerce"),
            "roe": pd.to_numeric(working.get("roe"), errors="coerce"),
            "cash_and_equivalents": pd.Series(index=working.index, dtype="float64"),
            "total_debt": pd.Series(index=working.index, dtype="float64"),
            "source_name": f"yfinance.fallback.{frequency}",
        }
    )
    if frequency == "annual":
        result["fiscal_period"] = "FY"
    return result.reindex(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)


def _month_to_fiscal_period(month: float | int | None) -> str:
    if pd.isna(month):
        return ""
    month_int = int(month)
    if month_int in {1, 2, 3}:
        return "Q1"
    if month_int in {4, 5, 6}:
        return "Q2"
    if month_int in {7, 8, 9}:
        return "Q3"
    if month_int in {10, 11, 12}:
        return "FY"
    return ""


def _deduplicate_buffett3_financials(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.reindex(columns=BUFFETT3_OFFICIAL_FINANCIAL_COLUMNS)
    working = df.copy()
    working["_source_rank"] = working["source_name"].astype(str).str.startswith("twse.").map(
        {True: 0, False: 1}
    )
    working = working.sort_values(
        ["ticker", "report_date", "fiscal_period", "_source_rank", "source_name"]
    )
    working = working.drop_duplicates(["ticker", "report_date", "fiscal_period"], keep="first")
    return working.drop(columns="_source_rank").reset_index(drop=True)
