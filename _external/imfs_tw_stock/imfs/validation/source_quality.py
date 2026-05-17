"""Source-level validation for loaded IMFS records."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from imfs.data.models import FinancialSnapshot, PriceRecord, SecurityProfile, SourceMeta
from imfs.data.source_registry import SourceRegistry
from imfs.validation.result import Severity, ValidationReport


def validate_source_meta(source: SourceMeta, subject: str = "source") -> ValidationReport:
    report = ValidationReport(subject)
    if not source.source.strip():
        report.add("missing_source_name", "Source name is required.", field="source")
    if source.as_of is None and source.retrieved_at is None:
        report.add(
            "missing_source_timestamp",
            "Source requires either as_of date or retrieved_at timestamp.",
            field="source",
        )
    if source.as_of and source.as_of > date.today():
        report.add("future_source_as_of", "Source as_of date cannot be in the future.", field="as_of")
    if source.retrieved_at:
        now = datetime.now(source.retrieved_at.tzinfo)
        if source.retrieved_at > now:
            report.add(
                "future_retrieved_at",
                "Source retrieved_at timestamp cannot be in the future.",
                field="retrieved_at",
            )
    return report


def validate_registered_source(
    record: SecurityProfile | PriceRecord | FinancialSnapshot,
    registry: SourceRegistry,
) -> ValidationReport:
    source = getattr(record, "source", None)
    subject = f"registered_source:{getattr(record, 'ticker', 'unknown')}"
    report = ValidationReport(subject)
    if source is None:
        report.add(
            "record_has_no_source_meta",
            "Record type does not carry source metadata.",
            Severity.WARNING,
            field="source",
        )
        return report
    report.merge(validate_source_meta(source, subject))
    if not source.source:
        return report
    try:
        registered = registry.get(source.source)
    except KeyError:
        report.add("unregistered_source", f"Source is not registered: {source.source}", field="source")
        return report
    if getattr(record, "market", None) not in registered.markets:
        report.add(
            "source_market_mismatch",
            f"Source {source.source} is not registered for market {record.market.value}.",
            field="market",
        )
    if not registered.enabled:
        report.add(
            "source_disabled",
            f"Source {source.source} is disabled.",
            Severity.WARNING,
            field="source",
        )
    return report


def validate_ticker_alignment(
    securities: Iterable[SecurityProfile],
    prices: Iterable[PriceRecord],
    financials: Iterable[FinancialSnapshot],
) -> ValidationReport:
    report = ValidationReport("ticker_alignment")
    security_tickers = {item.ticker for item in securities}
    for item in prices:
        if item.ticker not in security_tickers:
            report.add(
                "price_without_security_profile",
                f"Price record has no matching security profile: {item.ticker}",
                field="ticker",
            )
    for item in financials:
        if item.ticker not in security_tickers:
            report.add(
                "financials_without_security_profile",
                f"Financial snapshot has no matching security profile: {item.ticker}",
                field="ticker",
            )
    return report

