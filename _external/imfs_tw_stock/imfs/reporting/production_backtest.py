"""Production backtest helpers using aligned historical price snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
from typing import Protocol

from imfs.backtest import BacktestConfig, BacktestResult, calculate_metrics, run_periodic_backtest
from imfs.decision import Verdict
from imfs.reporting.demo_pipeline import DemoAnalysis, rank_analyses


@dataclass(frozen=True)
class HistoricalPricePoint:
    as_of: date
    close: float


class HistoricalPriceProvider(Protocol):
    def fetch_history(self, ticker: str, start: date, end: date) -> list[HistoricalPricePoint]:
        ...


def run_production_backtest(
    analyses: list[DemoAnalysis],
    *,
    as_of: date | None = None,
    lookback_months: int = 12,
    benchmark_ticker: str = "SPY",
    provider: HistoricalPriceProvider | None = None,
) -> BacktestResult:
    if not analyses:
        raise ValueError("analyses cannot be empty")
    if lookback_months < 2:
        raise ValueError("lookback_months must be at least 2")

    effective_as_of = as_of or date.today()
    history_provider = provider or YFinanceHistoryProvider()
    ranked = rank_analyses(analyses)
    top = _selected_holdings(ranked)
    tickers = [analysis.profile.ticker for analysis in top]
    start_date = effective_as_of - timedelta(days=lookback_months * 35)

    histories = {
        ticker: history_provider.fetch_history(ticker, start_date, effective_as_of)
        for ticker in [*tickers, benchmark_ticker]
    }
    price_maps = {ticker: _month_end_price_map(points) for ticker, points in histories.items()}
    period_ends = _shared_period_labels(price_maps, tickers, benchmark_ticker, lookback_months)
    if len(period_ends) < 2:
        raise ValueError("insufficient shared monthly price history for production backtest")

    weights = [{ticker: 1.0 / len(tickers) for ticker in tickers} for _ in range(len(period_ends) - 1)]
    returns = []
    benchmark_returns = []
    benchmark_rows = []
    benchmark_curve = []
    benchmark_equity = 1.0

    for index in range(1, len(period_ends)):
        previous = period_ends[index - 1]
        current = period_ends[index]
        return_row = {
            ticker: price_maps[ticker][current] / price_maps[ticker][previous] - 1.0
            for ticker in tickers
        }
        benchmark_return = (
            price_maps[benchmark_ticker][current] / price_maps[benchmark_ticker][previous] - 1.0
        )
        returns.append(return_row)
        benchmark_returns.append(benchmark_return)
        benchmark_equity *= 1.0 + benchmark_return
        benchmark_curve.append(benchmark_equity)
        benchmark_rows.append({benchmark_ticker: benchmark_return})

    result = run_periodic_backtest(
        returns,
        weights,
        BacktestConfig(execution_lag_periods=1, transaction_cost_bps=10.0, periods_per_year=12),
    )
    period_labels = [value.isoformat() for value in period_ends[1:]]
    benchmark_metrics = calculate_metrics(benchmark_returns, benchmark_curve, _benchmark_ledger(benchmark_returns, benchmark_curve), 12)
    ledger = []
    for label, row in zip(period_labels, result.ledger):
        enriched = dict(row)
        enriched["period_end"] = label
        ledger.append(enriched)
    return BacktestResult(
        equity_curve=result.equity_curve,
        returns=result.returns,
        ledger=ledger,
        metrics=result.metrics,
        benchmark_curve=benchmark_curve,
        benchmark_returns=benchmark_returns,
        benchmark_metrics=benchmark_metrics,
        benchmark_ticker=benchmark_ticker,
        period_labels=period_labels,
    )


class YFinanceHistoryProvider:
    def fetch_history(self, ticker: str, start: date, end: date) -> list[HistoricalPricePoint]:
        try:
            import yfinance as yf
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("yfinance is unavailable") from exc

        history = yf.Ticker(ticker).history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
        )
        if history is None or history.empty:
            raise RuntimeError(f"no historical prices returned for {ticker}")
        points: list[HistoricalPricePoint] = []
        for stamp, row in history.iterrows():
            point_date = stamp.date()
            close = float(row.get("Adj Close", row["Close"]))
            if not math.isfinite(close) or close <= 0:
                continue
            points.append(HistoricalPricePoint(as_of=point_date, close=close))
        if not points:
            raise RuntimeError(f"no usable historical prices returned for {ticker}")
        return points


def _selected_holdings(ranked: list[tuple[int, DemoAnalysis]]) -> list[DemoAnalysis]:
    eligible = [analysis for _, analysis in ranked if analysis.decision.verdict in {Verdict.BUY, Verdict.HOLD}]
    if not eligible:
        eligible = [analysis for _, analysis in ranked[: min(3, len(ranked))]]
    return eligible[: min(3, len(eligible))]


def _month_end_price_map(points: list[HistoricalPricePoint]) -> dict[date, float]:
    by_month: dict[tuple[int, int], HistoricalPricePoint] = {}
    for point in points:
        key = (point.as_of.year, point.as_of.month)
        previous = by_month.get(key)
        if previous is None or point.as_of > previous.as_of:
            by_month[key] = point
    return {point.as_of: point.close for point in by_month.values()}


def _shared_period_labels(
    price_maps: dict[str, dict[date, float]],
    tickers: list[str],
    benchmark_ticker: str,
    lookback_months: int,
) -> list[date]:
    shared_dates: set[date] | None = None
    for ticker in [*tickers, benchmark_ticker]:
        dates = set(price_maps[ticker].keys())
        shared_dates = dates if shared_dates is None else shared_dates & dates
    ordered = sorted(shared_dates or [])
    return ordered[-lookback_months:]


def _benchmark_ledger(returns: list[float], equity_curve: list[float]) -> list[dict[str, float]]:
    ledger: list[dict[str, float]] = []
    for index, (period_return, equity) in enumerate(zip(returns, equity_curve)):
        ledger.append(
            {
                "period": float(index),
                "portfolio_return": period_return,
                "turnover": 0.0,
                "transaction_cost": 0.0,
                "equity": equity,
            }
        )
    return ledger
