from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import WorkspacePaths
from .csv_utils import iter_csv_rows, read_csv_rows, write_csv_rows


@dataclass
class TableSummary:
    name: str
    source_path: str
    output_path: str
    row_count: int
    grain: str
    status: str
    notes: list[str]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def discover_shared_data(paths: WorkspacePaths) -> dict[str, object]:
    fundamentals_root = paths.shared_data_root / "fundamentals"
    raw_root = paths.shared_data_root / "raw"
    raw_files = sorted(raw_root.glob("*.csv"))
    return {
        "shared_data_root": str(paths.shared_data_root),
        "discovered_at": _utc_now_iso(),
        "folders": {
            "fundamentals": str(fundamentals_root),
            "raw": str(raw_root),
        },
        "files": {
            "company_info": str(fundamentals_root / "company_info.csv"),
            "valuation": str(fundamentals_root / "valuation.csv"),
            "yfinance_fundamentals": str(fundamentals_root / "yfinance_fundamentals.csv"),
            "raw_csv_count": len(raw_files),
            "sample_raw_files": [item.name for item in raw_files[:5]],
        },
    }


def normalize_shared_data(paths: WorkspacePaths) -> dict[str, object]:
    paths.normalized_root.mkdir(parents=True, exist_ok=True)
    generated_at = _utc_now_iso()
    summaries = [
        _normalize_universe(paths, generated_at),
        _normalize_valuation_snapshot(paths, generated_at),
        _normalize_fundamentals_snapshot(paths, generated_at),
        _normalize_price_daily(paths, generated_at),
        _normalize_benchmark_daily(paths, generated_at),
    ]
    summary = {
        "generated_at": generated_at,
        "shared_data_root": str(paths.shared_data_root),
        "normalized_root": str(paths.normalized_root),
        "tables": [asdict(item) for item in summaries],
    }
    summary_path = paths.normalized_root / "normalization_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def validate_shared_data(paths: WorkspacePaths) -> dict[str, object]:
    normalized_summary_path = paths.normalized_root / "normalization_summary.json"
    results: dict[str, object] = {
        "validated_at": _utc_now_iso(),
        "normalized_root": str(paths.normalized_root),
        "checks": [],
    }
    if not normalized_summary_path.exists():
        raise FileNotFoundError(
            "Normalized data summary not found. Run normalize before validate."
        )

    checks = []

    universe_rows = read_csv_rows(paths.normalized_root / "universe_snapshot.csv")
    checks.append(
        {
            "table": "universe_snapshot",
            "row_count": len(universe_rows),
            "listing_date_missing": sum(
                1 for row in universe_rows if not row["listing_date"].strip()
            ),
            "status": "warning",
            "notes": ["listing_date is incomplete in the current shared dataset"],
        }
    )

    valuation_rows = read_csv_rows(paths.normalized_root / "valuation_snapshot.csv")
    checks.append(
        {
            "table": "valuation_snapshot",
            "row_count": len(valuation_rows),
            "has_source_date_column": "date" in valuation_rows[0] if valuation_rows else False,
            "zero_pe_count": sum(1 for row in valuation_rows if row["pe_ratio"] == "0.0"),
            "status": "warning",
            "notes": ["valuation source is currently a snapshot table with no historical date column"],
        }
    )

    fundamentals_rows = read_csv_rows(
        paths.normalized_root / "fundamentals_snapshot.csv"
    )
    checks.append(
        {
            "table": "fundamentals_snapshot",
            "row_count": len(fundamentals_rows),
            "has_report_date": "report_date" in fundamentals_rows[0]
            if fundamentals_rows
            else False,
            "status": "warning",
            "notes": ["fundamentals source is currently a snapshot table with no fiscal period metadata"],
        }
    )

    price_rows = read_csv_rows(paths.normalized_root / "price_daily.csv")
    tickers = {row["ticker"] for row in price_rows}
    checks.append(
        {
            "table": "price_daily",
            "row_count": len(price_rows),
            "ticker_count": len(tickers),
            "missing_adjusted_close": sum(
                1 for row in price_rows if not row["adjusted_close"].strip()
            ),
            "status": "ok",
            "notes": ["price time series is the strongest current data domain"],
        }
    )

    benchmark_rows = read_csv_rows(paths.normalized_root / "benchmark_daily.csv")
    checks.append(
        {
            "table": "benchmark_daily",
            "row_count": len(benchmark_rows),
            "status": "ok",
            "notes": ["TAIEX benchmark history is present and normalized"],
        }
    )

    results["checks"] = checks
    paths.validation_root.mkdir(parents=True, exist_ok=True)
    output_path = paths.validation_root / "validation_summary.json"
    output_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return results


def _normalize_universe(paths: WorkspacePaths, generated_at: str) -> TableSummary:
    source_path = paths.shared_data_root / "fundamentals" / "company_info.csv"
    output_path = paths.normalized_root / "universe_snapshot.csv"
    fieldnames = [
        "ticker",
        "company_name",
        "industry",
        "listing_date",
        "market",
        "source_name",
        "source_file",
        "data_as_of",
        "table_grain",
    ]

    def rows():
        for row in iter_csv_rows(source_path):
            yield {
                "ticker": row.get("stock_id", "").strip(),
                "company_name": row.get("name", "").strip(),
                "industry": row.get("industry", "").strip(),
                "listing_date": row.get("listing_date", "").strip(),
                "market": row.get("market", "").strip(),
                "source_name": "shared_data.company_info",
                "source_file": str(source_path),
                "data_as_of": generated_at,
                "table_grain": "snapshot",
            }

    row_count = write_csv_rows(output_path, fieldnames, rows())
    return TableSummary(
        name="universe_snapshot",
        source_path=str(source_path),
        output_path=str(output_path),
        row_count=row_count,
        grain="snapshot",
        status="ok",
        notes=["Derived from company_info.csv"],
    )


