from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd


COMPOUNDER_KEYWORDS = (
    "半導體",
    "晶圓",
    "電子",
    "軟體",
    "平台",
    "設計",
    "電腦",
    "網路",
    "商務",
)
FINANCIAL_KEYWORDS = ("金融", "銀行", "保險", "證券", "金控", "financial", "bank", "insurance")
CYCLICAL_KEYWORDS = (
    "航運",
    "shipping",
    "鋼",
    "steel",
    "面板",
    "panel",
    "記憶體",
    "dram",
    "塑化",
    "塑膠",
    "水泥",
    "玻璃",
    "陶瓷",
)
DEFENSIVE_KEYWORDS = ("電信", "通信", "瓦斯", "公用", "食品", "utility", "telecom", "gas")

FINANCIAL_INDUSTRIES = {"金融保險"}
CYCLICAL_INDUSTRIES = {"航運業", "鋼鐵工業", "塑膠工業", "水泥工業", "玻璃陶瓷"}
DEFENSIVE_INDUSTRIES = {"食品工業"}
CYCLICAL_TICKER_OVERRIDES = {"2409", "3481", "2408", "2337", "6770"}

VALUE_WEIGHTS = {
    "high_quality_compounder": {
        "normalized_pe": 0.35,
        "fcf_yield": 0.25,
        "residual_earnings": 0.25,
        "dividend_yield_or_ddm": 0.15,
    },
    "financial": {
        "roe_adjusted_pb": 0.40,
        "ddm": 0.35,
        "normalized_pe": 0.15,
        "residual_income": 0.10,
    },
    "cyclical": {
        "mid_cycle_eps": 0.30,
        "normalized_ev_ebitda": 0.30,
        "replacement_asset_value": 0.20,
        "trough_pb_downside": 0.20,
    },
    "defensive_dividend": {
        "dividend_yield_band": 0.35,
        "ddm": 0.30,
        "normalized_pe": 0.25,
        "fcf_yield": 0.10,
    },
}

SCENARIO_WEIGHTS = {
    "high_quality_compounder": {"conservative": 0.25, "base": 0.50, "bull": 0.25},
    "financial": {"conservative": 0.30, "base": 0.50, "bull": 0.20},
    "cyclical": {"conservative": 0.40, "base": 0.45, "bull": 0.15},
    "defensive_dividend": {"conservative": 0.30, "base": 0.50, "bull": 0.20},
}


@dataclass(frozen=True)
class BuffettThreeScenario:
    fair_pe: float
    required_fcf_yield: float
    cost_of_equity: float
    growth: float
    persistence_factor: float
    fair_dividend_yield: float
    fair_pb_cap: float
    replacement_bv_multiple: float
    trough_pb_multiple: float


BUFFETT3_SCENARIOS = {
    "high_quality_compounder": {
        "conservative": BuffettThreeScenario(18.0, 0.060, 0.105, 0.030, 0.80, 0.040, 2.4, 1.00, 0.90),
        "base": BuffettThreeScenario(22.0, 0.050, 0.095, 0.040, 0.90, 0.035, 2.8, 1.05, 1.00),
        "bull": BuffettThreeScenario(26.0, 0.045, 0.090, 0.050, 1.00, 0.030, 3.2, 1.10, 1.10),
    },
    "financial": {
        "conservative": BuffettThreeScenario(8.0, 0.080, 0.115, 0.015, 0.70, 0.065, 1.30, 1.00, 0.90),
        "base": BuffettThreeScenario(10.0, 0.070, 0.105, 0.020, 0.80, 0.055, 1.55, 1.05, 1.00),
        "bull": BuffettThreeScenario(12.0, 0.060, 0.095, 0.025, 0.90, 0.050, 1.80, 1.10, 1.10),
    },
    "cyclical": {
        "conservative": BuffettThreeScenario(5.0, 0.090, 0.125, 0.010, 0.55, 0.070, 1.10, 0.90, 0.70),
        "base": BuffettThreeScenario(7.0, 0.080, 0.115, 0.015, 0.65, 0.060, 1.25, 1.00, 0.85),
        "bull": BuffettThreeScenario(9.0, 0.070, 0.105, 0.020, 0.75, 0.055, 1.40, 1.10, 0.95),
    },
    "defensive_dividend": {
        "conservative": BuffettThreeScenario(16.0, 0.065, 0.100, 0.015, 0.75, 0.050, 2.0, 1.00, 0.95),
        "base": BuffettThreeScenario(18.0, 0.055, 0.090, 0.020, 0.85, 0.045, 2.2, 1.05, 1.00),
        "bull": BuffettThreeScenario(20.0, 0.050, 0.085, 0.025, 0.95, 0.040, 2.4, 1.10, 1.05),
    },
}


