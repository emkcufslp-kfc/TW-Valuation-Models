"""Shared data contracts for the IMFS 2.1 deterministic engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class Market(str, Enum):
    US = "US"
    HK = "HK"
    TW = "TW"


class Currency(str, Enum):
    USD = "USD"
    HKD = "HKD"
    TWD = "TWD"


@dataclass(frozen=True)
class SourceMeta:
    source: str
    as_of: date | None = None
    retrieved_at: datetime | None = None
    url: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class SecurityProfile:
    ticker: str
    name: str
    market: Market
    currency: Currency
    sector: str = ""
    industry: str = ""
    is_financial: bool = False
    is_cyclical: bool = False
    is_high_growth: bool = False
    is_stable_mature: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PriceRecord:
    ticker: str
    market: Market
    currency: Currency
    close: float
    trade_date: date
    source: SourceMeta
    adjusted_close: float | None = None


@dataclass(frozen=True)
class FinancialSnapshot:
    ticker: str
    market: Market
    currency: Currency
    fiscal_period_end: date
    source: SourceMeta
    revenue: float | None = None
    revenue_growth: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    normalized_earnings: float | None = None
    free_cash_flow: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    working_capital: float | None = None
    retained_earnings: float | None = None
    ebit: float | None = None
    sales: float | None = None
    market_cap: float | None = None
    shares_outstanding: float | None = None
    eps: float | None = None
    normalized_eps: float | None = None
    book_value_per_share: float | None = None
    price_to_book: float | None = None
    roe: float | None = None
    cost_of_equity: float | None = None
    growth_rate: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    one_time_adjustments: float = 0.0

    def current_ratio(self) -> float | None:
        if not self.current_liabilities:
            return None
        if self.current_assets is None:
            return None
        return self.current_assets / self.current_liabilities

    def debt_to_equity(self) -> float | None:
        if not self.total_equity:
            return None
        if self.total_liabilities is None:
            return None
        return self.total_liabilities / self.total_equity

    def effective_margin(self) -> float | None:
        if self.operating_margin is not None:
            return self.operating_margin
        if self.net_margin is not None:
            return self.net_margin
        if not self.revenue:
            return None
        if self.operating_income is not None:
            return self.operating_income / self.revenue
        if self.net_income is not None:
            return self.net_income / self.revenue
        return None


def ensure_same_currency(*records: object) -> Currency | None:
    currencies = {
        getattr(record, "currency", None)
        for record in records
        if getattr(record, "currency", None) is not None
    }
    if len(currencies) > 1:
        raise ValueError(f"Currency mismatch: {sorted(c.value for c in currencies)}")
    return next(iter(currencies), None)

