"""Valuation dispatcher keyed by routing decision."""

from __future__ import annotations

from imfs.data.models import FinancialSnapshot, PriceRecord
from imfs.routing.route_classifier import Route, RouteDecision
from imfs.valuation.epv import value_epv
from imfs.valuation.normalized_pe import value_normalized_pe
from imfs.valuation.result import ValuationResult
from imfs.valuation.roe_pb import value_roe_pb
from imfs.valuation.rule_of_40 import value_rule_of_40


def value_by_route(
    route: RouteDecision,
    snapshot: FinancialSnapshot,
    price: PriceRecord,
    *,
    wacc: float = 0.10,
    normalized_pe: float = 15.0,
    margin_of_safety: float = 0.20,
    cycle_position: str = "mid_cycle",
) -> ValuationResult:
    if route.route == Route.A:
        return value_epv(snapshot, price, wacc=wacc, margin_of_safety=margin_of_safety)
    if route.route == Route.B:
        return value_rule_of_40(snapshot, price)
    if route.route == Route.C:
        return value_roe_pb(snapshot, price, margin_of_safety=margin_of_safety)
    if route.route == Route.D:
        return value_normalized_pe(
            snapshot,
            price,
            normalized_pe=normalized_pe,
            margin_of_safety=margin_of_safety,
            cycle_position=cycle_position,
        )
    raise ValueError(f"Unsupported route: {route.route}")