def run_buffett_three_valuation(
    *,
    ticker: str,
    company_name: str,
    industry: str,
    current_price: float | None,
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
    valuation_df: pd.DataFrame,
    dividend_df: pd.DataFrame,
    monthly_revenue_df: pd.DataFrame,
    taiex_df: pd.DataFrame,
) -> dict[str, object]:
    annual_df = _prepare_financial_frame(annual_df)
    quarterly_df = _prepare_financial_frame(quarterly_df)
    valuation_df = valuation_df.copy()
    dividend_df = dividend_df.copy()
    monthly_revenue_df = monthly_revenue_df.copy()

    classification, classification_reason, classification_confidence = classify_company(
        ticker=ticker, company_name=company_name, industry=industry
    )
    normalized_inputs = _build_normalized_inputs(
        classification=classification,
        annual_df=annual_df,
        quarterly_df=quarterly_df,
        valuation_df=valuation_df,
        dividend_df=dividend_df,
        current_price=current_price,
    )
    valuation_legs = _build_valuation_legs(
        classification=classification,
        normalized_inputs=normalized_inputs,
    )
    scenario_weights = SCENARIO_WEIGHTS[classification]
    blended_normalized_valuation, leg_notes, manual_review_flags = _blend_valuation_legs(
        valuation_legs=valuation_legs,
        classification=classification,
    )
    modifiers = _build_modifiers(
        classification=classification,
        annual_df=annual_df,
        quarterly_df=quarterly_df,
        monthly_revenue_df=monthly_revenue_df,
        taiex_df=taiex_df,
        normalized_inputs=normalized_inputs,
    )
    final_fair_value = blended_normalized_valuation
    for block in modifiers.values():
        final_fair_value *= float(block["modifier_value"])

    current = _safe_float(current_price) or _safe_float(normalized_inputs.get("latest_price")) or 0.0
    upside_downside_pct = ((final_fair_value - current) / current) * 100.0 if current > 0 else None

    warnings = [
        *normalized_inputs.get("data_quality_flags", []),
        *leg_notes,
    ]
    result = {
        "ticker": ticker,
        "company_name": company_name,
        "valuation_date": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "classification": classification,
        "company_type": classification,
        "classification_reason": classification_reason,
        "classification_confidence": classification_confidence,
        "input_snapshot": {
            "industry": industry,
            "current_price": current,
            "valuation_row_count": int(len(valuation_df)),
            "dividend_row_count": int(len(dividend_df)),
            "monthly_revenue_row_count": int(len(monthly_revenue_df)),
            "annual_row_count": int(len(annual_df)),
            "quarterly_row_count": int(len(quarterly_df)),
        },
        "normalized_inputs": normalized_inputs,
        "valuation_legs": valuation_legs,
        "scenario_weights": scenario_weights,
        "blended_normalized_valuation": round(blended_normalized_valuation, 4),
        "blended_fair_value": round(blended_normalized_valuation, 4),
        "modifiers": modifiers,
        "final_fair_value_per_share": round(final_fair_value, 4),
        "final_fair_value": round(final_fair_value, 4),
        "current_price": current,
        "upside_downside_pct": round(upside_downside_pct, 4) if upside_downside_pct is not None else None,
        "rating": _value_rating(upside_downside_pct),
        "data_quality_flags": normalized_inputs.get("data_quality_flags", []),
        "manual_review_flags": sorted(set(manual_review_flags + normalized_inputs.get("manual_review_flags", []))),
        "formula_version": "buffett3_v1",
        "signal": _value_signal(upside_downside_pct),
        "warnings": warnings,
    }
    return result


