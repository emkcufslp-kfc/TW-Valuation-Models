from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .config import WorkspacePaths
from .dataset import (
    build_single_ticker_dataset,
    build_top100_dataset,
    load_top100_dataset,
    read_annual_financials,
    read_price_history,
    read_profile,
    read_quarterly_financials,
)
from .models.buffett_dcf import BuffettStock, run_buffett_dcf
from .models.buffett_three import run_buffett_three_valuation
from .source_bridge import import_imfs_modules, import_tw_buffett_quant_modules, import_tw_hybrid_modules


def _load_optional_external_modules(paths: WorkspacePaths) -> tuple[dict[str, object] | None, dict[str, object] | None, dict[str, object] | None, dict[str, str]]:
    availability: dict[str, str] = {}
    imfs_modules = _safe_import_bundle("imfs", import_imfs_modules, paths, availability)
    quant_modules = _safe_import_bundle("tw_buffett_quant", import_tw_buffett_quant_modules, paths, availability)
    hybrid_modules = _safe_import_bundle("tw_hybrid", import_tw_hybrid_modules, paths, availability)
    return imfs_modules, quant_modules, hybrid_modules, availability


def _safe_import_bundle(
    key: str,
    loader,
    paths: WorkspacePaths,
    availability: dict[str, str],
) -> dict[str, object] | None:
    try:
        bundle = loader(paths)
        availability[key] = "ready"
        return bundle
    except Exception as exc:
        availability[key] = f"{type(exc).__name__}: {exc}"
        return None


