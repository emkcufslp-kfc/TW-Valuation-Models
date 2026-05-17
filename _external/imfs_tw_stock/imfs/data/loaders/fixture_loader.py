"""JSON fixture loader for deterministic source-integration tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from imfs.data.models import (
    Currency,
    FinancialSnapshot,
    Market,
    PriceRecord,
    SecurityProfile,
    SourceMeta,
)


@dataclass(frozen=True)
class FixtureBundle:
    securities: list[SecurityProfile]
    prices: list[PriceRecord]
    financials: list[FinancialSnapshot]


class FixtureLoader:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def load(self) -> FixtureBundle:
        return FixtureBundle(
            securities=self.load_securities("security_profiles.json"),
            prices=self.load_prices("prices.json"),
            financials=self.load_financials("financial_snapshots.json"),
        )

    def load_securities(self, filename: str) -> list[SecurityProfile]:
        return [_security_from_dict(row) for row in _read_json(self.root / filename)]

    def load_prices(self, filename: str) -> list[PriceRecord]:
        return [_price_from_dict(row) for row in _read_json(self.root / filename)]

    def load_financials(self, filename: str) -> list[FinancialSnapshot]:
        return [_financial_from_dict(row) for row in _read_json(self.root / filename)]


def _read_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in fixture: {path}")
    return data


def _source_from_dict(row: dict[str, Any]) -> SourceMeta:
    source = row.get("source") or {}
    return SourceMeta(
        source=str(source.get("name") or ""),
        as_of=_parse_date(source.get("as_of")),
        retrieved_at=_parse_datetime(source.get("retrieved_at")),
        url=source.get("url"),
        notes=source.get("notes"),
    )


def _security_from_dict(row: dict[str, Any]) -> SecurityProfile:
    return SecurityProfile(
        ticker=str(row["ticker"]),
        name=str(row["name"]),
        market=Market(row["market"]),
        currency=Currency(row["currency"]),
        sector=str(row.get("sector", "")),
        industry=str(row.get("industry", "")),
        is_financial=bool(row.get("is_financial", False)),
        is_cyclical=bool(row.get("is_cyclical", False)),
        is_high_growth=bool(row.get("is_high_growth", False)),
        is_stable_mature=bool(row.get("is_stable_mature", False)),
        metadata=dict(row.get("metadata", {})),
    )


def _price_from_dict(row: dict[str, Any]) -> PriceRecord:
    return PriceRecord(
        ticker=str(row["ticker"]),
        market=Market(row["market"]),
        currency=Currency(row["currency"]),
        close=float(row["close"]),
        trade_date=_parse_date(row["trade_date"]),
        source=_source_from_dict(row),
        adjusted_close=_optional_float(row.get("adjusted_close")),
    )


def _financial_from_dict(row: dict[str, Any]) -> FinancialSnapshot:
    fields = {
        "ticker": str(row["ticker"]),
        "market": Market(row["market"]),
        "currency": Currency(row["currency"]),
        "fiscal_period_end": _parse_date(row["fiscal_period_end"]),
        "source": _source_from_dict(row),
    }
    optional_fields = [
        "revenue",
        "revenue_growth",
        "operating_income",
        "net_income",
        "normalized_earnings",
        "free_cash_flow",
        "total_assets",
        "total_liabilities",
        "total_equity",
        "current_assets",
        "current_liabilities",
        "working_capital",
        "retained_earnings",
        "ebit",
        "sales",
        "market_cap",
        "shares_outstanding",
        "eps",
        "normalized_eps",
        "book_value_per_share",
        "price_to_book",
        "roe",
        "cost_of_equity",
        "growth_rate",
        "operating_margin",
        "net_margin",
        "one_time_adjustments",
    ]
    for name in optional_fields:
        if name in row:
            fields[name] = _optional_float(row.get(name))
    return FinancialSnapshot(**fields)


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)

