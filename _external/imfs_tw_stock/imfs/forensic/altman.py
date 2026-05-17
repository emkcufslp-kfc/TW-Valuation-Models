"""Altman distress models."""

from __future__ import annotations

from dataclasses import dataclass

from imfs.data.models import FinancialSnapshot


@dataclass(frozen=True)
class ForensicScore:
    model: str
    score: float | None
    label: str
    warnings: tuple[str, ...] = ()

    @property
    def red_flag(self) -> bool:
        return self.label in {"distress", "manipulation_risk"}


def altman_z_score(snapshot: FinancialSnapshot) -> ForensicScore:
    required = [
        snapshot.working_capital,
        snapshot.retained_earnings,
        snapshot.ebit,
        snapshot.market_cap,
        snapshot.total_liabilities,
        snapshot.sales if snapshot.sales is not None else snapshot.revenue,
        snapshot.total_assets,
    ]
    if any(value is None for value in required):
        return ForensicScore("ALTMAN_Z", None, "insufficient_data", ("missing Altman Z inputs",))
    if not snapshot.total_assets or not snapshot.total_liabilities:
        return ForensicScore("ALTMAN_Z", None, "insufficient_data", ("invalid assets or liabilities",))

    sales = snapshot.sales if snapshot.sales is not None else snapshot.revenue
    score = (
        1.2 * (snapshot.working_capital / snapshot.total_assets)
        + 1.4 * (snapshot.retained_earnings / snapshot.total_assets)
        + 3.3 * (snapshot.ebit / snapshot.total_assets)
        + 0.6 * (snapshot.market_cap / snapshot.total_liabilities)
        + 1.0 * (sales / snapshot.total_assets)
    )
    if score < 1.81:
        label = "distress"
    elif score < 2.99:
        label = "grey_zone"
    else:
        label = "safe"
    return ForensicScore("ALTMAN_Z", score, label)


def altman_z_prime_score(snapshot: FinancialSnapshot) -> ForensicScore:
    required = [
        snapshot.working_capital,
        snapshot.retained_earnings,
        snapshot.ebit,
        snapshot.total_equity,
        snapshot.total_liabilities,
        snapshot.total_assets,
    ]
    if any(value is None for value in required):
        return ForensicScore("ALTMAN_Z_PRIME", None, "insufficient_data", ("missing Altman Z prime inputs",))
    if not snapshot.total_assets or not snapshot.total_liabilities:
        return ForensicScore("ALTMAN_Z_PRIME", None, "insufficient_data", ("invalid assets or liabilities",))

    score = (
        6.56 * (snapshot.working_capital / snapshot.total_assets)
        + 3.26 * (snapshot.retained_earnings / snapshot.total_assets)
        + 6.72 * (snapshot.ebit / snapshot.total_assets)
        + 1.05 * (snapshot.total_equity / snapshot.total_liabilities)
    )
    if score < 1.10:
        label = "distress"
    elif score < 2.60:
        label = "grey_zone"
    else:
        label = "safe"
    return ForensicScore("ALTMAN_Z_PRIME", score, label)