def _normalize_valuation_snapshot(paths: WorkspacePaths, generated_at: str) -> TableSummary:
    source_path = paths.shared_data_root / "fundamentals" / "valuation.csv"
    output_path = paths.normalized_root / "valuation_snapshot.csv"
    fieldnames = [
        "ticker",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield",
        "source_name",
        "source_file",
        "data_as_of",
        "table_grain",
    ]

    def rows():
        for row in iter_csv_rows(source_path):
            yield {
                "ticker": row.get("stock_id", "").strip(),
                "pe_ratio": row.get("pe_ratio", "").strip(),
                "pb_ratio": row.get("pb_ratio", "").strip(),
                "dividend_yield": row.get("dividend_yield", "").strip(),
                "source_name": "shared_data.valuation",
                "source_file": str(source_path),
                "data_as_of": generated_at,
                "table_grain": "snapshot",
            }

    row_count = write_csv_rows(output_path, fieldnames, rows())
    return TableSummary(
        name="valuation_snapshot",
        source_path=str(source_path),
        output_path=str(output_path),
        row_count=row_count,
        grain="snapshot",
        status="warning",
        notes=["No historical date column is available in the source snapshot"],
    )


def _normalize_fundamentals_snapshot(paths: WorkspacePaths, generated_at: str) -> TableSummary:
    source_path = paths.shared_data_root / "fundamentals" / "yfinance_fundamentals.csv"
    output_path = paths.normalized_root / "fundamentals_snapshot.csv"
    fieldnames = [
        "ticker",
        "market_cap",
        "roe",
        "eps",
        "revenue",
        "net_income",
        "total_equity",
        "operating_cf",
        "free_cash_flow",
        "source_name",
        "source_file",
        "data_as_of",
        "table_grain",
    ]

    def rows():
        for row in iter_csv_rows(source_path):
            yield {
                "ticker": row.get("stock_id", "").strip(),
                "market_cap": row.get("market_cap", "").strip(),
                "roe": row.get("roe", "").strip(),
                "eps": row.get("eps", "").strip(),
                "revenue": row.get("revenue", "").strip(),
                "net_income": row.get("net_income", "").strip(),
                "total_equity": row.get("total_equity", "").strip(),
                "operating_cf": row.get("operating_cf", "").strip(),
                "free_cash_flow": row.get("free_cf", "").strip(),
                "source_name": "shared_data.yfinance_fundamentals",
                "source_file": str(source_path),
                "data_as_of": generated_at,
                "table_grain": "snapshot",
            }

    row_count = write_csv_rows(output_path, fieldnames, rows())
    return TableSummary(
        name="fundamentals_snapshot",
        source_path=str(source_path),
        output_path=str(output_path),
        row_count=row_count,
        grain="snapshot",
        status="warning",
        notes=["No report_date or fiscal_period is available in the source snapshot"],
    )


def _normalize_price_daily(paths: WorkspacePaths, generated_at: str) -> TableSummary:
    raw_root = paths.shared_data_root / "raw"
    output_path = paths.normalized_root / "price_daily.csv"
    fieldnames = [
        "ticker",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close",
        "turnover_value",
        "source_name",
        "source_file",
        "data_as_of",
        "table_grain",
    ]

    def rows():
        for source_path in sorted(raw_root.glob("*.csv")):
            if source_path.stem.upper() == "TAIEX":
                continue
            ticker = source_path.stem
            for row in iter_csv_rows(source_path):
                yield {
                    "ticker": ticker,
                    "date": row.get("Date", "").strip(),
                    "open": row.get("Open", "").strip(),
                    "high": row.get("High", "").strip(),
                    "low": row.get("Low", "").strip(),
                    "close": row.get("Close", "").strip(),
                    "volume": row.get("Volume", "").strip(),
                    "adjusted_close": "",
                    "turnover_value": "",
                    "source_name": "shared_data.raw_price",
                    "source_file": str(source_path),
                    "data_as_of": generated_at,
                    "table_grain": "time_series",
                }

    row_count = write_csv_rows(output_path, fieldnames, rows())
    return TableSummary(
        name="price_daily",
        source_path=str(raw_root),
        output_path=str(output_path),
        row_count=row_count,
        grain="time_series",
        status="ok",
        notes=["Ticker is derived from the raw file name"],
    )


def _normalize_benchmark_daily(paths: WorkspacePaths, generated_at: str) -> TableSummary:
    source_path = paths.shared_data_root / "raw" / "TAIEX.csv"
    output_path = paths.normalized_root / "benchmark_daily.csv"
    fieldnames = [
        "benchmark_id",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source_name",
        "source_file",
        "data_as_of",
        "table_grain",
    ]

    def rows():
        for row in iter_csv_rows(source_path):
            yield {
                "benchmark_id": "TAIEX",
                "date": row.get("Date", "").strip(),
                "open": row.get("Open", "").strip(),
                "high": row.get("High", "").strip(),
                "low": row.get("Low", "").strip(),
                "close": row.get("Close", "").strip(),
                "volume": row.get("Volume", "").strip(),
                "source_name": "shared_data.taiex",
                "source_file": str(source_path),
                "data_as_of": generated_at,
                "table_grain": "time_series",
            }

    row_count = write_csv_rows(output_path, fieldnames, rows())
    return TableSummary(
        name="benchmark_daily",
        source_path=str(source_path),
        output_path=str(output_path),
        row_count=row_count,
        grain="time_series",
        status="ok",
        notes=["Derived from raw/TAIEX.csv"],
    )