def classify_company(*, ticker: str, company_name: str, industry: str) -> tuple[str, str, str]:
    industry_text = (industry or "").strip()
    text = " ".join([ticker, company_name or "", industry or ""]).lower()
    if industry_text in FINANCIAL_INDUSTRIES or ticker.startswith("28") or any(
        keyword.lower() in text for keyword in FINANCIAL_KEYWORDS
    ):
        return "financial", "industry_or_ticker_matches_financial_rules", "high"
    if ticker in CYCLICAL_TICKER_OVERRIDES:
        return "cyclical", "ticker_matches_cyclical_override", "high"
    if industry_text in CYCLICAL_INDUSTRIES:
        return "cyclical", "industry_exact_matches_cyclical_bucket", "high"
    if industry_text in DEFENSIVE_INDUSTRIES:
        return "defensive_dividend", "industry_exact_matches_defensive_bucket", "high"
    if any(keyword.lower() in text for keyword in CYCLICAL_KEYWORDS):
        return "cyclical", "industry_matches_cyclical_rules", "medium"
    if any(keyword.lower() in text for keyword in DEFENSIVE_KEYWORDS):
        return "defensive_dividend", "industry_matches_defensive_rules", "medium"
    if any(keyword.lower() in text for keyword in COMPOUNDER_KEYWORDS):
        return "high_quality_compounder", "industry_matches_compounder_rules", "medium"
    return "high_quality_compounder", "defaulted_to_compounder_rule", "low"


