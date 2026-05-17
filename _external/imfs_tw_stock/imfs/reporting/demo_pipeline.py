"""Demo analysis pipeline for the confirmation dashboard."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math

from imfs.backtest import BacktestConfig, BacktestResult, run_periodic_backtest
from imfs.data.models import Currency, FinancialSnapshot, Market, PriceRecord, SecurityProfile, SourceMeta
from imfs.decision import Decision, decide
from imfs.decision import Verdict
from imfs.forensic import BeneishInputs, ForensicReport, altman_z_prime_score, altman_z_score, beneish_m_score
from imfs.reality import RealityOverlayInput, RealityOverlayResult, run_reality_overlay
from imfs.routing import RouteDecision, classify_security
from imfs.valuation import ValuationResult, value_by_route


@dataclass(frozen=True)
class DemoInput:
    profile: SecurityProfile
    price: PriceRecord
    financials: FinancialSnapshot
    beneish_inputs: BeneishInputs | None
    wacc: float = 0.10
    normalized_pe: float = 15.0
    cycle_position: str = "mid_cycle"


@dataclass(frozen=True)
class DemoAnalysis:
    profile: SecurityProfile
    price: PriceRecord
    financials: FinancialSnapshot
    route: RouteDecision
    valuation: ValuationResult
    forensic: ForensicReport
    decision: Decision
    reality: RealityOverlayResult


@dataclass(frozen=True)
class CsvImportResult:
    analyses: list[DemoAnalysis]
    errors: list[str]


@dataclass(frozen=True)
class CsvTickerUniverse:
    tickers: list[str]
    labels: dict[str, dict[str, str]]
    errors: list[str]


def run_demo_analysis(item: DemoInput) -> DemoAnalysis:
    route = classify_security(item.profile, item.financials)
    valuation = value_by_route(
        route,
        item.financials,
        item.price,
        wacc=item.wacc,
        normalized_pe=item.normalized_pe,
        cycle_position=item.cycle_position,
    )
    forensic = ForensicReport(
        ticker=item.profile.ticker,
        altman=_altman_score(item.profile, item.financials),
        beneish=beneish_m_score(item.beneish_inputs),
    )
    decision = decide(valuation, forensic)
    reality = run_reality_overlay(
        RealityOverlayInput(
            profile=item.profile,
            price=item.price,
            financials=item.financials,
            route=route,
            valuation=valuation,
            forensic=forensic,
            decision=decision,
        )
    )
    return DemoAnalysis(
        profile=item.profile,
        price=item.price,
        financials=item.financials,
        route=route,
        valuation=valuation,
        forensic=forensic,
        decision=decision,
        reality=reality,
    )


def _altman_score(profile: SecurityProfile, snapshot: FinancialSnapshot):
    if profile.market in {Market.HK, Market.TW}:
        return altman_z_prime_score(snapshot)
    return altman_z_score(snapshot)


def run_us_demo_universe(as_of: date | None = None) -> list[DemoAnalysis]:
    return [run_demo_analysis(item) for item in us_demo_inputs(as_of=as_of)]


def us_demo_inputs(as_of: date | None = None) -> list[DemoInput]:
    effective_as_of = as_of or date.today()
    source = SourceMeta(
        source="unit_fixture",
        as_of=effective_as_of,
        retrieved_at=datetime.now(),
        notes="US demo data for dashboard confirmation only.",
    )
    return [
        DemoInput(
            profile=SecurityProfile(
                ticker="AAPL",
                name="Apple",
                market=Market.US,
                currency=Currency.USD,
                sector="Technology",
                industry="Consumer Electronics",
                is_stable_mature=True,
            ),
            price=_price("AAPL", 185.0, source, effective_as_of, Market.US, Currency.USD),
            financials=_financials(
                "AAPL",
                source,
                revenue=390_000.0,
                revenue_growth=0.04,
                operating_income=115_000.0,
                net_income=100_000.0,
                normalized_earnings=231_000.0,
                free_cash_flow=105_000.0,
                total_assets=350_000.0,
                total_liabilities=290_000.0,
                total_equity=60_000.0,
                working_capital=20_000.0,
                retained_earnings=10_000.0,
                ebit=115_000.0,
                sales=390_000.0,
                market_cap=2_850_000.0,
                shares_outstanding=15_400.0,
                eps=6.45,
                normalized_eps=6.15,
                operating_margin=0.295,
            ),
            beneish_inputs=_clean_beneish(),
            wacc=0.075,
        ),
        DemoInput(
            profile=SecurityProfile(
                ticker="NVDA",
                name="NVIDIA",
                market=Market.US,
                currency=Currency.USD,
                sector="Technology",
                industry="AI Infrastructure",
                is_high_growth=True,
            ),
            price=_price("NVDA", 925.0, source, effective_as_of, Market.US, Currency.USD),
            financials=_financials(
                "NVDA",
                source,
                revenue=95_000.0,
                revenue_growth=0.62,
                operating_income=52_000.0,
                net_income=45_000.0,
                normalized_earnings=43_000.0,
                free_cash_flow=40_000.0,
                total_assets=120_000.0,
                total_liabilities=35_000.0,
                total_equity=85_000.0,
                working_capital=45_000.0,
                retained_earnings=55_000.0,
                ebit=52_000.0,
                sales=95_000.0,
                market_cap=2_300_000.0,
                shares_outstanding=2_500.0,
                eps=18.0,
                normalized_eps=17.2,
                operating_margin=0.55,
            ),
            beneish_inputs=_clean_beneish(),
        ),
        DemoInput(
            profile=SecurityProfile(
                ticker="JPM",
                name="JPMorgan Chase",
                market=Market.US,
                currency=Currency.USD,
                sector="Financials",
                industry="Bank",
                is_financial=True,
            ),
            price=_price("JPM", 210.0, source, effective_as_of, Market.US, Currency.USD),
            financials=_financials(
                "JPM",
                source,
                revenue=165_000.0,
                revenue_growth=0.06,
                operating_income=62_000.0,
                net_income=50_000.0,
                normalized_earnings=48_000.0,
                total_assets=600_000.0,
                total_liabilities=250_000.0,
                total_equity=350_000.0,
                working_capital=180_000.0,
                retained_earnings=240_000.0,
                ebit=62_000.0,
                sales=165_000.0,
                market_cap=590_000.0,
                shares_outstanding=2_800.0,
                eps=17.8,
                book_value_per_share=260.0,
                price_to_book=0.92,
                roe=0.15,
                cost_of_equity=0.10,
                growth_rate=0.03,
            ),
            beneish_inputs=_clean_beneish(),
        ),
    ]


def load_csv_universe(csv_text: str, as_of: date | None = None) -> CsvImportResult:
    effective_as_of = as_of or date.today()
    source = SourceMeta(
        source="user_csv",
        as_of=effective_as_of,
        retrieved_at=datetime.now(),
        notes="User supplied CSV. Values are treated as point-in-time as of the selected date.",
    )
    errors: list[str] = []
    analyses: list[DemoAnalysis] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return CsvImportResult([], ["CSV header row is required."])

    for index, row in enumerate(reader, start=2):
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            errors.append(f"Row {index}: ticker is required.")
            continue
        try:
            item = _demo_input_from_csv_row(row, source, effective_as_of)
            analyses.append(run_demo_analysis(item))
        except ValueError as exc:
            errors.append(f"Row {index} {ticker}: {exc}")
    return CsvImportResult(analyses, errors)


def extract_csv_ticker_universe(csv_text: str) -> CsvTickerUniverse:
    errors: list[str] = []
    labels: dict[str, dict[str, str]] = {}
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return CsvTickerUniverse([], {}, ["CSV header row is required."])

    for index, row in enumerate(reader, start=2):
        code = _first_present(row, "ticker", "代號", "代码", "證券代號", "证券代码", "code", "symbol")
        if not code:
            errors.append(f"Row {index}: ticker is required.")
            continue
        market_raw = _first_present(row, "market", "市場", "市场")
        market = (market_raw or "").strip().upper()
        ticker = _normalize_uploaded_ticker(code.strip(), market)
        labels[ticker] = {
            "name": _first_present(row, "name", "名稱", "名称") or ticker,
            "sector": _first_present(row, "sector", "產業別", "产业别") or "",
            "industry": _first_present(row, "industry", "主要業務", "主要业务") or "",
            "market": market or "US",
        }
    return CsvTickerUniverse(list(labels.keys()), labels, errors)


def rank_analyses(analyses: list[DemoAnalysis]) -> list[tuple[int, DemoAnalysis]]:
    ranked = sorted(analyses, key=analysis_rank_score, reverse=True)
    return list(enumerate(ranked, start=1))


def analysis_rank_score(analysis: DemoAnalysis) -> float:
    verdict_score = {
        Verdict.BUY: 60.0,
        Verdict.HOLD: 25.0,
        Verdict.NO_DECISION: 5.0,
        Verdict.SELL: -25.0,
        Verdict.AVOID: -100.0,
    }[analysis.decision.verdict]
    valuation_gap = analysis.valuation.valuation_gap_pct
    if valuation_gap is None or not math.isfinite(valuation_gap):
        valuation_gap = 0.0
    route_confidence = analysis.route.confidence if math.isfinite(analysis.route.confidence) else 0.0
    valuation_confidence = analysis.valuation.confidence if math.isfinite(analysis.valuation.confidence) else 0.0
    forensic_confidence = analysis.forensic.confidence if math.isfinite(analysis.forensic.confidence) else 0.0
    if analysis.forensic.red_flag:
        return -100.0 + analysis.decision.confidence
    return (
        verdict_score
        + valuation_gap * 100.0
        + route_confidence * 10.0
        + valuation_confidence * 10.0
        + forensic_confidence * 10.0
    )


def run_mock_backtest(analyses: list[DemoAnalysis], as_of: date | None = None) -> BacktestResult:
    if not analyses:
        raise ValueError("analyses cannot be empty")
    ranked = rank_analyses(analyses)
    eligible = [analysis for _, analysis in ranked if analysis.decision.verdict in {Verdict.BUY, Verdict.HOLD}]
    if not eligible:
        eligible = [analysis for _, analysis in ranked[: min(3, len(ranked))]]
    top = eligible[: min(3, len(eligible))]
    tickers = [analysis.profile.ticker for analysis in analyses]
    weights = []
    returns = []
    end_date = as_of or date.today()
    for period in range(6):
        period_date = end_date - timedelta(days=(5 - period) * 30)
        weights.append({analysis.profile.ticker: 1.0 / len(top) for analysis in top})
        returns.append(
            {
                ticker: _mock_period_return(ticker, period, period_date)
                for ticker in tickers
            }
        )
    return run_periodic_backtest(
        returns,
        weights,
        BacktestConfig(execution_lag_periods=1, transaction_cost_bps=10.0, periods_per_year=12),
    )


def sample_csv() -> str:
    return "\n".join(
        [
            "ticker,name,sector,industry,price,revenue,revenue_growth,operating_income,net_income,normalized_earnings,free_cash_flow,total_assets,total_liabilities,total_equity,working_capital,retained_earnings,ebit,sales,market_cap,shares_outstanding,eps,book_value_per_share,price_to_book,roe,cost_of_equity,growth_rate,operating_margin,is_financial,is_high_growth,is_cyclical,is_stable_mature",
            "MSFT,Microsoft,Technology,Cloud Software,430,245000,0.15,110000,90000,92000,82000,520000,250000,270000,120000,160000,110000,245000,3200000,7430,12.1,,,.33,,,.45,false,false,false,true",
            "CRM,Salesforce,Technology,SaaS,285,41000,0.23,8200,6200,6500,7200,105000,47000,58000,26000,37000,8200,41000,280000,980,6.3,,,.11,,,.20,false,true,false,false",
            "BAC,Bank of America,Financials,Bank,38,98000,0.04,33000,27000,26000,,380000,180000,200000,90000,135000,33000,98000,305000,8020,3.35,34,0.95,0.125,0.10,0.025,,true,false,false,false",
        ]
    )


def _demo_input_from_csv_row(row: dict[str, str], source: SourceMeta, as_of: date) -> DemoInput:
    ticker = _required_text(row, "ticker").upper()
    market = _market(row.get("market"))
    currency = _currency(row.get("currency"), market)
    profile = SecurityProfile(
        ticker=ticker,
        name=row.get("name") or ticker,
        market=market,
        currency=currency,
        sector=row.get("sector") or "",
        industry=row.get("industry") or "",
        is_financial=_bool(row.get("is_financial")),
        is_cyclical=_bool(row.get("is_cyclical")),
        is_high_growth=_bool(row.get("is_high_growth")),
        is_stable_mature=_bool(row.get("is_stable_mature")),
    )
    price = _price(ticker, _required_float(row, "price"), source, as_of, market, currency)
    financials = _financials(
        ticker,
        source,
        market=market,
        currency=currency,
        revenue=_float(row.get("revenue")),
        revenue_growth=_float(row.get("revenue_growth")),
        operating_income=_float(row.get("operating_income")),
        net_income=_float(row.get("net_income")),
        normalized_earnings=_float(row.get("normalized_earnings")),
        free_cash_flow=_float(row.get("free_cash_flow")),
        total_assets=_float(row.get("total_assets")),
        total_liabilities=_float(row.get("total_liabilities")),
        total_equity=_float(row.get("total_equity")),
        working_capital=_float(row.get("working_capital")),
        retained_earnings=_float(row.get("retained_earnings")),
        ebit=_float(row.get("ebit")),
        sales=_float(row.get("sales")),
        market_cap=_float(row.get("market_cap")),
        shares_outstanding=_float(row.get("shares_outstanding")),
        eps=_float(row.get("eps")),
        normalized_eps=_float(row.get("normalized_eps")),
        book_value_per_share=_float(row.get("book_value_per_share")),
        price_to_book=_float(row.get("price_to_book")),
        roe=_float(row.get("roe")),
        cost_of_equity=_float(row.get("cost_of_equity")),
        growth_rate=_float(row.get("growth_rate")),
        operating_margin=_float(row.get("operating_margin")),
        net_margin=_float(row.get("net_margin")),
    )
    return DemoInput(
        profile=profile,
        price=price,
        financials=financials,
        beneish_inputs=_beneish_from_csv_row(row),
        wacc=_float(row.get("wacc")) or 0.10,
        normalized_pe=_float(row.get("normalized_pe")) or 15.0,
        cycle_position=row.get("cycle_position") or "mid_cycle",
    )


def _price(
    ticker: str,
    close: float,
    source: SourceMeta,
    trade_date: date,
    market: Market,
    currency: Currency,
) -> PriceRecord:
    return PriceRecord(
        ticker=ticker,
        market=market,
        currency=currency,
        close=close,
        adjusted_close=close,
        trade_date=trade_date,
        source=source,
    )


def _financials(
    ticker: str,
    source: SourceMeta,
    market: Market = Market.US,
    currency: Currency = Currency.USD,
    **kwargs,
) -> FinancialSnapshot:
    return FinancialSnapshot(
        ticker=ticker,
        market=market,
        currency=currency,
        fiscal_period_end=date(2026, 3, 31),
        source=source,
        current_assets=kwargs.pop("current_assets", None),
        current_liabilities=kwargs.pop("current_liabilities", None),
        **kwargs,
    )


def _clean_beneish() -> BeneishInputs:
    return BeneishInputs(
        dsri=0.95,
        gmi=0.98,
        aqi=1.00,
        sgi=1.05,
        depi=1.00,
        sgai=0.98,
        lvgi=1.00,
        tata=0.02,
    )


def _beneish_from_csv_row(row: dict[str, str]) -> BeneishInputs:
    return BeneishInputs(
        dsri=_float(row.get("dsri")) or 0.95,
        gmi=_float(row.get("gmi")) or 0.98,
        aqi=_float(row.get("aqi")) or 1.00,
        sgi=_float(row.get("sgi")) or 1.05,
        depi=_float(row.get("depi")) or 1.00,
        sgai=_float(row.get("sgai")) or 0.98,
        lvgi=_float(row.get("lvgi")) or 1.00,
        tata=_float(row.get("tata")) or 0.02,
    )


def _required_text(row: dict[str, str], field: str) -> str:
    value = (row.get(field) or "").strip()
    if not value:
        raise ValueError(f"{field} is required")
    return value


def _required_float(row: dict[str, str], field: str) -> float:
    value = _float(row.get(field))
    if value is None:
        raise ValueError(f"{field} is required and must be numeric")
    return value


def _float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except ValueError as exc:
        raise ValueError(f"invalid numeric value '{value}'") from exc


def _bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _market(value: str | None) -> Market:
    if not value:
        return Market.US
    return Market(value.strip().upper())


def _currency(value: str | None, market: Market) -> Currency:
    if value:
        return Currency(value.strip().upper())
    return {
        Market.US: Currency.USD,
        Market.HK: Currency.HKD,
        Market.TW: Currency.TWD,
    }[market]


def _mock_period_return(ticker: str, period: int, period_date: date) -> float:
    seed = sum(ord(char) for char in ticker) + period * 17 + period_date.month
    return ((seed % 13) - 5) / 100.0


def _first_present(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and value.strip():
            return value.strip()
    return None


def _normalize_uploaded_ticker(raw: str, market: str) -> str:
    symbol = raw.strip().upper()
    if "." in symbol:
        return symbol
    if market in {"TWSE", "TW", "TSE"}:
        return f"{symbol}.TW"
    if market in {"TPEX", "TWO", "OTC"}:
        return f"{symbol}.TWO"
    if market in {"HKEX", "HK"}:
        return f"{symbol}.HK"
    return symbol
