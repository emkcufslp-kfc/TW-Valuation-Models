from __future__ import annotations

from dataclasses import dataclass


SECTOR_EXIT_MULTIPLES = {
    "軟體": 18,
    "資訊服務": 16,
    "遊戲軟體": 16,
    "通信網路": 14,
    "工業電腦": 13,
    "POS系統": 13,
    "電子": 12,
    "電子零組件": 11,
    "電腦週邊": 11,
    "電源供應器": 10,
    "文化創意": 12,
    "光電": 10,
    "電機機械": 10,
    "金屬製品": 9,
    "營建": 8,
}
DEFAULT_EXIT_MULTIPLE = 12
TERMINAL_GROWTH_RATE = 2.0
MIN_SPREAD = 3.0
ASSET_FLOOR_RATIO = 0.7
DCF_YEARS = 10
EFFECTIVE_GROWTH_MIN = -15.0
EFFECTIVE_GROWTH_MAX = 25.0
GROWTH_RATE_MIN = -5.0
GROWTH_RATE_MAX = 15.0
SUSTAINABLE_GROWTH_FLEX = 1.2
DE_THRESHOLD = 0.5
DE_SLOPE = 3.0
DE_CAP = 4.0
CR_THRESHOLD = 1.5
CR_SLOPE = 2.0
CR_CAP = 2.0
CV_THRESHOLD = 0.3
CV_SLOPE = 3.0
CV_CAP = 3.0
MIN_HISTORICAL_EPS = 3
FCF_SEVERE_PENALTY = 0.5
FCF_CONVERSION_THRESHOLD = 0.6
FCF_MIN_FACTOR = 0.4


@dataclass
class BuffettStock:
    ticker: str
    name: str
    sector: str
    price: float
    eps: float
    pe: float
    pb: float
    roe: float
    dividend_yield: float
    debt_to_equity: float
    current_ratio: float
    fcf: float
    bvps: float
    growth_rate: float
    avg_eps: float | None
    fcf_per_share: float | None
    avg_fcf_per_share: float | None
    historical_eps: list[float]
    share_dilution_rate: float
    avg_roe: float | None = None


def run_buffett_dcf(
    stock: BuffettStock,
    *,
    discount_rate: float = 12.0,
    growth_discount: float = 100.0,
    valuation_mode: str = "avgEps",
) -> dict[str, object]:
    growth_rate = stock.growth_rate or 0.0
    roe = stock.roe or 0.0
    eps = stock.eps or 0.0
    price = stock.price or 0.0
    dividend_yield = stock.dividend_yield or 0.0

    capped = min(max(growth_rate, GROWTH_RATE_MIN), GROWTH_RATE_MAX)
    safe_growth_rate = round(capped * (growth_discount / 100.0), 1)

    if roe > 0 and eps > 0:
        payout_ratio = min((dividend_yield * price) / (eps * 100.0), 1.0)
        sustainable_growth = roe * (1.0 - payout_ratio)
        safe_growth_rate = round(
            min(safe_growth_rate, sustainable_growth * SUSTAINABLE_GROWTH_FLEX), 1
        )

    base_value, base_label = get_base_value(stock, valuation_mode)
    fcf_penalty = None
    if valuation_mode in {"eps", "avgEps"} and eps > 0 and stock.fcf_per_share is not None and stock.sector != "金融":
        conversion_ratio = stock.fcf_per_share / eps
        if conversion_ratio <= 0:
            base_value *= FCF_SEVERE_PENALTY
            fcf_penalty = FCF_SEVERE_PENALTY
        elif conversion_ratio < FCF_CONVERSION_THRESHOLD:
            factor = max(conversion_ratio, FCF_MIN_FACTOR)
            base_value *= factor
            fcf_penalty = round(factor, 2)

    dcf = calc_intrinsic_value(
        base_value,
        safe_growth_rate,
        discount_rate,
        sector=stock.sector,
        debt_to_equity=stock.debt_to_equity,
        current_ratio=stock.current_ratio,
        historical_eps=stock.historical_eps,
        share_dilution_rate=stock.share_dilution_rate,
        bvps=stock.bvps,
    )
    intrinsic_value = dcf["value"]
    mos = get_margin_of_safety(stock.price, intrinsic_value)
    return {
        "ticker": stock.ticker,
        "name": stock.name,
        "model": "BUFFETT_DCF",
        "valuation_mode": valuation_mode,
        "base_label": base_label,
        "base_value": base_value,
        "intrinsic_value": intrinsic_value,
        "margin_of_safety_pct": mos,
        "signal": get_signal_label(mos),
        "signal_color": get_signal_color(mos),
        "growth_rate_used": safe_growth_rate,
        "original_growth_rate": stock.growth_rate,
        "terminal_pct": dcf["terminalPct"],
        "effective_discount": dcf["effectiveDiscount"],
        "risk_premium": dcf["riskPremium"],
        "exit_multiple": dcf["exitMultiple"],
        "fcf_penalty": fcf_penalty,
        "is_asset_floored": dcf["isAssetFloored"],
        "price": stock.price,
        "warnings": [],
    }