def _prepare_financial_frame(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    for column in [
        "revenue",
        "net_income",
        "operating_income",
        "operating_cash_flow",
        "capital_expenditure",
        "free_cash_flow",
        "equity",
        "total_assets",
        "total_liabilities",
        "current_assets",
        "current_liabilities",
        "shares_outstanding",
        "eps",
        "book_value_per_share",
        "roe",
        "cash_and_equivalents",
        "total_debt",
    ]:
        if column in working.columns:
            working[column] = pd.to_numeric(working[column], errors="coerce")
    date_col = "report_date" if "report_date" in working.columns else "date"
    if date_col in working.columns:
        working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
        working = working.sort_values(date_col).reset_index(drop=True)
    return working


def _build_normalized_inputs(
    *,
    classification: str,
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
    valuation_df: pd.DataFrame,
    dividend_df: pd.DataFrame,
    current_price: float | None,
) -> dict[str, object]:
    annual_eps = annual_df.get("eps", pd.Series(dtype="float64")).dropna()
    annual_bvps = annual_df.get("book_value_per_share", pd.Series(dtype="float64")).dropna()
    annual_roe = annual_df.get("roe", pd.Series(dtype="float64")).dropna()
    annual_fcf_per_share = (
        annual_df.get("free_cash_flow", pd.Series(dtype="float64"))
        / annual_df.get("shares_outstanding", pd.Series(dtype="float64")).replace({0: pd.NA})
    ).dropna()
    latest_eps = _last_value(annual_eps)
    avg_eps3 = _mean_tail(annual_eps, 3)
    avg_eps4 = _mean_tail(annual_eps, 4)
    latest_bvps = _last_value(annual_bvps)
    avg_roe3 = _mean_tail(annual_roe, 3)
    latest_roe = _last_value(annual_roe)
    avg_fcf3 = _mean_tail(annual_fcf_per_share, 3)
    latest_price = _safe_float(current_price)
    if latest_price is None and not valuation_df.empty:
        latest_price = _safe_float(valuation_df.get("price", pd.Series(dtype="float64")).iloc[-1])
    pe_snapshot = _safe_float(_last_value(valuation_df.get("pe_ratio", pd.Series(dtype="float64")).dropna()))
    pb_snapshot = _safe_float(_last_value(valuation_df.get("pb_ratio", pd.Series(dtype="float64")).dropna()))
    dividend_yield_snapshot = _safe_float(
        _last_value(valuation_df.get("dividend_yield", pd.Series(dtype="float64")).dropna())
    )

    latest_dividend = None
    if not dividend_df.empty and "cash_dividend" in dividend_df.columns:
        dividend_df = dividend_df.copy()
        dividend_df["cash_dividend"] = pd.to_numeric(dividend_df["cash_dividend"], errors="coerce")
        dividend_df["announcement_date"] = pd.to_datetime(dividend_df.get("announcement_date"), errors="coerce")
        dividend_df = dividend_df.sort_values(["fiscal_year", "announcement_date"], na_position="last")
        latest_dividend = _safe_float(_last_value(dividend_df["cash_dividend"].dropna()))

    payout_proxy = None
    if latest_dividend is not None:
        payout_proxy = latest_dividend
    elif latest_price and dividend_yield_snapshot is not None:
        payout_proxy = latest_price * (dividend_yield_snapshot / 100.0)

    normalized_eps = _normalize_eps(
        classification=classification,
        latest_eps=latest_eps,
        avg_eps3=avg_eps3,
        avg_eps4=avg_eps4,
    )
    normalized_fcf_per_share = _normalize_fcf_per_share(
        classification=classification,
        annual_fcf_per_share=annual_fcf_per_share,
        avg_fcf3=avg_fcf3,
    )
    normalized_bvps = latest_bvps
    normalized_roe = _normalize_roe(
        classification=classification,
        latest_roe=latest_roe,
        avg_roe3=avg_roe3,
    )
    normalized_dividend_capacity = payout_proxy
    latest_current_ratio = _latest_ratio(quarterly_df, annual_df, "current_assets", "current_liabilities")
    latest_debt_to_equity = _latest_ratio(quarterly_df, annual_df, "total_liabilities", "equity")
    source_field_coverage = {
        "annual_total_debt_non_null_rows": int(annual_df.get("total_debt", pd.Series(dtype="float64")).dropna().shape[0]),
        "annual_cash_and_equivalents_non_null_rows": int(
            annual_df.get("cash_and_equivalents", pd.Series(dtype="float64")).dropna().shape[0]
        ),
        "annual_operating_income_non_null_rows": int(
            annual_df.get("operating_income", pd.Series(dtype="float64")).dropna().shape[0]
        ),
        "quarterly_total_debt_non_null_rows": int(
            quarterly_df.get("total_debt", pd.Series(dtype="float64")).dropna().shape[0]
        ),
        "quarterly_cash_and_equivalents_non_null_rows": int(
            quarterly_df.get("cash_and_equivalents", pd.Series(dtype="float64")).dropna().shape[0]
        ),
        "quarterly_operating_income_non_null_rows": int(
            quarterly_df.get("operating_income", pd.Series(dtype="float64")).dropna().shape[0]
        ),
    }

    trend_flags: list[str] = []
    if latest_eps is not None and avg_eps3 is not None and latest_eps < avg_eps3:
        trend_flags.append("latest_eps_below_3y_average")
    if normalized_fcf_per_share is not None and normalized_fcf_per_share < 0:
        trend_flags.append("negative_average_fcf")

    data_quality_flags: list[str] = []
    manual_review_flags: list[str] = []
    cyclical_ev_ebitda_blockers: list[str] = []
    if latest_dividend is None:
        data_quality_flags.append("dividend_history_missing_or_proxy_used")
        manual_review_flags.append("dividend_leg_proxy_used")
    if classification == "cyclical":
        manual_review_flags.append("cyclical_ev_ebitda_not_ready_without_clean_ebitda")
        if (
            source_field_coverage["annual_total_debt_non_null_rows"]
            + source_field_coverage["quarterly_total_debt_non_null_rows"]
            == 0
        ):
            cyclical_ev_ebitda_blockers.append("total_debt_missing_in_source_tables")
        if (
            source_field_coverage["annual_cash_and_equivalents_non_null_rows"]
            + source_field_coverage["quarterly_cash_and_equivalents_non_null_rows"]
            == 0
        ):
            cyclical_ev_ebitda_blockers.append("cash_and_equivalents_missing_in_source_tables")
        cyclical_ev_ebitda_blockers.append("clean_ebitda_series_not_available_in_current_dataset")
    if latest_current_ratio is None:
        data_quality_flags.append("current_ratio_missing")
    if latest_debt_to_equity is None:
        data_quality_flags.append("debt_to_equity_missing")
    if normalized_bvps is None:
        data_quality_flags.append("bvps_missing")
    if normalized_eps is None:
        data_quality_flags.append("normalized_eps_missing")

    return {
        "normalized_eps": normalized_eps,
        "normalized_fcf_per_share": normalized_fcf_per_share,
        "normalized_bvps": normalized_bvps,
        "normalized_roe": normalized_roe,
        "normalized_dividend_capacity_per_share": normalized_dividend_capacity,
        "latest_price": latest_price,
        "latest_pe_snapshot": pe_snapshot,
        "latest_pb_snapshot": pb_snapshot,
        "latest_dividend_yield_snapshot": dividend_yield_snapshot,
        "latest_current_ratio": latest_current_ratio,
        "latest_debt_to_equity": latest_debt_to_equity,
        "source_field_coverage": source_field_coverage,
        "cyclical_ev_ebitda_blockers": cyclical_ev_ebitda_blockers,
        "trend_flags": trend_flags,
        "data_quality_flags": data_quality_flags,
        "manual_review_flags": manual_review_flags,
    }


def _normalize_eps(
    *,
    classification: str,
    latest_eps: float | None,
    avg_eps3: float | None,
    avg_eps4: float | None,
) -> float | None:
    if classification == "high_quality_compounder":
        if latest_eps is None:
            return avg_eps3
        if avg_eps3 is None:
            return latest_eps
        if latest_eps > avg_eps3 * 1.15:
            return min(latest_eps, avg_eps3)
        return (latest_eps * 0.6) + (avg_eps3 * 0.4)
    if classification == "financial":
        return latest_eps if latest_eps is not None else avg_eps3
    if classification == "cyclical":
        candidates = [value for value in [avg_eps3, avg_eps4, latest_eps] if value is not None]
        return min(candidates) if candidates else None
    if latest_eps is None:
        return avg_eps3
    if avg_eps3 is None:
        return latest_eps
    return (latest_eps * 0.4) + (avg_eps3 * 0.6) if latest_eps < avg_eps3 else avg_eps3


def _normalize_roe(
    *,
    classification: str,
    latest_roe: float | None,
    avg_roe3: float | None,
) -> float | None:
    if classification == "financial" and avg_roe3 is not None and latest_roe is not None:
        if latest_roe < avg_roe3 * 0.75:
            return (avg_roe3 * 0.7) + (latest_roe * 0.3)
    return avg_roe3 if avg_roe3 is not None else latest_roe


def _normalize_fcf_per_share(
    *,
    classification: str,
    annual_fcf_per_share: pd.Series,
    avg_fcf3: float | None,
) -> float | None:
    if avg_fcf3 is None:
        return None
    if classification != "high_quality_compounder":
        return avg_fcf3
    trailing_fcf = annual_fcf_per_share.dropna().tail(3)
    if len(trailing_fcf) >= 3 and bool((trailing_fcf < 0).all()):
        return 0.0
    return avg_fcf3


def _build_valuation_legs(
    *, classification: str, normalized_inputs: dict[str, object]
) -> list[dict[str, object]]:
    legs: list[dict[str, object]] = []
    for leg_name, weight in VALUE_WEIGHTS[classification].items():
        scenarios = {}
        notes: list[str] = []
        ready = True
        for scenario_name, params in BUFFETT3_SCENARIOS[classification].items():
            value = _compute_leg_value(
                classification=classification,
                leg_name=leg_name,
                scenario_name=scenario_name,
                params=params,
                normalized_inputs=normalized_inputs,
            )
            if value is None:
                ready = False
            elif value < 0:
                value = 0.0
                if "negative_equity_leg_value_floored_to_zero" not in notes:
                    notes.append("negative_equity_leg_value_floored_to_zero")
            scenarios[scenario_name] = value
        if not ready:
            status = "not_ready"
            blended = None
            notes.append("leg_has_missing_required_inputs")
        else:
            status = "ready"
            blended = (
                scenarios["conservative"] * SCENARIO_WEIGHTS[classification]["conservative"]
                + scenarios["base"] * SCENARIO_WEIGHTS[classification]["base"]
                + scenarios["bull"] * SCENARIO_WEIGHTS[classification]["bull"]
            )
        if classification == "cyclical" and leg_name == "normalized_ev_ebitda":
            status = "not_ready"
            blended = None
            notes.append("v1_keeps_ev_ebitda_visible_but_uncomputed")
            notes.extend(str(item) for item in normalized_inputs.get("cyclical_ev_ebitda_blockers", []))
        legs.append(
            {
                "name": leg_name,
                "weight": weight,
                "status": status,
                "inputs": {
                    "normalized_eps": normalized_inputs.get("normalized_eps"),
                    "normalized_fcf_per_share": normalized_inputs.get("normalized_fcf_per_share"),
                    "normalized_bvps": normalized_inputs.get("normalized_bvps"),
                    "normalized_roe": normalized_inputs.get("normalized_roe"),
                    "normalized_dividend_capacity_per_share": normalized_inputs.get(
                        "normalized_dividend_capacity_per_share"
                    ),
                    "source_field_coverage": normalized_inputs.get("source_field_coverage", {}),
                },
                "conservative_value": scenarios.get("conservative"),
                "base_value": scenarios.get("base"),
                "bull_value": scenarios.get("bull"),
                "blended_value": blended,
                "notes": notes,
            }
        )
    return legs


def _compute_leg_value(
    *,
    classification: str,
    leg_name: str,
    scenario_name: str,
    params: BuffettThreeScenario,
    normalized_inputs: dict[str, object],
) -> float | None:
    eps = _safe_float(normalized_inputs.get("normalized_eps"))
    fcf_ps = _safe_float(normalized_inputs.get("normalized_fcf_per_share"))
    bvps = _safe_float(normalized_inputs.get("normalized_bvps"))
    roe_pct = _safe_float(normalized_inputs.get("normalized_roe"))
    dps = _safe_float(normalized_inputs.get("normalized_dividend_capacity_per_share"))
    growth = params.growth
    cost = params.cost_of_equity
    if leg_name == "normalized_pe":
        return eps * params.fair_pe if eps is not None else None
    if leg_name == "fcf_yield":
        return fcf_ps / params.required_fcf_yield if fcf_ps is not None else None
    if leg_name == "residual_earnings":
        if eps is None or bvps is None:
            return None
        residual_eps = eps - (bvps * cost)
        spread = max(cost - growth, 0.03)
        return bvps + ((residual_eps * params.persistence_factor) / spread)
    if leg_name == "roe_adjusted_pb":
        if bvps is None or roe_pct is None:
            return None
        roe = roe_pct / 100.0
        fair_pb = (roe - growth) / max(cost - growth, 0.03)
        fair_pb = min(max(fair_pb, 0.6), params.fair_pb_cap)
        return bvps * fair_pb
    if leg_name == "ddm":
        if dps is None:
            return None
        next_year_dps = dps * (1.0 + growth)
        spread = max(cost - growth, 0.03)
        return next_year_dps / spread
    if leg_name == "residual_income":
        if eps is None or bvps is None:
            return None
        charge = bvps * cost
        spread = max(cost - growth, 0.03)
        return bvps + (((eps - charge) * params.persistence_factor) / spread)
    if leg_name == "mid_cycle_eps":
        return eps * params.fair_pe if eps is not None else None
    if leg_name == "replacement_asset_value":
        return bvps * params.replacement_bv_multiple if bvps is not None else None
    if leg_name == "trough_pb_downside":
        return bvps * params.trough_pb_multiple if bvps is not None else None
    if leg_name == "dividend_yield_band":
        return dps / params.fair_dividend_yield if dps is not None else None
    if leg_name == "dividend_yield_or_ddm":
        if dps is None:
            return None
        dividend_yield_value = dps / params.fair_dividend_yield
        next_year_dps = dps * (1.0 + growth)
        spread = max(cost - growth, 0.03)
        ddm_value = next_year_dps / spread
        return (dividend_yield_value * 0.5) + (ddm_value * 0.5)
    return None


def _blend_valuation_legs(
    *, valuation_legs: list[dict[str, object]], classification: str
) -> tuple[float, list[str], list[str]]:
    ready_legs = [leg for leg in valuation_legs if leg["status"] == "ready" and leg["blended_value"] is not None]
    not_ready_legs = [leg for leg in valuation_legs if leg["status"] != "ready" or leg["blended_value"] is None]
    manual_review_flags: list[str] = []
    notes: list[str] = []
    if not ready_legs:
        manual_review_flags.append("no_ready_valuation_legs")
        return 0.0, notes, manual_review_flags

    total_ready_weight = sum(float(leg["weight"]) for leg in ready_legs)
    cyclical_structural_partial_set = (
        classification == "cyclical"
        and len(not_ready_legs) == 1
        and str(not_ready_legs[0].get("name")) == "normalized_ev_ebitda"
        and "v1_keeps_ev_ebitda_visible_but_uncomputed" in list(not_ready_legs[0].get("notes", []))
    )
    if total_ready_weight < 0.999:
        notes.append("valuation_weights_reallocated_over_ready_legs")
        if not cyclical_structural_partial_set:
            manual_review_flags.append("some_valuation_legs_not_ready")
    blended = 0.0
    for leg in ready_legs:
        adjusted_weight = float(leg["weight"]) / total_ready_weight
        blended += float(leg["blended_value"]) * adjusted_weight
    if classification == "cyclical":
        manual_review_flags.append("cyclical_model_uses_partial_leg_set")
    return blended, notes, manual_review_flags


def _build_modifiers(
    *,
    classification: str,
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
    monthly_revenue_df: pd.DataFrame,
    taiex_df: pd.DataFrame,
    normalized_inputs: dict[str, object],
) -> dict[str, dict[str, object]]:
    return {
        "macro_regime_modifier": _macro_modifier(taiex_df),
        "taiwan_risk_modifier": _taiwan_modifier(classification),
        "reality_validation_modifier": _reality_modifier(
            classification=classification,
            annual_df=annual_df,
            quarterly_df=quarterly_df,
            monthly_revenue_df=monthly_revenue_df,
            normalized_inputs=normalized_inputs,
        ),
    }


def _macro_modifier(taiex_df: pd.DataFrame) -> dict[str, object]:
    working = taiex_df.copy()
    if "Date" in working.columns:
        working["Date"] = pd.to_datetime(working["Date"], errors="coerce")
    close = pd.to_numeric(working.get("Close"), errors="coerce").dropna()
    if len(close) < 200:
        return {
            "raw_score": 0,
            "selected_bucket": "insufficient_data",
            "modifier_value": 1.0,
            "reason": "taiex_history_too_short_for_regime_signal",
            "data_source": "dataset.TAIEX",
        }
    sma50 = float(close.tail(50).mean())
    sma200 = float(close.tail(200).mean())
    latest = float(close.iloc[-1])
    if latest > sma50 > sma200:
        return {
            "raw_score": 2,
            "selected_bucket": "supportive",
            "modifier_value": 1.03,
            "reason": "latest_above_50d_and_200d_trend",
            "data_source": "dataset.TAIEX",
        }
    if latest < sma50 < sma200:
        return {
            "raw_score": -2,
            "selected_bucket": "headwind",
            "modifier_value": 0.94,
            "reason": "latest_below_50d_and_200d_trend",
            "data_source": "dataset.TAIEX",
        }
    return {
        "raw_score": 0,
        "selected_bucket": "neutral",
        "modifier_value": 1.0,
        "reason": "mixed_index_trend",
        "data_source": "dataset.TAIEX",
    }


def _taiwan_modifier(classification: str) -> dict[str, object]:
    value = {
        "high_quality_compounder": 0.95,
        "financial": 0.94,
        "cyclical": 0.92,
        "defensive_dividend": 0.96,
    }[classification]
    return {
        "raw_score": -1,
        "selected_bucket": "default_country_risk_haircut",
        "modifier_value": value,
        "reason": "v1_uses_conservative_taiwan_risk_discount",
        "data_source": "static_v1_config",
    }


def _reality_modifier(
    *,
    classification: str,
    annual_df: pd.DataFrame,
    quarterly_df: pd.DataFrame,
    monthly_revenue_df: pd.DataFrame,
    normalized_inputs: dict[str, object],
) -> dict[str, object]:
    score = 0
    reasons: list[str] = []
    latest_quarter_eps = _last_value(quarterly_df.get("eps", pd.Series(dtype="float64")).dropna())
    latest_monthly_yoy = _last_value(
        pd.to_numeric(monthly_revenue_df.get("revenue_yoy"), errors="coerce").dropna()
    )
    current_ratio = _safe_float(normalized_inputs.get("latest_current_ratio"))
    debt_to_equity = _safe_float(normalized_inputs.get("latest_debt_to_equity"))

    if latest_quarter_eps is not None and latest_quarter_eps > 0:
        score += 1
        reasons.append("latest_quarter_eps_positive")
    if latest_monthly_yoy is not None:
        if latest_monthly_yoy > 5:
            score += 1
            reasons.append("monthly_revenue_yoy_supportive")
        elif latest_monthly_yoy < -5:
            score -= 1
            reasons.append("monthly_revenue_yoy_weak")
    if current_ratio is not None and current_ratio < 1.0:
        score -= 1
        reasons.append("current_ratio_below_1")
    if debt_to_equity is not None and debt_to_equity > 1.5 and classification != "financial":
        score -= 1
        reasons.append("high_debt_to_equity")

    if score >= 2:
        modifier = 1.03
        bucket = "supported"
    elif score <= -2:
        modifier = 0.94
        bucket = "strained"
    else:
        modifier = 1.0
        bucket = "neutral"
    return {
        "raw_score": score,
        "selected_bucket": bucket,
        "modifier_value": modifier,
        "reason": ",".join(reasons) if reasons else "mixed_or_missing_operating_signals",
        "data_source": "buffett3_tables",
    }


def _value_signal(upside_downside_pct: float | None) -> str:
    if upside_downside_pct is None:
        return "資料不足"
    if upside_downside_pct >= 25:
        return "買進"
    if upside_downside_pct >= 10:
        return "觀察買進"
    if upside_downside_pct >= -5:
        return "持有"
    if upside_downside_pct >= -20:
        return "減碼"
    return "避開"


def _value_rating(upside_downside_pct: float | None) -> str:
    if upside_downside_pct is None:
        return "資料不足"
    if upside_downside_pct >= 25:
        return "低估"
    if upside_downside_pct >= 10:
        return "合理偏低"
    if upside_downside_pct >= -5:
        return "合理"
    if upside_downside_pct >= -20:
        return "合理偏高"
    if upside_downside_pct >= -50:
        return "昂貴"
    return "非常昂貴"


def _latest_ratio(
    quarterly_df: pd.DataFrame,
    annual_df: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
) -> float | None:
    for frame in [quarterly_df, annual_df]:
        if numerator_col in frame.columns and denominator_col in frame.columns:
            series_num = pd.to_numeric(frame[numerator_col], errors="coerce").dropna()
            series_den = pd.to_numeric(frame[denominator_col], errors="coerce").dropna()
            if not series_num.empty and not series_den.empty:
                numerator = _safe_float(series_num.iloc[-1])
                denominator = _safe_float(series_den.iloc[-1])
                if numerator is not None and denominator not in (None, 0):
                    return numerator / denominator
    return None


def _last_value(series: pd.Series) -> float | None:
    if series is None or series.empty:
        return None
    return _safe_float(series.iloc[-1])


def _mean_tail(series: pd.Series, count: int) -> float | None:
    if series is None:
        return None
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None
    return float(clean.tail(count).mean())


def _safe_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None