def build_all_model_results(paths: WorkspacePaths, top_n: int = 100) -> dict[str, object]:
    dataset_root = paths.artifacts_root / "datasets" / "top100"
    required_dataset_files = [
        dataset_root / "dataset_summary.json",
        dataset_root / "buffett3_valuation_snapshot.csv",
        dataset_root / "buffett3_dividend_history.csv",
        dataset_root / "buffett3_monthly_revenue_history.csv",
        dataset_root / "buffett3_annual_fundamentals.csv",
        dataset_root / "buffett3_quarterly_fundamentals.csv",
    ]
    if any(not path.exists() for path in required_dataset_files):
        build_top100_dataset(paths, top_n=top_n)

    dataset = load_top100_dataset(paths)
    dataset_root = dataset["dataset_root"]
    universe_df: pd.DataFrame = dataset["top100_universe"]
    valuation_df: pd.DataFrame = dataset["top100_valuation"]
    fundamentals_snapshot_df: pd.DataFrame = dataset["top100_fundamentals_snapshot"]
    monthly_revenue_df: pd.DataFrame = dataset["monthly_revenue"]
    buffett3_valuation_df = pd.read_csv(dataset_root / "buffett3_valuation_snapshot.csv")
    buffett3_dividend_df = pd.read_csv(dataset_root / "buffett3_dividend_history.csv")
    buffett3_monthly_revenue_df = pd.read_csv(dataset_root / "buffett3_monthly_revenue_history.csv")
    buffett3_annual_df = pd.read_csv(dataset_root / "buffett3_annual_fundamentals.csv")
    buffett3_quarterly_df = pd.read_csv(dataset_root / "buffett3_quarterly_fundamentals.csv")

    imfs_modules, quant_modules, hybrid_modules, external_availability = _load_optional_external_modules(paths)

    routing = imfs_modules["routing"] if imfs_modules else None
    models = imfs_modules["models"] if imfs_modules else None
    engine = imfs_modules["engine"] if imfs_modules else None
    strict_mode = quant_modules["strict_mode"] if quant_modules else None
    criteria_mod = quant_modules["criteria"] if quant_modules else None
    criteria = criteria_mod.get_default_filter_criteria() if criteria_mod else {}

    taiex_df = pd.read_csv(dataset_root / "TAIEX.csv")
    taiex_df["Date"] = pd.to_datetime(taiex_df["Date"], errors="coerce")
    taiex_df = taiex_df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    valuation_df = valuation_df.copy()
    valuation_df["ticker"] = valuation_df["ticker"].astype(str)
    valuation_lookup = valuation_df.set_index("ticker").to_dict("index")

    fundamentals_snapshot_df = fundamentals_snapshot_df.copy()
    fundamentals_snapshot_df["ticker"] = fundamentals_snapshot_df["ticker"].astype(str)
    fundamentals_lookup = fundamentals_snapshot_df.set_index("ticker").to_dict("index")

    universe_df = universe_df.copy()
    universe_df["ticker"] = universe_df["ticker"].astype(str)
    universe_lookup = universe_df.set_index("ticker").to_dict("index")

    rows = []
    buffett3_payload_root = paths.artifacts_root / "results" / "buffett3_payloads"
    buffett3_payload_root.mkdir(parents=True, exist_ok=True)
    for ticker in universe_df["ticker"].tolist():
        price_df = read_price_history(dataset_root, ticker)
        annual_df = read_annual_financials(dataset_root, ticker)
        quarterly_df = read_quarterly_financials(dataset_root, ticker)
        profile = read_profile(dataset_root, ticker)
        universe_row = universe_lookup.get(ticker, {})
        valuation_row = valuation_lookup.get(ticker, {})
        fundamentals_row = fundamentals_lookup.get(ticker, {})

        buffett_stock = _make_buffett_stock(
            ticker=ticker,
            universe_row=universe_row,
            valuation_row=valuation_row,
            profile=profile,
            annual_df=annual_df,
            quarterly_df=quarterly_df,
        )
        buffett_v1 = run_buffett_dcf(buffett_stock, valuation_mode="avgEps")
        buffett_v2 = run_buffett_dcf(buffett_stock, valuation_mode="fcfps")

        imfs_result = (
            _run_imfs_for_ticker(
                ticker=ticker,
                universe_row=universe_row,
                valuation_row=valuation_row,
                fundamentals_row=fundamentals_row,
                annual_df=annual_df,
                quarterly_df=quarterly_df,
                price_df=price_df,
                models_module=models,
                routing_module=routing,
                engine_module=engine,
            )
            if imfs_modules
            else _unavailable_imfs_result(external_availability.get("imfs", "not available"))
        )

        quant_result = (
            _run_tw_buffett_quant_for_ticker(
                ticker=ticker,
                sector=profile.get("sector") or universe_row.get("industry") or "",
                valuation_row=valuation_row,
                annual_df=annual_df,
                monthly_revenue_df=monthly_revenue_df,
                price_df=price_df,
                taiex_df=taiex_df,
                strict_mode_module=strict_mode,
                criteria=criteria,
            )
            if quant_modules
            else _unavailable_quant_result(external_availability.get("tw_buffett_quant", "not available"))
        )

        hybrid_result = (
            _run_tw_hybrid_for_ticker(
                ticker=ticker,
                price_df=price_df,
                strategy_module=hybrid_modules["strategy"],
            )
            if hybrid_modules
            else _unavailable_hybrid_result(external_availability.get("tw_hybrid", "not available"))
        )
        buffett3_result = run_buffett_three_valuation(
            ticker=ticker,
            company_name=str(universe_row.get("company_name") or profile.get("longName") or ticker),
            industry=str(universe_row.get("industry") or profile.get("industry") or profile.get("sector") or ""),
            current_price=buffett_stock.price,
            annual_df=buffett3_annual_df[buffett3_annual_df["ticker"].astype(str) == ticker].copy(),
            quarterly_df=buffett3_quarterly_df[
                buffett3_quarterly_df["ticker"].astype(str) == ticker
            ].copy(),
            valuation_df=buffett3_valuation_df[
                buffett3_valuation_df["ticker"].astype(str) == ticker
            ].copy(),
            dividend_df=buffett3_dividend_df[
                buffett3_dividend_df["ticker"].astype(str) == ticker
            ].copy(),
            monthly_revenue_df=buffett3_monthly_revenue_df[
                buffett3_monthly_revenue_df["stock_id"].astype(str) == ticker
            ].copy(),
            taiex_df=taiex_df.copy(),
        )
        (buffett3_payload_root / f"{ticker}.json").write_text(
            json.dumps(buffett3_result, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        rows.append(
            {
                "ticker": ticker,
                "name": universe_row.get("company_name") or profile.get("longName") or ticker,
                "industry": universe_row.get("industry") or profile.get("industry") or "",
                "market_cap": fundamentals_row.get("market_cap"),
                "price": buffett_stock.price,
                "buffett_v1_intrinsic": buffett_v1["intrinsic_value"],
                "buffett_v1_mos": buffett_v1["margin_of_safety_pct"],
                "buffett_v1_signal": buffett_v1["signal"],
                "buffett_v2_intrinsic": buffett_v2["intrinsic_value"],
                "buffett_v2_mos": buffett_v2["margin_of_safety_pct"],
                "buffett_v2_signal": buffett_v2["signal"],
                "buffett3_intrinsic": buffett3_result["final_fair_value_per_share"],
                "buffett3_mos": buffett3_result["upside_downside_pct"],
                "buffett3_signal": buffett3_result["signal"],
                "buffett3_type": buffett3_result["classification"],
                "buffett3_quality_flags": json.dumps(
                    {
                        "data_quality_flags": buffett3_result["data_quality_flags"],
                        "manual_review_flags": buffett3_result["manual_review_flags"],
                    },
                    ensure_ascii=False,
                ),
                "imfs_model": imfs_result["model"],
                "imfs_route": imfs_result["route"],
                "imfs_intrinsic": imfs_result["intrinsic_value"],
                "imfs_gap_pct": imfs_result["gap_pct"],
                "imfs_signal": imfs_result["signal"],
                "imfs_est_revenue_growth_pct": imfs_result["estimated_revenue_growth_pct"],
                "imfs_est_profit_margin_pct": imfs_result["estimated_profit_margin_pct"],
                "imfs_quality_score": imfs_result["quality_score"],
                "imfs_premium_eligible": imfs_result["premium_eligible"],
                "imfs_justified_pe": imfs_result["justified_pe"],
                "imfs_projected_eps": imfs_result["projected_eps"],
                "quant_score": quant_result["composite_score"],
                "quant_action": quant_result["action_plan"],
                "quant_signal": quant_result["river_signal"],
                "hybrid_target": hybrid_result["ens_price"],
                "hybrid_return_pct": hybrid_result["ens_ret_pct"],
                "hybrid_signal": hybrid_result["signal"],
                "data_warnings": json.dumps(
                    {
                        "buffett_v1": buffett_v1["warnings"],
                        "buffett_v2": buffett_v2["warnings"],
                        "buffett3": buffett3_result["warnings"],
                        "imfs": imfs_result["warnings"],
                        "quant": quant_result["warnings"],
                        "hybrid": hybrid_result["warnings"],
                    },
                    ensure_ascii=False,
                ),
            }
        )

    results_df = pd.DataFrame(rows)
    output_root = paths.artifacts_root / "results"
    output_root.mkdir(parents=True, exist_ok=True)
    results_path = output_root / "top100_model_results.csv"
    results_df.to_csv(results_path, index=False, encoding="utf-8")
    summary = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "result_count": len(results_df),
        "results_path": str(results_path),
        "model_logic_sources": {
            "buffett_v1": "formula_port_from_original_buffett_stock_tw_src_dcf_engine_and_useDCF",
            "buffett_v2": "formula_port_from_original_buffett_stock_tw_src_dcf_engine_and_useDCF",
            "buffett3": "workspace_buffett3_v1_rule_based_engine_using_buffett3_official_tables",
            "imfs": "direct_original_imfs_route_classifier_and_valuation_engine",
            "tw_buffett_quant": "direct_original_strict_mode_engine_with_integrated_inputs",
            "tw_hybrid": "direct_original_strategy_compute_technical_features_and_EnsembleValuationModel",
        },
        "external_model_availability": external_availability,
    }
    (output_root / "top100_model_results_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def build_single_ticker_model_result(paths: WorkspacePaths, ticker: str) -> dict[str, object]:
    ticker = str(ticker).strip()
    dataset_summary = build_single_ticker_dataset(paths, ticker)
    dataset_root = Path(dataset_summary["dataset_root"])

    price_df = read_price_history(dataset_root, ticker)
    annual_df = read_annual_financials(dataset_root, ticker)
    quarterly_df = read_quarterly_financials(dataset_root, ticker)
    profile = read_profile(dataset_root, ticker)

    universe_df = pd.read_csv(dataset_root / "top100_universe.csv")
    valuation_df = pd.read_csv(dataset_root / "top100_valuation_snapshot.csv")
    fundamentals_snapshot_df = pd.read_csv(dataset_root / "top100_fundamentals_snapshot.csv")
    monthly_revenue_df = pd.read_csv(dataset_root / "monthly_revenue_history.csv")
    buffett3_valuation_df = pd.read_csv(dataset_root / "buffett3_valuation_snapshot.csv")
    buffett3_dividend_df = pd.read_csv(dataset_root / "buffett3_dividend_history.csv")
    buffett3_monthly_revenue_df = pd.read_csv(dataset_root / "buffett3_monthly_revenue_history.csv")
    buffett3_annual_df = pd.read_csv(dataset_root / "buffett3_annual_fundamentals.csv")
    buffett3_quarterly_df = pd.read_csv(dataset_root / "buffett3_quarterly_fundamentals.csv")
    taiex_df = pd.read_csv(dataset_root / "TAIEX.csv")
    taiex_df["Date"] = pd.to_datetime(taiex_df["Date"], errors="coerce")
    taiex_df = taiex_df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    universe_df["ticker"] = universe_df["ticker"].astype(str)
    valuation_df["ticker"] = valuation_df["ticker"].astype(str)
    fundamentals_snapshot_df["ticker"] = fundamentals_snapshot_df["ticker"].astype(str)
    universe_row = universe_df[universe_df["ticker"] == ticker].iloc[0].to_dict()
    valuation_row = (
        valuation_df[valuation_df["ticker"] == ticker].iloc[0].to_dict()
        if not valuation_df[valuation_df["ticker"] == ticker].empty
        else {}
    )
    fundamentals_row = (
        fundamentals_snapshot_df[fundamentals_snapshot_df["ticker"] == ticker].iloc[0].to_dict()
        if not fundamentals_snapshot_df[fundamentals_snapshot_df["ticker"] == ticker].empty
        else {}
    )

    imfs_modules, quant_modules, hybrid_modules, external_availability = _load_optional_external_modules(paths)
    routing = imfs_modules["routing"] if imfs_modules else None
    models = imfs_modules["models"] if imfs_modules else None
    engine = imfs_modules["engine"] if imfs_modules else None
    strict_mode = quant_modules["strict_mode"] if quant_modules else None
    criteria_mod = quant_modules["criteria"] if quant_modules else None
    criteria = criteria_mod.get_default_filter_criteria() if criteria_mod else {}

    buffett_stock = _make_buffett_stock(
        ticker=ticker,
        universe_row=universe_row,
        valuation_row=valuation_row,
        profile=profile,
        annual_df=annual_df,
        quarterly_df=quarterly_df,
    )
    buffett_v1 = run_buffett_dcf(buffett_stock, valuation_mode="avgEps")
    buffett_v2 = run_buffett_dcf(buffett_stock, valuation_mode="fcfps")
    imfs_result = (
        _run_imfs_for_ticker(
            ticker=ticker,
            universe_row=universe_row,
            valuation_row=valuation_row,
            fundamentals_row=fundamentals_row,
            annual_df=annual_df,
            quarterly_df=quarterly_df,
            price_df=price_df,
            models_module=models,
            routing_module=routing,
            engine_module=engine,
        )
        if imfs_modules
        else _unavailable_imfs_result(external_availability.get("imfs", "not available"))
    )
    quant_result = (
        _run_tw_buffett_quant_for_ticker(
            ticker=ticker,
            sector=profile.get("sector") or universe_row.get("industry") or "",
            valuation_row=valuation_row,
            annual_df=annual_df,
            monthly_revenue_df=monthly_revenue_df,
            price_df=price_df,
            taiex_df=taiex_df,
            strict_mode_module=strict_mode,
            criteria=criteria,
        )
        if quant_modules
        else _unavailable_quant_result(external_availability.get("tw_buffett_quant", "not available"))
    )
    hybrid_result = (
        _run_tw_hybrid_for_ticker(
            ticker=ticker,
            price_df=price_df,
            strategy_module=hybrid_modules["strategy"],
        )
        if hybrid_modules
        else _unavailable_hybrid_result(external_availability.get("tw_hybrid", "not available"))
    )
    buffett3_result = run_buffett_three_valuation(
        ticker=ticker,
        company_name=str(universe_row.get("company_name") or profile.get("longName") or ticker),
        industry=str(universe_row.get("industry") or profile.get("industry") or profile.get("sector") or ""),
        current_price=buffett_stock.price,
        annual_df=buffett3_annual_df[buffett3_annual_df["ticker"].astype(str) == ticker].copy(),
        quarterly_df=buffett3_quarterly_df[
            buffett3_quarterly_df["ticker"].astype(str) == ticker
        ].copy(),
        valuation_df=buffett3_valuation_df[
            buffett3_valuation_df["ticker"].astype(str) == ticker
        ].copy(),
        dividend_df=buffett3_dividend_df[
            buffett3_dividend_df["ticker"].astype(str) == ticker
        ].copy(),
        monthly_revenue_df=buffett3_monthly_revenue_df[
            buffett3_monthly_revenue_df["stock_id"].astype(str) == ticker
        ].copy(),
        taiex_df=taiex_df.copy(),
    )

    row = {
        "ticker": ticker,
        "name": universe_row.get("company_name") or profile.get("longName") or ticker,
        "industry": universe_row.get("industry") or profile.get("industry") or "",
        "market_cap": fundamentals_row.get("market_cap"),
        "price": buffett_stock.price,
        "buffett_v1_intrinsic": buffett_v1["intrinsic_value"],
        "buffett_v1_mos": buffett_v1["margin_of_safety_pct"],
        "buffett_v1_signal": buffett_v1["signal"],
        "buffett_v2_intrinsic": buffett_v2["intrinsic_value"],
        "buffett_v2_mos": buffett_v2["margin_of_safety_pct"],
        "buffett_v2_signal": buffett_v2["signal"],
        "buffett3_intrinsic": buffett3_result["final_fair_value_per_share"],
        "buffett3_mos": buffett3_result["upside_downside_pct"],
        "buffett3_signal": buffett3_result["signal"],
        "buffett3_type": buffett3_result["classification"],
        "buffett3_quality_flags": json.dumps(
            {
                "data_quality_flags": buffett3_result["data_quality_flags"],
                "manual_review_flags": buffett3_result["manual_review_flags"],
            },
            ensure_ascii=False,
        ),
        "imfs_model": imfs_result["model"],
        "imfs_route": imfs_result["route"],
        "imfs_intrinsic": imfs_result["intrinsic_value"],
        "imfs_gap_pct": imfs_result["gap_pct"],
        "imfs_signal": imfs_result["signal"],
        "imfs_est_revenue_growth_pct": imfs_result["estimated_revenue_growth_pct"],
        "imfs_est_profit_margin_pct": imfs_result["estimated_profit_margin_pct"],
        "imfs_quality_score": imfs_result["quality_score"],
        "imfs_premium_eligible": imfs_result["premium_eligible"],
        "imfs_justified_pe": imfs_result["justified_pe"],
        "imfs_projected_eps": imfs_result["projected_eps"],
        "quant_score": quant_result["composite_score"],
        "quant_action": quant_result["action_plan"],
        "quant_signal": quant_result["river_signal"],
        "hybrid_target": hybrid_result["ens_price"],
        "hybrid_return_pct": hybrid_result["ens_ret_pct"],
        "hybrid_signal": hybrid_result["signal"],
        "data_warnings": json.dumps(
            {
                "buffett_v1": buffett_v1["warnings"],
                "buffett_v2": buffett_v2["warnings"],
                "buffett3": buffett3_result["warnings"],
                "imfs": imfs_result["warnings"],
                "quant": quant_result["warnings"],
                "hybrid": hybrid_result["warnings"],
            },
            ensure_ascii=False,
        ),
        "dataset_root": str(dataset_root),
    }

    paths.on_demand_results_root.mkdir(parents=True, exist_ok=True)
    result_path = paths.on_demand_results_root / f"{ticker}.json"
    result_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "ticker": ticker,
                "dataset_root": str(dataset_root),
                "row": row,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    buffett3_payload_root = paths.artifacts_root / "results" / "buffett3_payloads"
    buffett3_payload_root.mkdir(parents=True, exist_ok=True)
    (buffett3_payload_root / f"{ticker}.json").write_text(
        json.dumps(buffett3_result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "ticker": ticker,
        "dataset_root": str(dataset_root),
        "result_path": str(result_path),
        "buffett3_payload_path": str(buffett3_payload_root / f"{ticker}.json"),
        "row": row,
        "external_model_availability": external_availability,
    }


def _make_buffett_stock(
    *,
    ticker: str,
    universe_row: dict[str, object],
    valuation_row: dict[str, object],
    profile: dict[str, object],
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
) -> BuffettStock:
    annual_df = annual_df.copy()
    quarterly_df = quarterly_df.copy()
    annual_df["eps"] = pd.to_numeric(annual_df.get("eps"), errors="coerce")
    annual_df["free_cash_flow"] = pd.to_numeric(annual_df.get("free_cash_flow"), errors="coerce")
    annual_df["shares_outstanding"] = pd.to_numeric(
        annual_df.get("shares_outstanding"), errors="coerce"
    )
    annual_df["roe"] = pd.to_numeric(annual_df.get("roe"), errors="coerce")
    annual_df["book_value_per_share"] = pd.to_numeric(
        annual_df.get("book_value_per_share"), errors="coerce"
    )
    quarterly_df["free_cash_flow"] = pd.to_numeric(
        quarterly_df.get("free_cash_flow"), errors="coerce"
    )
    quarterly_df["shares_outstanding"] = pd.to_numeric(
        quarterly_df.get("shares_outstanding"), errors="coerce"
    )

    hist_eps = annual_df["eps"].dropna().tail(5).tolist()
    avg_eps = float(pd.Series(hist_eps[-3:]).mean()) if hist_eps else None
    annual_fcf_per_share = (
        annual_df["free_cash_flow"] / annual_df["shares_outstanding"].replace({0: pd.NA})
    ).dropna()
    avg_fcf_per_share = (
        float(annual_fcf_per_share.tail(3).mean()) if not annual_fcf_per_share.empty else None
    )
    quarterly_fcf_per_share = (
        quarterly_df["free_cash_flow"]
        / quarterly_df["shares_outstanding"].replace({0: pd.NA})
    ).dropna()
    fcf_per_share = (
        float(quarterly_fcf_per_share.tail(4).sum())
        if len(quarterly_fcf_per_share) >= 4
        else (float(avg_fcf_per_share) if avg_fcf_per_share is not None else None)
    )

    shares_series = annual_df["shares_outstanding"].dropna()
    share_dilution_rate = 0.0
    if len(shares_series) >= 2 and shares_series.iloc[0] > 0:
        years = max(len(shares_series) - 1, 1)
        share_dilution_rate = ((shares_series.iloc[-1] / shares_series.iloc[0]) ** (1 / years) - 1) * 100

    non_empty_annual = annual_df.dropna(subset=["eps"])
    latest_annual = non_empty_annual.iloc[-1] if not non_empty_annual.empty else None
    latest_book = _safe_float(latest_annual.get("book_value_per_share")) if latest_annual is not None else None
    latest_roe = _safe_float(latest_annual.get("roe")) if latest_annual is not None else None
    latest_fcf = _safe_float(latest_annual.get("free_cash_flow")) if latest_annual is not None else None

    price = _safe_float(profile.get("currentPrice") or profile.get("regularMarketPrice"))
    if price is None:
        price = _safe_float(profile.get("previousClose")) or 0.0

    eps = _safe_float(profile.get("trailingEps"))
    if eps is None and latest_annual is not None:
        eps = _safe_float(latest_annual.get("eps")) or 0.0

    pb = _safe_float(valuation_row.get("pb_ratio")) or _safe_float(profile.get("priceToBook")) or 0.0
    pe = _safe_float(valuation_row.get("pe_ratio")) or _safe_float(profile.get("trailingPE")) or 0.0
    dividend_yield = _safe_float(valuation_row.get("dividend_yield"))
    if dividend_yield is None:
        dy = _safe_float(profile.get("dividendYield"))
        dividend_yield = (dy * 100.0) if dy is not None and dy <= 1 else (dy or 0.0)

    sector = str(profile.get("sector") or universe_row.get("industry") or "")
    current_ratio = _compute_current_ratio(latest_annual)
    if current_ratio == 0.0:
        current_ratio = _safe_float(profile.get("currentRatio")) or 0.0

    debt_to_equity = _compute_debt_to_equity(latest_annual)
    if debt_to_equity == 0.0:
        dte = _safe_float(profile.get("debtToEquity"))
        if dte is not None:
            debt_to_equity = dte / 100.0 if dte > 10 else dte

    return BuffettStock(
        ticker=ticker,
        name=str(universe_row.get("company_name") or profile.get("longName") or ticker),
        sector=sector,
        price=price or 0.0,
        eps=eps or 0.0,
        pe=pe or 0.0,
        pb=pb or 0.0,
        roe=latest_roe or 0.0,
        dividend_yield=dividend_yield or 0.0,
        debt_to_equity=debt_to_equity,
        current_ratio=current_ratio,
        fcf=latest_fcf or 0.0,
        bvps=latest_book or 0.0,
        growth_rate=_compute_growth_rate(annual_df),
        avg_eps=avg_eps,
        fcf_per_share=fcf_per_share,
        avg_fcf_per_share=avg_fcf_per_share,
        historical_eps=[float(x) for x in hist_eps],
        share_dilution_rate=share_dilution_rate,
        avg_roe=float(annual_df["roe"].dropna().tail(3).mean()) if not annual_df["roe"].dropna().empty else None,
    )


def _run_imfs_for_ticker(
    *,
    ticker: str,
    universe_row: dict[str, object],
    valuation_row: dict[str, object],
    fundamentals_row: dict[str, object],
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
    price_df: pd.DataFrame,
    models_module,
    routing_module,
    engine_module,
) -> dict[str, object]:
    annual_df = annual_df.copy()
    annual_df["date"] = pd.to_datetime(annual_df["date"], errors="coerce")
    latest_frame = annual_df.dropna(subset=["date"]).sort_values("date")
    latest = latest_frame.iloc[-1] if not latest_frame.empty else None
    if "Close" not in price_df.columns or "Date" not in price_df.columns:
        return _unavailable_imfs_result("missing Date/Close columns in price history")
    if pd.to_numeric(price_df["Close"], errors="coerce").dropna().empty:
        return _unavailable_imfs_result("no valid close prices in price history")
    if pd.to_datetime(price_df["Date"], errors="coerce").dropna().empty:
        return _unavailable_imfs_result("no valid dates in price history")
    latest_price = _latest_close(price_df)
    latest_date = _latest_date(price_df)
    SourceMeta = models_module.SourceMeta
    SecurityProfile = models_module.SecurityProfile
    FinancialSnapshot = models_module.FinancialSnapshot
    PriceRecord = models_module.PriceRecord
    Market = models_module.Market
    Currency = models_module.Currency

    industry = str(universe_row.get("industry") or "")
    source = SourceMeta(source="integrated_top100_dataset", as_of=date.today(), retrieved_at=datetime.now(UTC))
    profile = SecurityProfile(
        ticker=ticker,
        name=str(universe_row.get("company_name") or ticker),
        market=Market.TW,
        currency=Currency.TWD,
        sector=industry,
        industry=industry,
        is_financial=("金融" in industry) or ("銀行" in industry),
        is_cyclical=("景氣" in industry) or ("航運" in industry) or ("鋼鐵" in industry),
        is_high_growth=("半導體" in industry) or ("電子" in industry),
        is_stable_mature=("金融" not in industry) and ("生技" not in industry),
    )
    roe_pct = _safe_float(latest.get("roe")) if latest is not None else None
    growth_rate = _compute_growth_rate(annual_df) / 100.0 if not annual_df.empty else 0.02
    snapshot = FinancialSnapshot(
        ticker=ticker,
        market=Market.TW,
        currency=Currency.TWD,
        fiscal_period_end=(latest["date"].date() if latest is not None else date.today()),
        source=source,
        revenue=_safe_float(latest.get("revenue")) if latest is not None else None,
        revenue_growth=growth_rate,
        operating_income=_safe_float(latest.get("operating_income")) if latest is not None else None,
        net_income=_safe_float(latest.get("net_income")) if latest is not None else None,
        normalized_earnings=_safe_float(latest.get("net_income")) if latest is not None else None,
        free_cash_flow=_safe_float(latest.get("free_cash_flow")) if latest is not None else None,
        total_assets=_safe_float(latest.get("total_assets")) if latest is not None else None,
        total_liabilities=_safe_float(latest.get("total_liabilities")) if latest is not None else None,
        total_equity=_safe_float(latest.get("equity")) if latest is not None else None,
        current_assets=_safe_float(latest.get("current_assets")) if latest is not None else None,
        current_liabilities=_safe_float(latest.get("current_liabilities")) if latest is not None else None,
        ebit=_safe_float(latest.get("operating_income")) if latest is not None else None,
        sales=_safe_float(latest.get("revenue")) if latest is not None else None,
        market_cap=_safe_float(fundamentals_row.get("market_cap")),
        shares_outstanding=_safe_float(latest.get("shares_outstanding")) if latest is not None else None,
        eps=_safe_float(latest.get("eps")) if latest is not None else None,
        normalized_eps=_safe_float(latest.get("eps")) if latest is not None else None,
        book_value_per_share=_safe_float(latest.get("book_value_per_share")) if latest is not None else None,
        price_to_book=_safe_float(valuation_row.get("pb_ratio")),
        roe=(roe_pct / 100.0) if roe_pct is not None else None,
        cost_of_equity=0.10,
        growth_rate=growth_rate,
        operating_margin=_safe_ratio(
            _safe_float(latest.get("operating_income")),
            _safe_float(latest.get("revenue")),
        )
        if latest is not None
        else None,
        net_margin=_safe_ratio(
            _safe_float(latest.get("net_income")),
            _safe_float(latest.get("revenue")),
        )
        if latest is not None
        else None,
    )
    price = PriceRecord(
        ticker=ticker,
        market=Market.TW,
        currency=Currency.TWD,
        close=latest_price,
        trade_date=latest_date,
        source=source,
    )
    route_decision = routing_module.classify_security(profile, snapshot)
    result = engine_module.value_by_route(route_decision, snapshot, price)
    bridge = _build_imfs_rule40_bridge(snapshot, latest_price, annual_df, quarterly_df) if result.route.value == "B" else {}
    intrinsic_value = result.intrinsic_value_per_share
    gap_pct = result.valuation_gap_pct
    warnings = list(result.warnings)
    if intrinsic_value is None and bridge.get("intrinsic_value") is not None:
        intrinsic_value = bridge["intrinsic_value"]
        gap_pct = bridge["gap_pct"]
        warnings.extend(bridge.get("warnings", []))

    signal = "usable" if intrinsic_value is not None else "warning"
    if gap_pct is not None:
        if gap_pct >= 0.3:
            signal = "deep_discount"
        elif gap_pct >= 0.1:
            signal = "discount"
        else:
            signal = "fair_or_rich"
    return {
        "route": result.route.value,
        "model": result.model,
        "intrinsic_value": intrinsic_value,
        "gap_pct": gap_pct,
        "signal": signal,
        "warnings": warnings,
        "estimated_revenue_growth_pct": bridge.get("estimated_revenue_growth_pct"),
        "estimated_profit_margin_pct": bridge.get("estimated_profit_margin_pct"),
        "quality_score": bridge.get("quality_score"),
        "premium_eligible": bridge.get("premium_eligible"),
        "justified_pe": bridge.get("justified_pe"),
        "projected_eps": bridge.get("projected_eps"),
    }


def _unavailable_imfs_result(reason: str) -> dict[str, object]:
    return {
        "route": None,
        "model": "unavailable",
        "intrinsic_value": None,
        "gap_pct": None,
        "signal": "unavailable",
        "warnings": [f"imfs unavailable: {reason}"],
        "estimated_revenue_growth_pct": None,
        "estimated_profit_margin_pct": None,
        "quality_score": None,
        "premium_eligible": None,
        "justified_pe": None,
        "projected_eps": None,
    }


def _run_tw_buffett_quant_for_ticker(
    *,
    ticker: str,
    sector: str,
    valuation_row: dict[str, object],
    annual_df: pd.DataFrame,
    monthly_revenue_df: pd.DataFrame,
    price_df: pd.DataFrame,
    taiex_df: pd.DataFrame,
    strict_mode_module,
    criteria: dict[str, object],
) -> dict[str, object]:
    financials_df = pd.DataFrame()
    if not annual_df.empty:
        financials_df = pd.DataFrame(
            {
                "ROE": pd.to_numeric(annual_df["roe"], errors="coerce"),
                "OperatingCashFlow": pd.to_numeric(annual_df["operating_cash_flow"], errors="coerce"),
                "CapitalExpenditure": pd.to_numeric(annual_df["capital_expenditure"], errors="coerce"),
                "FCF": pd.to_numeric(annual_df["free_cash_flow"], errors="coerce"),
                "NetIncome": pd.to_numeric(annual_df["net_income"], errors="coerce"),
            }
        ).dropna(how="all")

    valuation_history_df = pd.DataFrame()
    if not annual_df.empty:
        annual_df = annual_df.copy()
        annual_df["date"] = pd.to_datetime(annual_df["date"], errors="coerce")
        shares = pd.to_numeric(annual_df["shares_outstanding"], errors="coerce")
        annual_df["close"] = annual_df["date"].apply(lambda dt: _price_on_or_after(price_df, dt))
        annual_df["PE"] = annual_df["close"] * shares / pd.to_numeric(
            annual_df["net_income"], errors="coerce"
        )
        annual_df["PB"] = annual_df["close"] * shares / pd.to_numeric(
            annual_df["equity"], errors="coerce"
        )
        valuation_history_df = annual_df[["date", "PE", "PB"]].dropna(how="all")

    revenue_metrics = _build_revenue_metrics(ticker, monthly_revenue_df)
    latest_pe = _safe_float(valuation_row.get("pe_ratio"))
    latest_pb = _safe_float(valuation_row.get("pb_ratio"))
    latest_yield = _safe_float(valuation_row.get("dividend_yield"))
    daily_stats_df = pd.DataFrame(
        [{"stock_id": ticker, "PE": latest_pe, "PB": latest_pb, "Yield": latest_yield}]
    ).set_index("stock_id")

    eval_result = strict_mode_module.evaluate_stock_strict_mode(
        ticker=ticker,
        sector=sector,
        financials_df=financials_df if not financials_df.empty else pd.DataFrame(columns=["ROE"]),
        valuation_df=valuation_history_df,
        daily_stats_df=daily_stats_df,
        revenue_metrics=revenue_metrics,
        price_df=price_df,
        benchmark_df=taiex_df,
        criteria=criteria,
    )
    return {
        "composite_score": eval_result["composite_score"],
        "action_plan": eval_result["action_plan"],
        "river_signal": eval_result["river_signal"],
        "warnings": [],
    }


def _unavailable_quant_result(reason: str) -> dict[str, object]:
    return {
        "composite_score": None,
        "action_plan": "unavailable",
        "river_signal": "unavailable",
        "warnings": [f"tw buffett quant unavailable: {reason}"],
    }


def _run_tw_hybrid_for_ticker(*, ticker: str, price_df: pd.DataFrame, strategy_module) -> dict[str, object]:
    feature_df = price_df.copy()
    feature_df["Date"] = pd.to_datetime(feature_df["Date"], errors="coerce")
    feature_df = feature_df.dropna(subset=["Date"]).set_index("Date").sort_index()
    feature_df = strategy_module.compute_technical_features(feature_df)
    feature_cols = list(strategy_module.FEATURE_COLS)
    train_feat = feature_df.dropna(subset=feature_cols + ["fwd_ret_20d"])
    if train_feat.empty or len(train_feat) < 80:
        return {
            "ens_price": None,
            "ens_ret_pct": None,
            "signal": "insufficient_data",
            "warnings": ["insufficient history for TW hybrid runner"],
        }

    current_price = float(train_feat["Close"].iloc[-1])
    try:
        model = strategy_module.EnsembleValuationModel(radius_optimal=15.0, n_neighbors=10, xgb_weight=0.6)
        fold_rmse = model.fit(train_feat, n_splits=5)
        feature_row = train_feat[feature_cols].iloc[-1]
        prediction = model.predict_target_price(current_price, feature_row)
    except Exception as exc:
        return {
            "ens_price": None,
            "ens_ret_pct": None,
            "signal": "runtime_error",
            "warnings": [f"tw hybrid training failed: {exc}"],
        }

    ens_ret_pct = prediction["expected_ret_pct"]
    if ens_ret_pct > 5:
        signal = "buy"
    elif ens_ret_pct < -5:
        signal = "avoid"
    else:
        signal = "hold"
    return {
        "ens_price": prediction["ensemble_target"],
        "ens_ret_pct": ens_ret_pct,
        "signal": signal,
        "warnings": [f"cv_rmse_mean={round(float(np.mean(fold_rmse)), 5) if fold_rmse else None}"],
    }


def _unavailable_hybrid_result(reason: str) -> dict[str, object]:
    return {
        "ens_price": None,
        "ens_ret_pct": None,
        "signal": "unavailable",
        "warnings": [f"tw hybrid unavailable: {reason}"],
    }


def _build_revenue_metrics(ticker: str, monthly_revenue_df: pd.DataFrame) -> dict[str, object]:
    df = monthly_revenue_df[monthly_revenue_df["stock_id"].astype(str) == ticker].copy()
    if df.empty:
        return {}
    df["period"] = pd.to_datetime(df["period"], errors="coerce")
    df = df.dropna(subset=["period"]).sort_values("period")
    if df.empty:
        return {}
    latest = df.iloc[-1]
    latest_revenue_yoy = _safe_float(latest.get("revenue_yoy"))
    avg_3m = pd.to_numeric(df["revenue_yoy"], errors="coerce").tail(3).mean()
    return {
        "latest_revenue_month": latest["period"].strftime("%Y-%m"),
        "latest_revenue": _safe_float(latest.get("monthly_revenue")),
        "latest_revenue_yoy": latest_revenue_yoy,
        "avg_3m_revenue_yoy": float(avg_3m) if not math.isnan(avg_3m) else None,
    }


def _build_imfs_rule40_bridge(
    snapshot,
    latest_price: float,
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
) -> dict[str, object]:
    estimated_growth_pct = _estimate_forward_revenue_growth_pct(annual_df, quarterly_df)
    estimated_margin_pct = _estimate_forward_profit_margin_pct(annual_df, quarterly_df, snapshot)
    shares_outstanding = _estimate_shares_outstanding(annual_df, quarterly_df, snapshot)
    base_revenue = _estimate_base_revenue(annual_df, quarterly_df, snapshot)

    if (
        estimated_growth_pct is None
        or estimated_margin_pct is None
        or shares_outstanding in (None, 0)
        or base_revenue in (None, 0)
    ):
        return {
            "warnings": ["rule_of_40_bridge_missing_inputs"],
        }

    quality_score = estimated_growth_pct + estimated_margin_pct
    premium_eligible = quality_score >= 40.0
    justified_pe = _estimate_rule40_justified_pe(quality_score, premium_eligible)
    projected_revenue = base_revenue * (1.0 + estimated_growth_pct / 100.0)
    projected_net_income = projected_revenue * (estimated_margin_pct / 100.0)
    projected_eps = projected_net_income / shares_outstanding if shares_outstanding else None
    intrinsic_value = projected_eps * justified_pe if projected_eps is not None else None
    gap_pct = ((intrinsic_value - latest_price) / latest_price) if intrinsic_value and latest_price else None

    return {
        "estimated_revenue_growth_pct": estimated_growth_pct,
        "estimated_profit_margin_pct": estimated_margin_pct,
        "quality_score": quality_score,
        "premium_eligible": premium_eligible,
        "justified_pe": justified_pe,
        "projected_eps": projected_eps,
        "intrinsic_value": intrinsic_value,
        "gap_pct": gap_pct,
        "warnings": ["rule_of_40_bridge_applied"],
    }


def _estimate_forward_revenue_growth_pct(
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
) -> float | None:
    quarterly = quarterly_df.copy()
    if not quarterly.empty:
        quarterly["date"] = pd.to_datetime(quarterly["date"], errors="coerce")
        quarterly["revenue"] = pd.to_numeric(quarterly.get("revenue"), errors="coerce")
        quarterly = quarterly.dropna(subset=["date", "revenue"]).sort_values("date")
        if len(quarterly) >= 8:
            current_ttm = float(quarterly["revenue"].tail(4).sum())
            prior_ttm = float(quarterly["revenue"].iloc[-8:-4].sum())
            if prior_ttm > 0:
                return max(min((current_ttm / prior_ttm - 1.0) * 100.0, 45.0), -20.0)

    annual = annual_df.copy()
    annual["date"] = pd.to_datetime(annual["date"], errors="coerce")
    annual["revenue"] = pd.to_numeric(annual.get("revenue"), errors="coerce")
    annual = annual.dropna(subset=["date", "revenue"]).sort_values("date")
    if len(annual) >= 2 and float(annual["revenue"].iloc[-2]) > 0:
        latest_growth = (float(annual["revenue"].iloc[-1]) / float(annual["revenue"].iloc[-2]) - 1.0) * 100.0
        return max(min(latest_growth, 45.0), -20.0)
    return None


def _estimate_forward_profit_margin_pct(
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
    snapshot,
) -> float | None:
    quarterly = quarterly_df.copy()
    if not quarterly.empty:
        quarterly["date"] = pd.to_datetime(quarterly["date"], errors="coerce")
        quarterly["revenue"] = pd.to_numeric(quarterly.get("revenue"), errors="coerce")
        quarterly["net_income"] = pd.to_numeric(quarterly.get("net_income"), errors="coerce")
        quarterly["operating_income"] = pd.to_numeric(quarterly.get("operating_income"), errors="coerce")
        quarterly = quarterly.dropna(subset=["date"]).sort_values("date")
        ttm = quarterly.tail(4)
        revenue_ttm = float(ttm["revenue"].sum()) if len(ttm) and ttm["revenue"].notna().any() else None
        net_income_ttm = float(ttm["net_income"].sum()) if len(ttm) and ttm["net_income"].notna().any() else None
        operating_income_ttm = (
            float(ttm["operating_income"].sum()) if len(ttm) and ttm["operating_income"].notna().any() else None
        )
        if revenue_ttm and revenue_ttm > 0:
            if net_income_ttm is not None:
                return max(min(net_income_ttm / revenue_ttm * 100.0, 45.0), 1.0)
            if operating_income_ttm is not None:
                return max(min(operating_income_ttm / revenue_ttm * 100.0, 45.0), 1.0)

    margin = snapshot.net_margin if snapshot.net_margin is not None else snapshot.effective_margin()
    if margin is not None:
        return max(min(margin * 100.0, 45.0), 1.0)
    return None


def _estimate_shares_outstanding(
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
    snapshot,
) -> float | None:
    quarterly_shares = pd.to_numeric(quarterly_df.get("shares_outstanding"), errors="coerce").dropna()
    if not quarterly_shares.empty:
        return float(quarterly_shares.iloc[-1])
    annual_shares = pd.to_numeric(annual_df.get("shares_outstanding"), errors="coerce").dropna()
    if not annual_shares.empty:
        return float(annual_shares.iloc[-1])
    return _safe_float(snapshot.shares_outstanding)


def _estimate_base_revenue(
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
    snapshot,
) -> float | None:
    quarterly_revenue = pd.to_numeric(quarterly_df.get("revenue"), errors="coerce").dropna()
    if len(quarterly_revenue) >= 4:
        return float(quarterly_revenue.tail(4).sum())
    annual_revenue = pd.to_numeric(annual_df.get("revenue"), errors="coerce").dropna()
    if not annual_revenue.empty:
        return float(annual_revenue.iloc[-1])
    return _safe_float(snapshot.revenue)


def _estimate_rule40_justified_pe(quality_score: float, premium_eligible: bool) -> float:
    base_multiple = max(12.0, min(quality_score * 0.45, 28.0))
    premium_bonus = 2.5 if premium_eligible else 0.0
    return round(min(base_multiple + premium_bonus, 32.0), 2)


def _latest_close(price_df: pd.DataFrame) -> float:
    close = pd.to_numeric(price_df["Close"], errors="coerce").dropna()
    return float(close.iloc[-1])


def _latest_date(price_df: pd.DataFrame) -> date:
    return pd.to_datetime(price_df["Date"], errors="coerce").dropna().iloc[-1].date()


def _price_on_or_after(price_df: pd.DataFrame, target_date) -> float | None:
    if target_date is None or pd.isna(target_date):
        return None
    frame = price_df.copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.dropna(subset=["Date"]).sort_values("Date")
    hist = frame[frame["Date"] >= target_date]
    if hist.empty:
        return None
    return _safe_float(hist.iloc[0]["Close"])


def _compute_growth_rate(annual_df: pd.DataFrame) -> float:
    revenue = pd.to_numeric(annual_df.get("revenue"), errors="coerce").dropna()
    if len(revenue) < 2 or revenue.iloc[0] == 0:
        return 0.0
    years = max(len(revenue) - 1, 1)
    return ((revenue.iloc[-1] / revenue.iloc[0]) ** (1 / years) - 1) * 100


def _compute_debt_to_equity(latest_row) -> float:
    if latest_row is None:
        return 0.0
    liabilities = _safe_float(latest_row.get("total_liabilities"))
    equity = _safe_float(latest_row.get("equity"))
    if liabilities is None or equity in (None, 0):
        return 0.0
    return liabilities / equity


def _compute_current_ratio(latest_row) -> float:
    if latest_row is None:
        return 0.0
    current_assets = _safe_float(latest_row.get("current_assets"))
    current_liabilities = _safe_float(latest_row.get("current_liabilities"))
    if current_assets is None or current_liabilities in (None, 0):
        return 0.0
    return current_assets / current_liabilities


def _safe_float(value) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _safe_ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den in (None, 0):
        return None
    return num / den