def get_base_value(stock: BuffettStock, mode: str) -> tuple[float, str]:
    if mode == "avgEps" and stock.avg_eps is not None:
        return stock.avg_eps, "平滑EPS"
    if mode == "fcfps" and stock.fcf_per_share is not None:
        return stock.fcf_per_share, "每股自由現金流"
    return stock.eps or 0.0, "每股盈餘"


def calc_intrinsic_value(
    base_value: float,
    initial_growth_rate: float,
    discount_rate: float,
    *,
    sector: str,
    debt_to_equity: float | None,
    current_ratio: float | None,
    historical_eps: list[float],
    share_dilution_rate: float,
    bvps: float | None,
) -> dict[str, float | bool]:
    if not base_value or base_value <= 0:
        floor_value = 0.0
        is_asset_floored = False
        if bvps is not None and bvps > 0:
            floor_value = bvps * ASSET_FLOOR_RATIO
            is_asset_floored = True
        return {
            "value": floor_value,
            "terminalPct": 0.0,
            "effectiveDiscount": discount_rate,
            "riskPremium": 0.0,
            "exitMultiple": 0.0,
            "isAssetFloored": is_asset_floored,
        }

    risk_premium = 0.0
    if debt_to_equity is not None and debt_to_equity > DE_THRESHOLD:
        risk_premium += min((debt_to_equity - DE_THRESHOLD) * DE_SLOPE, DE_CAP)
    if current_ratio is not None and current_ratio < CR_THRESHOLD:
        risk_premium += min((CR_THRESHOLD - current_ratio) * CR_SLOPE, CR_CAP)
    if len(historical_eps) >= MIN_HISTORICAL_EPS:
        mean = sum(historical_eps) / len(historical_eps)
        if abs(mean) > 0.01:
            variance = sum((item - mean) ** 2 for item in historical_eps) / len(historical_eps)
            std = variance ** 0.5
            cv = std / abs(mean)
            if cv > CV_THRESHOLD:
                risk_premium += min(cv * CV_SLOPE, CV_CAP)

    risk_premium = round(risk_premium, 2)
    adjusted_discount = discount_rate + risk_premium
    total_pv = 0.0
    current_value = base_value
    for year in range(1, DCF_YEARS + 1):
        current_growth = initial_growth_rate
        if year > 5:
            fade_ratio = (year - 5) / 5
            current_growth = initial_growth_rate - (
                (initial_growth_rate - TERMINAL_GROWTH_RATE) * fade_ratio
            )
        effective_growth = current_growth - share_dilution_rate
        safe_effective_growth = min(
            max(effective_growth, EFFECTIVE_GROWTH_MIN), EFFECTIVE_GROWTH_MAX
        )
        current_value = current_value * (1 + safe_effective_growth / 100.0)
        total_pv += current_value / ((1 + adjusted_discount / 100.0) ** year)

    final_year_value = current_value * (1 + TERMINAL_GROWTH_RATE / 100.0)
    spread = adjusted_discount - TERMINAL_GROWTH_RATE
    safe_spread = max(spread, MIN_SPREAD)
    gordon_tv = final_year_value / (safe_spread / 100.0)
    exit_multiple = SECTOR_EXIT_MULTIPLES.get(sector, DEFAULT_EXIT_MULTIPLE)
    exit_multiple_tv = final_year_value * exit_multiple
    terminal_value = min(gordon_tv, exit_multiple_tv)
    discounted_terminal_value = terminal_value / ((1 + adjusted_discount / 100.0) ** DCF_YEARS)

    intrinsic_value = total_pv + discounted_terminal_value
    terminal_pct = round((discounted_terminal_value / intrinsic_value) * 100.0, 1) if intrinsic_value > 0 else 0.0
    is_asset_floored = False
    if bvps is not None and bvps > 0 and intrinsic_value < bvps * ASSET_FLOOR_RATIO:
        intrinsic_value = bvps * ASSET_FLOOR_RATIO
        is_asset_floored = True
    return {
        "value": intrinsic_value,
        "terminalPct": terminal_pct,
        "effectiveDiscount": round(adjusted_discount, 2),
        "riskPremium": risk_premium,
        "exitMultiple": exit_multiple,
        "isAssetFloored": is_asset_floored,
    }


def get_margin_of_safety(price: float, intrinsic_value: float) -> float:
    if not intrinsic_value or intrinsic_value <= 0:
        return 0.0
    return ((intrinsic_value - price) / intrinsic_value) * 100.0


def get_signal_color(mos: float) -> str:
    if mos >= 30.0:
        return "#22c55e"
    if mos >= 10.0:
        return "#f59e0b"
    return "#ef4444"


def get_signal_label(mos: float) -> str:
    if mos >= 30.0:
        return "低估"
    if mos >= 10.0:
        return "合理價位"
    return "高估"
