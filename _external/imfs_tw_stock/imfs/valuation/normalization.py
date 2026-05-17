"""Earnings normalization helpers for valuation routes."""

from __future__ import annotations


def adjusted_earnings(
    reported_earnings: float | None,
    one_time_items: float = 0.0,
    cyclicality_adjustment: float = 0.0,
) -> float | None:
    """Normalize earnings by removing one-time items and cycle effects."""
    if reported_earnings is None:
        return None
    return reported_earnings - one_time_items + cyclicality_adjustment

