"""Valuation result contract."""

from __future__ import annotations

from dataclasses import dataclass, field

from imfs.data.models import Currency
from imfs.routing.route_classifier import Route


@dataclass(frozen=True)
class ValuationResult:
    ticker: str
    route: Route
    model: str
    currency: Currency
    intrinsic_value_per_share: float | None
    current_price: float | None
    margin_of_safety_price: float | None
    valuation_gap_pct: float | None
    confidence: float
    inputs: dict[str, float | str | None] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def usable(self) -> bool:
        return (
            self.intrinsic_value_per_share is not None
            and self.current_price is not None
            and self.current_price > 0
            and self.confidence > 0
        )


def valuation_gap(intrinsic_value: float | None, current_price: float | None) -> float | None:
    if intrinsic_value is None or current_price is None or current_price <= 0:
        return None
    return (intrinsic_value - current_price) / current_price

