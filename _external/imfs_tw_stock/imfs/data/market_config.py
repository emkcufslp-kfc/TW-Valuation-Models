"""Market configuration helpers for IMFS 2.1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from imfs.data.models import Currency, Market


@dataclass(frozen=True)
class MarketSettings:
    market: Market
    currency: Currency
    enabled: bool = True
    notes: str = ""


DEFAULT_MARKETS: dict[Market, MarketSettings] = {
    Market.US: MarketSettings(Market.US, Currency.USD, True, "US equities"),
    Market.HK: MarketSettings(Market.HK, Currency.HKD, True, "Hong Kong equities"),
    Market.TW: MarketSettings(Market.TW, Currency.TWD, True, "Taiwan equities"),
}


def get_market_settings(market: Market | str) -> MarketSettings:
    normalized = Market(market)
    return DEFAULT_MARKETS[normalized]


def list_enabled_markets() -> list[MarketSettings]:
    return [settings for settings in DEFAULT_MARKETS.values() if settings.enabled]


def config_exists(path: str | Path = "config/markets.yaml") -> bool:
    return Path(path).exists()

