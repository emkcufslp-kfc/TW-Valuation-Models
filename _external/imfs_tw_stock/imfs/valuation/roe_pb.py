"""Route C valuation: ROE-PB model for financial institutions."""

from __future__ import annotations

from imfs.data.models import FinancialSnapshot, PriceRecord, ensure_same_currency
from imfs.routing.route_classifier import Route
from imfs.valuation.result import ValuationResult, valuation_gap


def value_roe_pb(
    snapshot: FinancialSnapshot,
    price: PriceRecord,
    margin_of_safety: float = 0.20,
) -> ValuationResult:
    ensure_same_currency(snapshot, price)
    roe = snapshot.roe
    growth = snapshot.growth_rate if snapshot.growth_rate is not None else 0.02
    cost = snapshot.cost_of_equity
    book = snapshot.book_value_per_share
    if roe is None or cost is None or book is None:
        return _unusable(snapshot, price, "missing ROE, cost of equity, or book value per share")
    if cost <= growth:
        return _unusable(snapshot, price, "cost of equity must be greater than growth")
    if roe <= growth:
        return _unusable(snapshot, price, "ROE must be greater than growth for a positive theoretical P/B")
    if book <= 0:
        return _unusable(snapshot, price, "book value per share must be positive")

    theoretical_pb = (roe - growth) / (cost - growth)
    intrinsic = theoretical_pb * book
    mos = intrinsic * (1.0 - margin_of_safety)
    actual_pb = snapshot.price_to_book
    roe_exceeds_cost = roe > cost
    pb_discount = actual_pb is not None and actual_pb < 1.0
    benchmark_candidate = roe_exceeds_cost and pb_discount
    return ValuationResult(
        ticker=snapshot.ticker,
        route=Route.C,
        model="ROE_PB",
        currency=snapshot.currency,
        intrinsic_value_per_share=intrinsic,
        current_price=price.close,
        margin_of_safety_price=mos,
        valuation_gap_pct=valuation_gap(intrinsic, price.close),
        confidence=0.75,
        inputs={
            "roe": roe,
            "growth": growth,
            "cost_of_equity": cost,
            "theoretical_pb": theoretical_pb,
            "actual_pb": actual_pb,
            "roe_minus_cost_of_equity": roe - cost,
            "roe_exceeds_cost_of_equity": str(roe_exceeds_cost),
            "pb_below_1": str(pb_discount),
            "benchmark_candidate": str(benchmark_candidate),
        },
    )


def _unusable(snapshot: FinancialSnapshot, price: PriceRecord, warning: str) -> ValuationResult:
    return ValuationResult(
        ticker=snapshot.ticker,
        route=Route.C,
        model="ROE_PB",
        currency=snapshot.currency,
        intrinsic_value_per_share=None,
        current_price=price.close,
        margin_of_safety_price=None,
        valuation_gap_pct=None,
        confidence=0.0,
        warnings=(warning,),
    )
