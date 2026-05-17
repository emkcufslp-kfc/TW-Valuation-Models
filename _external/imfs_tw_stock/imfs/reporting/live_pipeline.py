"""Live-market reporting pipeline with graceful fallback semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
from typing import Any, Protocol

from imfs.data.models import Currency, FinancialSnapshot, Market, PriceRecord, SecurityProfile, SourceMeta
from imfs.forensic import BeneishInputs
from imfs.reporting.demo_pipeline import DemoAnalysis, DemoInput, run_demo_analysis


class LiveProvider(Protocol):
    def fetch_security(self, ticker: str, as_of: date) -> DemoInput:
        ...


@dataclass(frozen=True)
class LiveUniverseResult:
    analyses: list[DemoAnalysis]
    errors: list[str]


def run_live_universe(
    tickers: list[str],
    *,
    as_of: date | None = None,
    provider: LiveProvider | None = None,
) -> LiveUniverseResult:
    effective_as_of = as_of or date.today()
    live_provider = provider or YFinanceProvider()
    analyses: list[DemoAnalysis] = []
    errors: list[str] = []

    for raw in tickers:
        ticker = raw.strip().upper()
        if not ticker:
            continue
        try:
            analyses.append(run_demo_analysis(live_provider.fetch_security(ticker, effective_as_of)))
        except Exception as exc:
            errors.append(f"{ticker}: {exc}")
    return LiveUniverseResult(analyses=analyses, errors=errors)


class YFinanceProvider:
    def fetch_security(self, ticker: str, as_of: date) -> DemoInput:
        try:
            import yfinance as yf
        except Exception as exc:  # pragma: no cover - dependency import failure
            raise RuntimeError("yfinance is unavailable") from exc

        instrument = yf.Ticker(ticker)
        info = instrument.info or {}
        history = instrument.history(period="1mo", interval="1d", auto_adjust=False)
        if history is None or history.empty:
            raise RuntimeError("no price history returned")
        close_row = history[history.index.date <= as_of]
        if close_row.empty:
            close_row = history
        latest = close_row.iloc[-1]
        trade_date = close_row.index[-1].date()

        market = _infer_market(ticker)
        currency = _infer_currency(info.get("currency"), market)
        source = SourceMeta(
            source="yfinance_live",
            as_of=trade_date,
            retrieved_at=datetime.now(),
            url="https://finance.yahoo.com",
            notes="Live market snapshot assembled from yfinance info, history, and statement tables.",
        )
        price = PriceRecord(
            ticker=ticker,
            market=market,
            currency=currency,
            close=float(latest["Close"]),
            adjusted_close=float(latest.get("Adj Close", latest["Close"])),
            trade_date=trade_date,
            source=source,
        )

        financials = self._financial_snapshot(instrument, ticker, market, currency, source, info)
        profile = self._security_profile(ticker, market, currency, info, financials)
        beneish_inputs = self._beneish_inputs(instrument, profile)
        return DemoInput(
            profile=profile,
            price=price,
            financials=financials,
            beneish_inputs=beneish_inputs,
            wacc=0.10 if not profile.is_financial else 0.09,
            normalized_pe=15.0,
            cycle_position="mid_cycle",
        )

    def _financial_snapshot(
        self,
        instrument: Any,
        ticker: str,
        market: Market,
        currency: Currency,
        source: SourceMeta,
        info: dict[str, Any],
    ) -> FinancialSnapshot:
        balance = _maybe_frame(instrument, "quarterly_balance_sheet", "balance_sheet")
        income, income_periodicity = _maybe_frame_with_periodicity(
            instrument,
            ("quarterly_income_stmt", "quarterly"),
            ("income_stmt", "annual"),
            ("quarterly_financials", "quarterly"),
            ("financials", "annual"),
        )
        cashflow, cashflow_periodicity = _maybe_frame_with_periodicity(
            instrument,
            ("quarterly_cashflow", "quarterly"),
            ("cashflow", "annual"),
            ("cash_flow", "annual"),
        )

        fiscal_period_end = _frame_period_end(income) or _frame_period_end(balance) or source.as_of or date.today()

        revenue = _period_flow_value(income, income_periodicity, "Total Revenue", "Operating Revenue")
        operating_income = _period_flow_value(
            income,
            income_periodicity,
            "Operating Income",
            "Total Operating Income As Reported",
        )
        net_income = _frame_value(
            income,
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income From Continuing Operation Net Minority Interest",
            "Net Income Continuous Operations",
        )
        net_income = _annualize_if_quarterly(net_income, income_periodicity)
        ebit = _period_flow_value(income, income_periodicity, "EBIT", "Ebit", "Operating Income", "Total Operating Income As Reported")
        total_assets = _frame_value(balance, "Total Assets")
        total_liabilities = _frame_value(balance, "Total Liabilities Net Minority Interest", "Total Liabilities")
        total_equity = _frame_value(balance, "Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity")
        current_assets = _frame_value(balance, "Current Assets", "Current Assets Total")
        current_liabilities = _frame_value(balance, "Current Liabilities", "Current Liabilities Total")
        retained_earnings = _frame_value(balance, "Retained Earnings")
        free_cash_flow = _period_flow_value(cashflow, cashflow_periodicity, "Free Cash Flow", "Operating Cash Flow")
        shares = _clean_float(info.get("sharesOutstanding"))
        revenue_growth = _clean_float(info.get("revenueGrowth"))
        market_cap = _clean_float(info.get("marketCap"))
        book_value_per_share = _clean_float(info.get("bookValue"))
        price_to_book = _clean_float(info.get("priceToBook"))
        roe = _clean_float(info.get("returnOnEquity"))
        cost_of_equity = 0.10
        eps = _clean_float(info.get("trailingEps"))
        margin = _clean_float(info.get("operatingMargins"))
        net_margin = _clean_float(info.get("profitMargins"))
        earnings_from_eps = eps * shares if eps is not None and shares is not None else None
        if net_income is None and earnings_from_eps is not None:
            net_income = earnings_from_eps
        normalized_earnings = earnings_from_eps if earnings_from_eps is not None else net_income or operating_income
        normalized_eps = eps
        growth_rate = _conservative_growth_rate(revenue_growth, cost_of_equity)
        working_capital = (
            current_assets - current_liabilities
            if current_assets is not None and current_liabilities is not None
            else None
        )

        return FinancialSnapshot(
            ticker=ticker,
            market=market,
            currency=currency,
            fiscal_period_end=fiscal_period_end,
            source=source,
            revenue=revenue,
            revenue_growth=revenue_growth,
            operating_income=operating_income,
            net_income=net_income,
            normalized_earnings=normalized_earnings,
            free_cash_flow=free_cash_flow,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            current_assets=current_assets,
            current_liabilities=current_liabilities,
            working_capital=working_capital,
            retained_earnings=retained_earnings,
            ebit=ebit,
            sales=revenue,
            market_cap=market_cap,
            shares_outstanding=shares,
            eps=eps,
            normalized_eps=normalized_eps,
            book_value_per_share=book_value_per_share,
            price_to_book=price_to_book,
            roe=roe,
            cost_of_equity=cost_of_equity,
            growth_rate=growth_rate,
            operating_margin=margin,
            net_margin=net_margin,
        )

    def _security_profile(
        self,
        ticker: str,
        market: Market,
        currency: Currency,
        info: dict[str, Any],
        snapshot: FinancialSnapshot,
    ) -> SecurityProfile:
        sector = str(info.get("sector") or "")
        industry = str(info.get("industry") or "")
        text = f"{sector} {industry}".lower()
        revenue_growth = snapshot.revenue_growth or 0.0
        is_financial = any(term in text for term in ("bank", "financial", "insurance", "broker", "securities"))
        is_high_growth = revenue_growth >= 0.20 or any(term in text for term in ("software", "saas", "ai", "cloud"))
        is_cyclical = any(term in text for term in ("semiconductor", "steel", "chemical", "shipping", "commodity", "materials"))
        is_stable_mature = not is_financial and not is_high_growth and not is_cyclical and -0.05 <= revenue_growth <= 0.15
        return SecurityProfile(
            ticker=ticker,
            name=str(info.get("shortName") or info.get("longName") or ticker),
            market=market,
            currency=currency,
            sector=sector,
            industry=industry,
            is_financial=is_financial,
            is_cyclical=is_cyclical,
            is_high_growth=is_high_growth,
            is_stable_mature=is_stable_mature,
            metadata={"source": "yfinance_live"},
        )

    def _beneish_inputs(self, instrument: Any, profile: SecurityProfile) -> BeneishInputs | None:
        try:
            return self._beneish_inputs_inner(instrument, profile)
        except Exception:
            return None

    def _beneish_inputs_inner(self, instrument: Any, profile: SecurityProfile) -> BeneishInputs | None:
        if profile.is_financial:
            return None
        balance = _maybe_frame(instrument, "balance_sheet")
        income = _maybe_frame(instrument, "income_stmt", "financials")
        cashflow = _maybe_frame(instrument, "cashflow", "cash_flow")
        if balance is None or income is None or cashflow is None:
            return None
        periods = _shared_statement_periods(balance, income, cashflow)
        if len(periods) < 2:
            return None
        current, previous = periods[0], periods[1]

        sales_t = _frame_value_for_period(income, current, "Total Revenue", "Operating Revenue")
        sales_p = _frame_value_for_period(income, previous, "Total Revenue", "Operating Revenue")
        receivables_t = _frame_value_for_period(balance, current, "Receivables", "Accounts Receivable", "Gross Accounts Receivable")
        receivables_p = _frame_value_for_period(balance, previous, "Receivables", "Accounts Receivable", "Gross Accounts Receivable")
        cogs_t = _frame_value_for_period(income, current, "Cost Of Revenue", "Reconciled Cost Of Revenue")
        cogs_p = _frame_value_for_period(income, previous, "Cost Of Revenue", "Reconciled Cost Of Revenue")
        current_assets_t = _frame_value_for_period(balance, current, "Current Assets", "Current Assets Total")
        current_assets_p = _frame_value_for_period(balance, previous, "Current Assets", "Current Assets Total")
        total_assets_t = _frame_value_for_period(balance, current, "Total Assets")
        total_assets_p = _frame_value_for_period(balance, previous, "Total Assets")
        ppe_t = _frame_value_for_period(balance, current, "Gross PPE", "Net PPE", "Machinery Furniture Equipment", "Properties")
        ppe_p = _frame_value_for_period(balance, previous, "Gross PPE", "Net PPE", "Machinery Furniture Equipment", "Properties")
        depreciation_t = _frame_value_for_period(cashflow, current, "Depreciation", "Depreciation And Amortization", "Depreciation Amortization Depletion")
        depreciation_p = _frame_value_for_period(cashflow, previous, "Depreciation", "Depreciation And Amortization", "Depreciation Amortization Depletion")
        sga_t = _frame_value_for_period(income, current, "Selling General And Administration", "Selling And Marketing Expense")
        sga_p = _frame_value_for_period(income, previous, "Selling General And Administration", "Selling And Marketing Expense")
        liabilities_t = _frame_value_for_period(balance, current, "Total Liabilities Net Minority Interest", "Total Liabilities")
        liabilities_p = _frame_value_for_period(balance, previous, "Total Liabilities Net Minority Interest", "Total Liabilities")
        income_t = _frame_value_for_period(
            income,
            current,
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income From Continuing Operation Net Minority Interest",
        )
        operating_cash_t = _frame_value_for_period(
            cashflow,
            current,
            "Operating Cash Flow",
            "Cash Flow From Continuing Operating Activities",
        )

        if not all(
            value is not None
            for value in [
                sales_t,
                sales_p,
                receivables_t,
                receivables_p,
                cogs_t,
                cogs_p,
                current_assets_t,
                current_assets_p,
                total_assets_t,
                total_assets_p,
                ppe_t,
                ppe_p,
                depreciation_t,
                depreciation_p,
                sga_t,
                sga_p,
                liabilities_t,
                liabilities_p,
                income_t,
                operating_cash_t,
            ]
        ):
            return None

        dsri = _ratio(receivables_t / sales_t, receivables_p / sales_p)
        gmi = _ratio((sales_p - cogs_p) / sales_p, (sales_t - cogs_t) / sales_t)
        aqi = _ratio(
            1.0 - ((current_assets_t + ppe_t) / total_assets_t),
            1.0 - ((current_assets_p + ppe_p) / total_assets_p),
        )
        sgi = _ratio(sales_t, sales_p)
        dep_rate_t = depreciation_t / (depreciation_t + ppe_t)
        dep_rate_p = depreciation_p / (depreciation_p + ppe_p)
        depi = _ratio(dep_rate_p, dep_rate_t)
        sgai = _ratio(sga_t / sales_t, sga_p / sales_p)
        lvgi = _ratio(liabilities_t / total_assets_t, liabilities_p / total_assets_p)
        tata = (income_t - operating_cash_t) / total_assets_t
        return BeneishInputs(dsri=dsri, gmi=gmi, aqi=aqi, sgi=sgi, depi=depi, sgai=sgai, lvgi=lvgi, tata=tata)


def _infer_market(ticker: str) -> Market:
    symbol = ticker.upper()
    if symbol.endswith(".TW"):
        return Market.TW
    if symbol.endswith(".HK"):
        return Market.HK
    return Market.US


def _infer_currency(raw: Any, market: Market) -> Currency:
    code = str(raw or "").upper()
    if code in {"USD", "HKD", "TWD"}:
        return Currency(code)
    return {
        Market.US: Currency.USD,
        Market.HK: Currency.HKD,
        Market.TW: Currency.TWD,
    }[market]


def _maybe_frame(instrument: Any, *attrs: str) -> Any:
    for attr in attrs:
        value = getattr(instrument, attr, None)
        if value is not None and getattr(value, "empty", True) is False:
            return value
    return None


def _maybe_frame_with_periodicity(
    instrument: Any,
    *attrs: tuple[str, str],
) -> tuple[Any | None, str | None]:
    for attr, periodicity in attrs:
        value = getattr(instrument, attr, None)
        if value is not None and getattr(value, "empty", True) is False:
            return value, periodicity
    return None, None


def _period_flow_value(frame: Any, periodicity: str | None, *candidates: str) -> float | None:
    return _annualize_if_quarterly(_frame_value(frame, *candidates), periodicity)


def _annualize_if_quarterly(value: float | None, periodicity: str | None) -> float | None:
    if value is None:
        return None
    if periodicity == "quarterly":
        return value * 4.0
    return value


def _frame_period_end(frame: Any) -> date | None:
    if frame is None:
        return None
    try:
        column = frame.columns[0]
    except Exception:
        return None
    stamp = getattr(column, "to_pydatetime", lambda: column)()
    return stamp.date() if hasattr(stamp, "date") else None


def _frame_value(frame: Any, *candidates: str) -> float | None:
    if frame is None:
        return None
    normalized_rows = {str(index).strip().lower(): index for index in frame.index}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in normalized_rows:
            try:
                row = frame.loc[normalized_rows[key]]
                if hasattr(row, "tolist"):
                    for item in row.tolist():
                        cleaned = _clean_float(item)
                        if cleaned is not None:
                            return cleaned
                return _clean_float(row.iloc[0])
            except Exception:
                return None
    return None


def _frame_value_for_period(frame: Any, period: Any, *candidates: str) -> float | None:
    if frame is None:
        return None
    normalized_rows = {str(index).strip().lower(): index for index in frame.index}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in normalized_rows and period in frame.columns:
            try:
                return _clean_float(frame.loc[normalized_rows[key], period])
            except Exception:
                return None
    return None


def _clean_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except Exception:
        return None


def _conservative_growth_rate(revenue_growth: float | None, cost_of_equity: float) -> float:
    if revenue_growth is None:
        return min(0.03, cost_of_equity - 0.02)
    return min(max(revenue_growth, 0.0), min(0.04, cost_of_equity - 0.02))


def _shared_statement_periods(*frames: Any) -> list[Any]:
    shared: set[Any] | None = None
    for frame in frames:
        columns = set(getattr(frame, "columns", []))
        shared = columns if shared is None else shared & columns
    return sorted(shared or [], reverse=True)


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0 or not math.isfinite(numerator) or not math.isfinite(denominator):
        raise ZeroDivisionError("invalid Beneish ratio denominator")
    return numerator / denominator
