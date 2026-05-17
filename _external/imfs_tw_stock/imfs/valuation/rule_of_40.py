"""Route B model: Rule of 40 quality score."""

from __future__ import annotations

from imfs.data.models import FinancialSnapshot, PriceRecord, ensure_same_currency
from imfs.routing.route_classifier import Route
from imfs.valuation.result import ValuationResult


def value_rule_of_40(snapshot: FinancialSnapshot, price: PriceRecord) -> ValuationResult:
    ensure_same_currency(snapshot, price)
    margin = snapshot.effective_margin()
    growth = snapshot.revenue_growth
    if growth is None or margin is None:
        return ValuationResult(
            ticker=snapshot.ticker,
            route=Route.B,
            model="RULE_OF_40",
            currency=snapshot.currency,
            intrinsic_value_per_share=None,
            current_price=price.close,
            margin_of_safety_price=None,
            valuation_gap_pct=None,
            confidence=0.0,
            warnings=("missing revenue growth or margin",),
        )

    score = (growth + margin) * 100.0
    premium_multiple_eligible = score >= 40.0
    confidence = 0.75 if premium_multiple_eligible else 0.45
    return ValuationResult(
        ticker=snapshot.ticker,
        route=Route.B,
        model="RULE_OF_40",
        currency=snapshot.currency,
        intrinsic_value_per_share=None,
        current_price=price.close,
        margin_of_safety_price=None,
        valuation_gap_pct=None,
        confidence=confidence,
        inputs={
            "revenue_growth_pct": growth * 100.0,
            "profit_margin_pct": margin * 100.0,
            "rule_of_40_score": score,
            "premium_multiple_eligible": str(premium_multiple_eligible),
        },
        warnings=("quality score only; no intrinsic value produced",),
    )
