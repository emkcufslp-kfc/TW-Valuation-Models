"""Deterministic backtest utilities for IMFS 2.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import pstdev
from typing import Mapping, Sequence


ReturnRow = Mapping[str, float]
WeightRow = Mapping[str, float]


@dataclass(frozen=True)
class BacktestConfig:
    execution_lag_periods: int = 1
    transaction_cost_bps: float = 10.0
    initial_cash: float = 1.0
    periods_per_year: int = 12


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: list[float]
    returns: list[float]
    ledger: list[dict[str, float]]
    metrics: dict[str, float]
    benchmark_curve: list[float] = field(default_factory=list)
    benchmark_returns: list[float] = field(default_factory=list)
    benchmark_metrics: dict[str, float] = field(default_factory=dict)
    benchmark_ticker: str | None = None
    period_labels: list[str] = field(default_factory=list)


def run_periodic_backtest(
    returns: Sequence[ReturnRow],
    weights: Sequence[WeightRow],
    config: BacktestConfig | None = None,
) -> BacktestResult:
    cfg = config or BacktestConfig()
    if not returns:
        raise ValueError("returns cannot be empty")
    if not weights:
        raise ValueError("weights cannot be empty")

    tickers = sorted({ticker for row in returns for ticker in row})
    aligned_weights = [_normalize_weights(_weight_for_period(weights, i, tickers)) for i in range(len(returns))]
    if cfg.execution_lag_periods > 0:
        zero = {ticker: 0.0 for ticker in tickers}
        aligned_weights = [zero.copy()] * cfg.execution_lag_periods + aligned_weights
        aligned_weights = aligned_weights[: len(returns)]

    previous_weights = {ticker: 0.0 for ticker in tickers}
    equity = cfg.initial_cash
    equity_curve: list[float] = []
    portfolio_returns: list[float] = []
    ledger: list[dict[str, float]] = []

    for i, return_row in enumerate(returns):
        weight_row = aligned_weights[i]
        turnover = sum(abs(weight_row.get(ticker, 0.0) - previous_weights.get(ticker, 0.0)) for ticker in tickers)
        transaction_cost = turnover * (cfg.transaction_cost_bps / 10000.0)
        gross_return = sum(return_row.get(ticker, 0.0) * weight_row.get(ticker, 0.0) for ticker in tickers)
        net_return = gross_return - transaction_cost
        equity *= 1.0 + net_return
        equity_curve.append(equity)
        portfolio_returns.append(net_return)
        ledger.append(
            {
                "period": float(i),
                "portfolio_return": net_return,
                "turnover": turnover,
                "transaction_cost": transaction_cost,
                "equity": equity,
            }
        )
        previous_weights = weight_row

    return BacktestResult(
        equity_curve=equity_curve,
        returns=portfolio_returns,
        ledger=ledger,
        metrics=calculate_metrics(portfolio_returns, equity_curve, ledger, cfg.periods_per_year),
    )


def calculate_metrics(
    returns: Sequence[float],
    equity_curve: Sequence[float],
    ledger: Sequence[Mapping[str, float]],
    periods_per_year: int = 12,
) -> dict[str, float]:
    if not returns or not equity_curve:
        raise ValueError("returns and equity_curve are required")
    start_equity = 1.0
    end_equity = equity_curve[-1]
    total_return = end_equity / start_equity - 1.0
    years = max(len(returns) / periods_per_year, 1 / periods_per_year)
    cagr = (end_equity / start_equity) ** (1.0 / years) - 1.0
    volatility = pstdev(returns) * (periods_per_year ** 0.5) if len(returns) > 1 else 0.0
    downside_returns = [value for value in returns if value < 0]
    downside = pstdev(downside_returns) * (periods_per_year ** 0.5) if len(downside_returns) > 1 else 0.0
    sharpe = cagr / volatility if volatility else 0.0
    sortino = cagr / downside if downside else 0.0
    max_drawdown = _max_drawdown(equity_curve)
    calmar = cagr / abs(max_drawdown) if max_drawdown < 0 else 0.0
    win_rate = sum(1 for value in returns if value > 0) / len(returns)
    average_turnover = sum(row["turnover"] for row in ledger) / len(ledger)
    transaction_cost_impact = sum(row["transaction_cost"] for row in ledger)
    return {
        "total_return": total_return,
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "average_turnover": average_turnover,
        "transaction_cost_impact": transaction_cost_impact,
    }


def _weight_for_period(weights: Sequence[WeightRow], index: int, tickers: Sequence[str]) -> dict[str, float]:
    source = weights[min(index, len(weights) - 1)]
    return {ticker: float(source.get(ticker, 0.0)) for ticker in tickers}


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(abs(value) for value in weights.values())
    if total <= 1.0:
        return weights
    return {ticker: value / total for ticker, value in weights.items()}


def _max_drawdown(equity_curve: Sequence[float]) -> float:
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        drawdown = value / peak - 1.0
        max_dd = min(max_dd, drawdown)
    return max_dd
