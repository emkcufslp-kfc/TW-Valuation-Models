"""Route classification for IMFS valuation models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from imfs.data.models import FinancialSnapshot, SecurityProfile


class Route(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


ROUTE_MODELS: dict[Route, str] = {
    Route.A: "EPV",
    Route.B: "RULE_OF_40",
    Route.C: "ROE_PB",
    Route.D: "NORMALIZED_PE",
}


@dataclass(frozen=True)
class RouteDecision:
    route: Route
    model: str
    confidence: float
    reasons: tuple[str, ...]
    manual_override: bool = False


FINANCIAL_TERMS = ("bank", "financial", "insurance", "broker", "securities", "holding")
HIGH_GROWTH_TERMS = ("software", "saas", "cloud", "ai", "internet", "platform")
CYCLICAL_TERMS = (
    "semiconductor",
    "steel",
    "chemical",
    "commodity",
    "materials",
    "shipping",
    "memory",
)


def classify_security(
    profile: SecurityProfile,
    snapshot: FinancialSnapshot | None = None,
    override: Route | str | None = None,
) -> RouteDecision:
    if override is not None:
        route = Route(override)
        return RouteDecision(
            route=route,
            model=ROUTE_MODELS[route],
            confidence=1.0,
            reasons=("manual override",),
            manual_override=True,
        )

    sector = profile.sector.lower()
    industry = profile.industry.lower()
    combined = f"{sector} {industry}"
    revenue_growth = snapshot.revenue_growth if snapshot else None

    if profile.is_financial or any(term in combined for term in FINANCIAL_TERMS):
        return _decision(Route.C, 0.95, "financial institution route priority")

    if profile.is_high_growth or (
        any(term in combined for term in HIGH_GROWTH_TERMS)
        and revenue_growth is not None
        and revenue_growth >= 0.20
    ):
        return _decision(Route.B, 0.80, "high-growth technology profile")

    if profile.is_cyclical or any(term in combined for term in CYCLICAL_TERMS):
        return _decision(Route.D, 0.80, "cyclical or semiconductor profile")

    if profile.is_stable_mature:
        return _decision(Route.A, 0.80, "stable mature enterprise flag")

    if snapshot and snapshot.free_cash_flow and snapshot.revenue_growth is not None:
        if -0.05 <= snapshot.revenue_growth <= 0.15:
            return _decision(Route.A, 0.70, "stable cash generation and moderate growth")

    return _decision(Route.A, 0.55, "default mature-enterprise route")


def _decision(route: Route, confidence: float, reason: str) -> RouteDecision:
    return RouteDecision(
        route=route,
        model=ROUTE_MODELS[route],
        confidence=confidence,
        reasons=(reason,),
    )

