"""Route D valuation: normalized P/E model."""

from __future__ import annotations

from imfs.data.models import FinancialSnapshot, PriceRecord, ensure_same_currency
from imfs.routing.route_classifier import Route
from imfs.valuation.result import ValuationResult, valuation_gap


def value_normalized_pe(
    snapshot: FinancialSnapshot,
    price: PriceRecord,
    normalized_pe: float,
    margin_of_safety: float = 0.20,
    cycle_position: str = "mid_cycle",
) -> ValuationResult:
    ensure_same_currency(snapshot, price)
    eps = snapshot.normalized_eps if snapshot.normalized_eps is not None else snapshot.eps
    if eps is None or eps <= 0:
        return _unusable(snapshot, price, "missing or non-positive normalized EPS")
    if normalized_pe <= 0:
        return _unusable(snapshot, price, "normalized P/E must be positive")

    intrinsic = eps * normalized_pe
    mos = intrinsic * (1.0 - margin_of_safety)
    warnings: list[str] = []
    if cycle_position != "mid_cycle":
        warnings.append("cyclical error risk: normalized EPS should represent mid-cycle earnings")
    return ValuationResult(
        ticker=snapshot.ticker,
        route=Route.D,
        model="NORMALIZED_PE",
        currency=snapshot.currency,
        intrinsic_value_per_share=intrinsic,
        current_price=price.close,
        margin_of_safety_price=mos,
        valuation_gap_pct=valuation_gap(intrinsic, price.close),
        confidence=0.70 if cycle_position == "mid_cycle" else 0.55,
        inputs={
            "mid_cycle_eps": eps,
            "normalized_pe": normalized_pe,
            "cycle_position": cycle_position,
            "cyclical_error_guardrail": "avoid peak-trough P/E interpretation",
        },
        warnings=tuple(warnings),
    )


def _unusable(snapshot: FinancialSnapshot, price: PriceRecord, warning: str) -> ValuationResult:
    return ValuationResult(
        ticker=snapshot.ticker,
        route=Route.D,
        model="NORMALIZED_PE",
        currency=snapshot.currency,
        intrinsic_value_per_share=None,
        current_price=price.close,
        margin_of_safety_price=None,
        valuation_gap_pct=None,
        confidence=0.0,
        warnings=(warning,),
    )
