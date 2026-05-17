"""Data source registry for IMFS 2.1 loaders."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from imfs.data.models import Market


class SourceTrust(str, Enum):
    OFFICIAL = "official"
    SECONDARY = "secondary"
    FIXTURE = "fixture"
    MANUAL = "manual"


@dataclass(frozen=True)
class DataSource:
    name: str
    markets: tuple[Market, ...]
    trust: SourceTrust
    description: str
    url: str | None = None
    enabled: bool = True


class SourceRegistry:
    def __init__(self, sources: tuple[DataSource, ...] = ()) -> None:
        self._sources = {source.name: source for source in sources}

    def register(self, source: DataSource) -> None:
        self._sources[source.name] = source

    def get(self, name: str) -> DataSource:
        try:
            return self._sources[name]
        except KeyError as exc:
            raise KeyError(f"Unknown data source: {name}") from exc

    def list(self, market: Market | None = None) -> list[DataSource]:
        sources = list(self._sources.values())
        if market is None:
            return sources
        return [source for source in sources if market in source.markets]


DEFAULT_SOURCE_REGISTRY = SourceRegistry(
    (
        DataSource(
            name="twse_openapi",
            markets=(Market.TW,),
            trust=SourceTrust.OFFICIAL,
            description="Taiwan Stock Exchange official OpenAPI.",
            url="https://openapi.twse.com.tw/",
        ),
        DataSource(
            name="yfinance",
            markets=(Market.US, Market.HK, Market.TW),
            trust=SourceTrust.SECONDARY,
            description="Secondary bootstrap source for prices and metadata.",
            url="https://query1.finance.yahoo.com/",
        ),
        DataSource(
            name="unit_fixture",
            markets=(Market.US, Market.HK, Market.TW),
            trust=SourceTrust.FIXTURE,
            description="Local deterministic test fixture source.",
        ),
    )
)

