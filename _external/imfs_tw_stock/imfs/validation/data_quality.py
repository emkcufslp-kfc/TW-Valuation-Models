"""Data quality checks for Phase 1 data contracts."""

from __future__ import annotations

from datetime import date

from imfs.data.models import FinancialSnapshot, PriceRecord, SecurityProfile
from imfs.validation.result import Severity, ValidationReport


def validate_security_profile(profile: SecurityProfile) -> ValidationReport:
    report = ValidationReport(f"security:{profile.ticker}")
    if not profile.ticker.strip():
        report.add("missing_ticker", "Ticker is required.", field="ticker")
    if not profile.name.strip():
        report.add("missing_name", "Security name is required.", field="name")
    if not profile.currency:
        report.add("missing_currency", "Currency is required.", field="currency")
    return report


def validate_price_record(record: PriceRecord, max_age_days: int = 10) -> ValidationReport:
    report = ValidationReport(f"price:{record.ticker}")
    if record.close <= 0:
        report.add("invalid_close", "Close price must be positive.", field="close")
    if record.adjusted_close is not None and record.adjusted_close <= 0:
        report.add(
            "invalid_adjusted_close",
            "Adjusted close must be positive when provided.",
            field="adjusted_close",
        )
    if record.trade_date > date.today():
        report.add("future_trade_date", "Trade date cannot be in the future.", field="trade_date")
    age_days = (date.today() - record.trade_date).days
    if age_days > max_age_days:
        report.add(
            "stale_price",
            f"Price is {age_days} days old.",
            Severity.WARNING,
            field="trade_date",
        )
    if not record.source.source.strip():
        report.add("missing_source", "Price source is required.", field="source")
    return report


def validate_financial_snapshot(
    snapshot: FinancialSnapshot,
    as_of: date | None = None,
) -> ValidationReport:
    report = ValidationReport(f"financials:{snapshot.ticker}")
    reference_date = as_of or date.today()
    if snapshot.fiscal_period_end > reference_date:
        report.add(
            "future_fiscal_period",
            "Fiscal period cannot be after the reference date.",
            field="fiscal_period_end",
        )
    if not snapshot.source.source.strip():
        report.add("missing_source", "Financial source is required.", field="source")
    if snapshot.total_equity is not None and snapshot.total_equity <= 0:
        report.add(
            "negative_or_zero_equity",
            "Total equity is zero or negative and must be explicitly handled.",
            Severity.WARNING,
            field="total_equity",
        )
    if snapshot.shares_outstanding is not None and snapshot.shares_outstanding <= 0:
        report.add(
            "invalid_shares",
            "Shares outstanding must be positive when provided.",
            field="shares_outstanding",
        )
    if snapshot.revenue is None and snapshot.net_income is None and snapshot.eps is None:
        report.add(
            "insufficient_statement_data",
            "At least one of revenue, net income, or EPS is required.",
            field="revenue",
        )
    return report

