"""Route A valuation: earnings power value."""

from __future__ import annotations

from imfs.data.models import FinancialSnapshot, PriceRecord, ensure_same_currency
from imfs.routing.route_classifier import Route
from imfs.valuation.normalization import adjusted_earnings
from imfs.valuation.result import ValuationResult, valuation_gap


def value_epv(
    snapshot: FinancialSnapshot,
    price: PriceRecord,
    wacc: float,
    margin_of_safety: float = 0.20,
) -> ValuationResult:
    ensure_same_currency(snapshot, price)
    warnings: list[str] = []
    earnings = snapshot.normalized_earnings
    if earnings is None and snapshot.net_income is not None:
        earnings = adjusted_earnings(snapshot.net_income, snapshot.one_time_adjustments)
        warnings.append("normalized earnings unavailable; adjusted net income used")
    if earnings is None or earnings <= 0:
        return _unusable(snapshot, price, "missing or non-positive normalized earnings")
    if not snapshot.shares_outstanding or snapshot.shares_outstanding <= 0:
        return _unusable(snapshot, price, "missing or invalid shares outstanding")
    if wacc <= 0:
        return _unusable(snapshot, price, "WACC must be positive")

    equity_value = earnings / wacc
    intrinsic = equity_value / snapshot.shares_outstanding
    mos = intrinsic * (1.0 - margin_of_safety)
    replacement_cost = snapshot.total_assets
    moat_ratio = equity_value / replacement_cost if replacement_cost and replacement_cost > 0 else None
    moat_label = _moat_label(moat_ratio)
    return ValuationResult(
        ticker=snapshot.ticker,
        route=Route.A,
        model="EPV",
        currency=snapshot.currency,
        intrinsic_value_per_share=intrinsic,
        current_price=price.close,
        margin_of_safety_price=mos,
        valuation_gap_pct=valuation_gap(intrinsic, price.close),
        confidence=0.75 if not warnings else 0.65,
        inputs={
            "adjusted_earnings": earnings,
            "wacc": wacc,
            "shares": snapshot.shares_outstanding,
            "epv_equity_value": equity_value,
            "asset_value_replacement_cost": replacement_cost,
            "moat_ratio": moat_ratio,
            "moat_label": moat_label,
        },
        warnings=tuple(warnings),
    )


def _unusable(snapshot: FinancialSnapshot, price: PriceRecord, warning: str) -> ValuationResult:
    return ValuationResult(
        ticker=snapshot.ticker,
        route=Route.A,
        model="EPV",
        currency=snapshot.currency,
        intrinsic_value_per_share=None,
        current_price=price.close,
        margin_of_safety_price=None,
        valuation_gap_pct=None,
        confidence=0.0,
        warnings=(warning,),
    )


def _moat_label(moat_ratio: float | None) -> str:
    if moat_ratio is None:
        return "unknown"
    if moat_ratio >= 1.25:
        return "strong_moat"
    if moat_ratio >= 1.0:
        return "possible_moat"
    return "no_moat"
