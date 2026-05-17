from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import WorkspacePaths
from .csv_utils import read_csv_rows
from .final_module_data import PILOT_TICKERS


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_results_row(paths: WorkspacePaths, ticker: str) -> dict[str, str]:
    results_path = paths.artifacts_root / "results" / "top100_model_results.csv"
    with results_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row["ticker"]) == ticker:
                return row
    on_demand_path = paths.on_demand_results_root / f"{ticker}.json"
    if on_demand_path.exists():
        payload = json.loads(on_demand_path.read_text(encoding="utf-8"))
        row = payload.get("row", {})
        if isinstance(row, dict):
            return {str(key): value for key, value in row.items()}
    raise KeyError(f"Ticker {ticker} not found in top100_model_results.csv")


def _load_buffett3_payload(paths: WorkspacePaths, ticker: str) -> dict[str, Any]:
    payload_path = paths.artifacts_root / "results" / "buffett3_payloads" / f"{ticker}.json"
    return json.loads(payload_path.read_text(encoding="utf-8"))


def _load_snapshot_rows(paths: WorkspacePaths, filename: str, ticker: str) -> list[dict[str, str]]:
    return [
        row
        for row in read_csv_rows(paths.final_module_normalized_root / filename)
        if str(row["ticker"]) == ticker
    ]


@dataclass(frozen=True)
class SectorProfile:
    company_name: str
    industry_bucket: str
    valuation_method_primary: str
    valuation_method_secondary: str
    action_stance_fair_high_quality: str
    reasoning_summary: str
    calculation_logic_summary: str
    key_assumptions: list[str]
    key_risks: list[str]


SECTOR_PROFILES: dict[str, SectorProfile] = {
    "2330": SectorProfile(
        company_name="\u53f0\u7063\u7a4d\u9ad4\u96fb\u8def\u88fd\u9020\u80a1\u4efd\u6709\u9650\u516c\u53f8",
        industry_bucket="\u534a\u5c0e\u9ad4\u6210\u9577\u80a1",
        valuation_method_primary="\u6210\u9577\u578b\u672c\u76ca\u6bd4\u6cd5",
        valuation_method_secondary="\u81ea\u7531\u73fe\u91d1\u6d41\u4ea4\u53c9\u9a57\u8b49\u6cd5",
        action_stance_fair_high_quality="hold",
        reasoning_summary="\u53f0\u7a4d\u96fb\u5c6c\u65bc\u9ad8\u54c1\u8cea\u3001\u9ad8\u6210\u9577\u4e14\u5177\u6280\u8853\u8b77\u57ce\u6cb3\u7684\u6838\u5fc3\u8cc7\u7522\uff0c\u4f46\u76ee\u524d\u5e02\u5834\u50f9\u683c\u5df2\u53cd\u6620\u5927\u91cf AI \u6210\u9577\u9810\u671f\uff0c\u56e0\u6b64\u4e0d\u5c6c\u65bc\u660e\u986f\u4f4e\u4f30\u3002",
        calculation_logic_summary="\u4ee5\u6b63\u5e38\u5316 EPS \u5c0d\u61c9\u9ad8\u54c1\u8cea\u534a\u5c0e\u9ad4\u9f8d\u982d\u7684\u5408\u7406\u672c\u76ca\u6bd4\u5340\u9593\u4f30\u7b97\u6838\u5fc3\u50f9\u503c\uff0c\u518d\u7528\u6bcf\u80a1\u81ea\u7531\u73fe\u91d1\u6d41\u5c0d\u7167\u7d50\u679c\u505a\u4fdd\u5b88\u4ea4\u53c9\u9a57\u8b49\u3002\u9019\u500b\u65b9\u6cd5\u627f\u8a8d\u6210\u9577\u6ea2\u50f9\uff0c\u4f46\u4e0d\u76f4\u63a5\u6cbf\u7528\u65e2\u6709\u6a21\u578b\u7684\u5167\u5728\u50f9\u503c\u8f38\u51fa\u3002",
        key_assumptions=[
            "AI \u9700\u6c42\u8207\u5148\u9032\u88fd\u7a0b\u52d5\u80fd\u4ecd\u5ef6\u7e8c",
            "\u9ad8\u54c1\u8cea\u9f8d\u982d\u53ef\u7dad\u6301\u9ad8\u65bc\u5e02\u5834\u5e73\u5747\u7684\u5408\u7406\u672c\u76ca\u6bd4",
            "\u81ea\u7531\u73fe\u91d1\u6d41\u8207\u7372\u5229\u54c1\u8cea\u672a\u51fa\u73fe\u7d50\u69cb\u6027\u60e1\u5316",
        ],
        key_risks=[
            "AI \u984c\u6750\u964d\u6eab\u5c0e\u81f4\u4f30\u503c\u4fee\u6b63",
            "\u8cc7\u672c\u652f\u51fa\u58d3\u529b\u9ad8\u65bc\u9810\u671f",
            "\u5730\u7de3\u653f\u6cbb\u8207\u4f9b\u61c9\u93c8\u98a8\u96aa",
        ],
    ),
    "2881": SectorProfile(
        company_name="\u5bcc\u90a6\u91d1\u878d\u63a7\u80a1\u80a1\u4efd\u6709\u9650\u516c\u53f8",
        industry_bucket="\u91d1\u878d\u80a1",
        valuation_method_primary="ROE / PB \u4f30\u503c\u6cd5",
        valuation_method_secondary="\u80a1\u5229\u6298\u73fe\u6cd5",
        action_stance_fair_high_quality="hold",
        reasoning_summary="\u5bcc\u90a6\u91d1\u5177\u91d1\u63a7\u9f8d\u982d\u898f\u6a21\u3001\u7a69\u5b9a\u914d\u606f\u80fd\u529b\u8207\u4e2d\u7b49\u504f\u4e0a\u7684 ROE\uff0c\u4f46\u76ee\u524d\u5e02\u5834\u50f9\u683c\u5df2\u63a5\u8fd1\u5408\u7406\u5340\u9593\uff0c\u4e26\u975e\u660e\u986f\u4f4e\u4f30\u3002",
        calculation_logic_summary="\u4ee5\u6b63\u5e38\u5316 ROE \u5c0d\u61c9\u5408\u7406 PB \u5340\u9593\u4f30\u7b97\u6838\u5fc3\u50f9\u503c\uff0c\u518d\u4ee5\u73fe\u91d1\u80a1\u5229\u80fd\u529b\u505a\u4ea4\u53c9\u9a57\u8b49\u3002\u5c0d\u91d1\u878d\u80a1\u800c\u8a00\uff0c\u6de8\u503c\u3001ROE \u8207\u914d\u606f\u7a69\u5b9a\u6027\u6bd4\u9ad8\u6210\u9577\u6558\u4e8b\u66f4\u91cd\u8981\u3002",
        key_assumptions=[
            "\u6b63\u5e38\u5316 ROE \u7dad\u6301\u5728 11% \u5230 13% \u5340\u9593",
            "\u5e02\u5834\u7d66\u4e88\u7684\u5408\u7406 PB \u4e0d\u6703\u9577\u671f\u812b\u96e2 1.2 \u5230 1.4 \u500d\u592a\u591a",
            "\u73fe\u91d1\u80a1\u5229\u80fd\u529b\u7dad\u6301\u5728\u6bcf\u80a1 4 \u5143\u4ee5\u4e0a\u9644\u8fd1",
        ],
        key_risks=[
            "\u58fd\u96aa\u8207\u8cc7\u672c\u5e02\u5834\u6ce2\u52d5\u5f71\u97ff\u6de8\u503c",
            "\u5229\u7387\u8207\u532f\u7387\u8b8a\u52d5\u5f71\u97ff\u7372\u5229\u54c1\u8cea",
            "\u82e5\u914d\u606f\u4e0d\u5982\u9810\u671f\uff0c\u5e02\u5834\u8a55\u50f9\u53ef\u80fd\u4e0b\u4fee",
        ],
    ),
    "2603": SectorProfile(
        company_name="\u9577\u69ae\u6d77\u904b\u80a1\u4efd\u6709\u9650\u516c\u53f8",
        industry_bucket="\u666f\u6c23\u5faa\u74b0\u80a1",
        valuation_method_primary="\u666f\u6c23\u4e2d\u4f4d\u7372\u5229\u4f30\u503c\u6cd5",
        valuation_method_secondary="\u80a1\u5229\u80fd\u529b\u8207\u8cc7\u7522\u50f9\u503c\u8f14\u52a9\u6cd5",
        action_stance_fair_high_quality="hold",
        reasoning_summary="\u9577\u69ae\u76ee\u524d\u80a1\u50f9\u5927\u81f4\u843d\u5728\u5408\u7406\u5340\u9593\u5167\uff0c\u77ed\u671f\u6709\u9ad8\u80a1\u606f\u8207\u904b\u50f9\u652f\u6490\uff0c\u4f46\u4e2d\u9577\u671f\u4ecd\u5c6c\u666f\u6c23\u5faa\u74b0\u80a1\uff0c\u4e0d\u5b9c\u7528\u9ad8\u5cf0\u7372\u5229\u76f4\u63a5\u505a\u6c38\u4e45\u4f30\u503c\u3002",
        calculation_logic_summary="\u4ee5\u6b63\u5e38\u5316 EPS \u5c0d\u61c9\u666f\u6c23\u4e2d\u4f4d\u6578 PE \u5340\u9593\u4f30\u7b97\u6838\u5fc3\u50f9\u503c\uff0c\u518d\u7528\u6bcf\u80a1\u6de8\u503c\u8207\u80a1\u5229\u80fd\u529b\u505a\u8f14\u52a9\u9a57\u8b49\u3002\u91cd\u9ede\u4e0d\u662f\u55ae\u5e74\u9ad8\u5cf0\u8cfa\u591a\u5c11\uff0c\u800c\u662f\u6b63\u5e38\u9031\u671f\u5e74\u4efd\u5927\u6982\u503c\u591a\u5c11\u3002",
        key_assumptions=[
            "\u4e0d\u4ee5\u666f\u6c23\u9ad8\u5cf0\u5e74\u5ea6\u7372\u5229\u76f4\u63a5\u8996\u70ba\u5e38\u614b",
            "\u5e02\u5834\u9858\u610f\u7d66\u4e88\u9ad8\u80a1\u606f\u652f\u6490\uff0c\u4f46\u4e0d\u6703\u7121\u9650\u63d0\u9ad8\u4f30\u503c\u500d\u6578",
            "\u672a\u4f86\u904b\u50f9\u8207\u4f9b\u9700\u7d50\u69cb\u4e0d\u5047\u8a2d\u6301\u7e8c\u6975\u7aef\u6709\u5229",
        ],
        key_risks=[
            "\u5168\u7403\u666f\u6c23\u653e\u7de9\u5c0e\u81f4\u904b\u50f9\u56de\u843d",
            "\u4f9b\u7d66\u589e\u52a0\u58d3\u7e2e\u672a\u4f86\u7372\u5229\u4e2d\u6a1e",
            "\u5e02\u5834\u904e\u5ea6\u628a\u9ad8\u914d\u606f\u8996\u70ba\u9577\u671f\u5e38\u614b",
        ],
    ),
    "2412": SectorProfile(
        company_name="\u4e2d\u83ef\u96fb\u4fe1\u80a1\u4efd\u6709\u9650\u516c\u53f8",
        industry_bucket="\u9632\u79a6\u578b\u9ad8\u80a1\u606f\u80a1",
        valuation_method_primary="\u80a1\u5229\u6298\u73fe\u6cd5",
        valuation_method_secondary="\u6536\u76ca\u6b96\u5229\u7387\u4f30\u503c\u6cd5",
        action_stance_fair_high_quality="hold",
        reasoning_summary="\u4e2d\u83ef\u96fb\u4fe1\u5177\u7a69\u5b9a\u73fe\u91d1\u6d41\u3001\u914d\u606f\u8207\u9632\u79a6\u6027\uff0c\u4f46\u7531\u65bc\u6210\u9577\u6027\u6709\u9650\uff0c\u4f30\u503c\u61c9\u4e3b\u8981\u5efa\u7acb\u5728\u6536\u76ca\u8207\u7a69\u5b9a\u6027\uff0c\u800c\u4e0d\u662f\u9ad8\u6210\u9577\u6ea2\u50f9\u4e0a\u3002",
        calculation_logic_summary="\u5148\u4ee5\u53ef\u6301\u7e8c\u80a1\u5229\u80fd\u529b\u63a8\u7b97\u5408\u7406\u6b96\u5229\u7387\u5340\u9593\uff0c\u518d\u7528\u7a69\u5b9a\u6536\u76ca\u578b\u8cc7\u7522\u7684\u73fe\u91d1\u6d41\u4f30\u503c\u505a\u4ea4\u53c9\u9a57\u8b49\u3002\u9019\u985e\u6a19\u7684\u7684\u4f30\u503c\u6838\u5fc3\u662f\u6536\u76ca\u53ef\u6301\u7e8c\u6027\u8207\u9632\u5b88\u50f9\u503c\u3002",
        key_assumptions=[
            "\u672a\u4f86\u80a1\u5229\u80fd\u529b\u7dad\u6301\u7a69\u5b9a",
            "\u6210\u9577\u7387\u7dad\u6301\u4f4e\u500b\u4f4d\u6578",
            "\u5e02\u5834\u9858\u610f\u70ba\u7a69\u5b9a\u6536\u76ca\u8cc7\u7522\u652f\u4ed8\u9069\u5ea6\u6ea2\u50f9",
        ],
        key_risks=[
            "\u82e5\u914d\u606f\u653f\u7b56\u6539\u8b8a\uff0c\u8a55\u50f9\u4e2d\u6a1e\u53ef\u80fd\u4e0b\u964d",
            "\u82e5\u5229\u7387\u74b0\u5883\u6539\u8b8a\uff0c\u9ad8\u80a1\u606f\u8cc7\u7522\u5438\u5f15\u529b\u53ef\u80fd\u4e0b\u964d",
            "\u6210\u9577\u6027\u4e0d\u8db3\u9650\u5236\u8a55\u50f9\u4e0a\u4fee\u7a7a\u9593",
        ],
    ),
}


def build_final_module_payloads(
    paths: WorkspacePaths, tickers: list[str] | None = None
) -> dict[str, object]:
    selected = tickers or list(PILOT_TICKERS)
    generated_at = _utc_now_iso()
    as_of_date = datetime.now().date().isoformat()
    paths.final_module_independent_ai_root.mkdir(parents=True, exist_ok=True)
    paths.final_module_commentary_root.mkdir(parents=True, exist_ok=True)

    created = []
    for ticker in selected:
        independent_payload = _build_independent_ai_payload(paths, ticker, as_of_date, generated_at)
        commentary_payload = _build_commentary_payload(
            paths, ticker, as_of_date, generated_at, independent_payload
        )

        independent_path = paths.final_module_independent_ai_root / f"{ticker}.json"
        commentary_path = paths.final_module_commentary_root / f"{ticker}.json"
        independent_path.write_text(
            json.dumps(independent_payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        commentary_path.write_text(
            json.dumps(commentary_payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        created.append(
            {
                "ticker": ticker,
                "independent_ai": str(independent_path),
                "final_commentary": str(commentary_path),
            }
        )

    summary = {
        "generated_at": generated_at,
        "as_of_date": as_of_date,
        "tickers": selected,
        "payload_count": len(created),
        "files": created,
    }
    summary_path = paths.final_module_payload_root / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def _build_independent_ai_payload(
    paths: WorkspacePaths, ticker: str, as_of_date: str, generated_at: str
) -> dict[str, Any]:
    results = _load_results_row(paths, ticker)
    buffett3 = _load_buffett3_payload(paths, ticker)
    institutional_rows = _load_snapshot_rows(paths, "institutional_consensus.csv", ticker)
    public_rows = _load_snapshot_rows(paths, "public_commentary.csv", ticker)
    news_rows = _load_snapshot_rows(paths, "news_commentary.csv", ticker)
    profile = _resolve_sector_profile(ticker, results, buffett3)
    current_price = _safe_float(results["price"])
    metrics = buffett3.get("normalized_inputs", {})
    low, base, high = _calculate_range_for_ticker(
        ticker=ticker,
        classification=str(buffett3.get("classification") or results.get("buffett3_type") or ""),
        current_price=current_price,
        metrics=metrics,
        institutional_rows=institutional_rows,
    )
    valuation_conclusion = _valuation_label(current_price, base)
    action_stance = _action_stance(profile, valuation_conclusion)

    return {
        "ticker": ticker,
        "as_of_date": as_of_date,
        "industry_bucket": profile.industry_bucket,
        "valuation_method_primary": profile.valuation_method_primary,
        "valuation_method_secondary": profile.valuation_method_secondary,
        "fair_value_low": round(low, 2),
        "fair_value_base": round(base, 2),
        "fair_value_high": round(high, 2),
        "valuation_conclusion": valuation_conclusion,
        "action_stance": action_stance,
        "confidence": _confidence_label(profile),
        "reasoning_summary": profile.reasoning_summary,
        "calculation_logic_summary": profile.calculation_logic_summary,
        "key_assumptions": profile.key_assumptions,
        "key_risks": profile.key_risks,
        "market_context_used": bool(institutional_rows or public_rows or news_rows),
        "generated_at": generated_at,
    }


def _calculate_range_for_ticker(
    ticker: str,
    classification: str,
    current_price: float,
    metrics: dict[str, Any],
    institutional_rows: list[dict[str, str]],
) -> tuple[float, float, float]:
    eps = _safe_float(metrics.get("normalized_eps"))
    fcf = _safe_float(metrics.get("normalized_fcf_per_share"))
    bvps = _safe_float(metrics.get("normalized_bvps"))
    dividend = _safe_float(metrics.get("normalized_dividend_capacity_per_share"))
    targets = [
        _safe_float(row.get("target_price"))
        for row in institutional_rows
        if _safe_float(row.get("target_price")) > 0
    ]
    institution_avg_target = sum(targets) / len(targets) if targets else 0.0

    if ticker == "2330":
        pe_values = [eps * 42.0, eps * 49.0, eps * 54.0]
        fcf_values = [fcf * 26.0, fcf * 30.0, fcf * 34.0]
        low = (pe_values[0] * 0.7) + (fcf_values[0] * 0.3)
        base = (pe_values[1] * 0.75) + (fcf_values[1] * 0.25)
        high = max((pe_values[2] * 0.8) + (fcf_values[2] * 0.2), institution_avg_target * 0.96)
        return low, base, high
    if ticker == "2881":
        pb_values = [bvps * 1.20, bvps * 1.28, bvps * 1.36]
        ddm_values = [dividend / 0.049, dividend / 0.046, dividend / 0.043]
        low = (pb_values[0] * 0.7) + (ddm_values[0] * 0.3)
        base = (pb_values[1] * 0.7) + (ddm_values[1] * 0.3)
        high = (pb_values[2] * 0.65) + (ddm_values[2] * 0.35)
        return low, base, high
    if ticker == "2603":
        pe_values = [eps * 3.0, eps * 3.3, eps * 3.7]
        pb_values = [bvps * 0.93, bvps * 1.06, bvps * 1.18]
        low = (pe_values[0] * 0.6) + (pb_values[0] * 0.4)
        base = (pe_values[1] * 0.65) + (pb_values[1] * 0.35)
        high = (pe_values[2] * 0.65) + (pb_values[2] * 0.35)
        return low, base, high
    if ticker == "2412":
        yield_values = [dividend / 0.039, dividend / 0.0365, dividend / 0.0345]
        price_anchor = [current_price * 0.91, current_price * 0.975, current_price * 1.03]
        low = (yield_values[0] * 0.8) + (price_anchor[0] * 0.2)
        base = (yield_values[1] * 0.85) + (price_anchor[1] * 0.15)
        high = (yield_values[2] * 0.85) + (price_anchor[2] * 0.15)
        return low, base, high
    if classification == "financial":
        pb_values = [bvps * 1.10, bvps * 1.22, bvps * 1.35]
        ddm_values = [dividend / 0.052, dividend / 0.047, dividend / 0.043]
        return (
            (pb_values[0] * 0.65) + (ddm_values[0] * 0.35),
            (pb_values[1] * 0.65) + (ddm_values[1] * 0.35),
            max((pb_values[2] * 0.6) + (ddm_values[2] * 0.4), institution_avg_target * 0.92),
        )
    if classification == "cyclical":
        pe_values = [eps * 3.4, eps * 4.0, eps * 4.6]
        pb_values = [bvps * 0.9, bvps * 1.02, bvps * 1.15]
        return (
            (pe_values[0] * 0.6) + (pb_values[0] * 0.4),
            (pe_values[1] * 0.65) + (pb_values[1] * 0.35),
            max((pe_values[2] * 0.65) + (pb_values[2] * 0.35), institution_avg_target * 0.9),
        )
    if classification == "defensive_dividend":
        yield_values = [dividend / 0.045, dividend / 0.039, dividend / 0.034]
        price_anchor = [current_price * 0.88, current_price * 0.98, current_price * 1.06]
        return (
            (yield_values[0] * 0.8) + (price_anchor[0] * 0.2),
            (yield_values[1] * 0.8) + (price_anchor[1] * 0.2),
            max((yield_values[2] * 0.8) + (price_anchor[2] * 0.2), institution_avg_target * 0.92),
        )
    pe_values = [eps * 14.0, eps * 17.0, eps * 20.0]
    fcf_values = [fcf * 12.0, fcf * 15.0, fcf * 18.0]
    low = (pe_values[0] * 0.65) + (fcf_values[0] * 0.35)
    base = (pe_values[1] * 0.7) + (fcf_values[1] * 0.3)
    high = max((pe_values[2] * 0.7) + (fcf_values[2] * 0.3), institution_avg_target * 0.92)
    return low, base, high


def _valuation_label(current_price: float, fair_value_base: float) -> str:
    if current_price <= fair_value_base * 0.85:
        return "undervalued"
    if current_price <= fair_value_base * 1.15:
        return "fair"
    return "overvalued"


def _action_stance(profile: SectorProfile, valuation_conclusion: str) -> str:
    if valuation_conclusion == "undervalued":
        return "buy" if profile.industry_bucket in {"半導體成長股", "金融股"} else "accumulate"
    if valuation_conclusion == "fair":
        return profile.action_stance_fair_high_quality
    if profile.industry_bucket in {"半導體成長股", "防禦型高股息股"}:
        return "hold"
    return "reduce"


def _confidence_label(profile: SectorProfile) -> str:
    return "medium" if profile.industry_bucket == "景氣循環股" else "medium_high"


def _trad_valuation_label(code: str) -> str:
    return {
        "undervalued": "\u4f4e\u4f30",
        "fair": "\u5408\u7406",
        "overvalued": "\u9ad8\u4f30",
    }[code]


def _trad_action_label(code: str) -> str:
    return {
        "buy": "\u8cb7\u9032",
        "accumulate": "\u5206\u6279\u5e03\u5c40",
        "hold": "\u6301\u6709",
        "reduce": "\u6e1b\u78bc",
        "avoid": "\u907f\u958b",
    }[code]


def _trad_confidence_label(code: str) -> str:
    return {
        "medium": "\u4e2d\u7b49",
        "medium_high": "\u4e2d\u9ad8",
        "high": "\u9ad8",
    }[code]


def _build_commentary_payload(
    paths: WorkspacePaths,
    ticker: str,
    as_of_date: str,
    generated_at: str,
    independent_payload: dict[str, Any],
) -> dict[str, Any]:
    results = _load_results_row(paths, ticker)
    buffett3 = _load_buffett3_payload(paths, ticker)
    institutional_rows = _load_snapshot_rows(paths, "institutional_consensus.csv", ticker)
    news_rows = _load_snapshot_rows(paths, "news_commentary.csv", ticker)
    public_rows = _load_snapshot_rows(paths, "public_commentary.csv", ticker)
    profile = _resolve_sector_profile(ticker, results, buffett3)

    hybrid_target = _safe_float(results.get("hybrid_target"))
    quant_score = _safe_float(results.get("quant_score"))
    current_price = _safe_float(results.get("price"))
    final_label = _trad_valuation_label(independent_payload["valuation_conclusion"])
    action_label = _trad_action_label(independent_payload["action_stance"])

    return {
        "ticker": ticker,
        "as_of_date": as_of_date,
        "company_name": profile.company_name,
        "internal_model_snapshot": {
            "buffett3": {
                "fair_value": round(_safe_float(results.get("buffett3_intrinsic")), 4),
                "conclusion": _clean_buffett3_rating(buffett3),
                "action": _clean_buffett3_action(buffett3),
                "comment": _buffett3_comment(profile),
            },
            "imfs": {
                "fair_value": round(_safe_float(results.get("imfs_intrinsic")), 4),
                "conclusion": _imfs_conclusion(results),
                "action": _imfs_action(results),
                "comment": _imfs_comment(profile),
            },
            "hybrid": {
                "fair_value": round(hybrid_target, 4) if hybrid_target else None,
                "conclusion": _hybrid_conclusion(hybrid_target, current_price),
                "action": "\u6301\u6709" if hybrid_target else "\u89c0\u5bdf",
                "comment": "\u8f03\u63a5\u8fd1\u5e02\u5834\u7d9c\u5408\u5b9a\u50f9\u3002" if hybrid_target else "\u7576\u524d\u7121\u53ef\u7528\u8f38\u51fa\u3002",
            },
            "quant": {
                "score": quant_score,
                "conclusion": _quant_conclusion(quant_score),
                "action": "\u89c0\u5bdf",
                "comment": "\u56e0\u5b50\u5206\u6578\u9069\u5408\u505a\u6392\u5e8f\u8f14\u52a9\uff0c\u4e0d\u9069\u5408\u55ae\u7368\u53d6\u4ee3\u4f30\u503c\u7d50\u8ad6\u3002",
            },
        },
        "independent_ai_snapshot": {
            "fair_value_range": f"{independent_payload['fair_value_low']}-{independent_payload['fair_value_high']}",
            "base_fair_value": independent_payload["fair_value_base"],
            "conclusion": _trad_valuation_label(independent_payload["valuation_conclusion"]),
            "action": _trad_action_label(independent_payload["action_stance"]),
            "confidence": _trad_confidence_label(independent_payload["confidence"]),
        },
        "news_snapshot": {
            "summary": _build_news_summary(news_rows),
            "sentiment": _build_news_sentiment(news_rows),
            "comment": _build_news_comment(profile, news_rows),
        },
        "public_vs_institution_snapshot": {
            "public_view": _build_public_view(profile, public_rows),
            "institution_view": _build_institution_view(profile, institutional_rows),
            "divergence": _build_divergence_summary_clean(institutional_rows, public_rows, news_rows),
        },
        "model_difference_explanation": _model_difference_explanation(profile),
        "final_conclusion": {
            "valuation_label": final_label,
            "action_label": action_label,
            "summary": _build_final_summary(
                ticker=ticker,
                profile=profile,
                action_label=action_label,
                current_price=current_price,
                fair_value_base=independent_payload["fair_value_base"],
            ),
        },
        "risk_summary": profile.key_risks,
        "change_view_conditions": _change_conditions(profile),
        "generated_at": generated_at,
    }


def _resolve_sector_profile(
    ticker: str, results: dict[str, str], buffett3: dict[str, Any]
) -> SectorProfile:
    if ticker in SECTOR_PROFILES:
        return SECTOR_PROFILES[ticker]
    company_name = str(
        results.get("name")
        or buffett3.get("company_name")
        or ticker
    )
    classification = str(buffett3.get("classification") or results.get("buffett3_type") or "")
    if classification == "financial":
        return SectorProfile(
            company_name=company_name,
            industry_bucket="金融股",
            valuation_method_primary="ROE / PB 估值法",
            valuation_method_secondary="股利折現法",
            action_stance_fair_high_quality="hold",
            reasoning_summary="此標的較適合以淨值、ROE 與股利能力評估合理價值，而非直接套用高成長股估值框架。",
            calculation_logic_summary="先以正常化 ROE 對應合理 PB 區間估算核心價值，再用可持續現金股利能力做交叉驗證。",
            key_assumptions=["ROE 維持正常區間", "淨值品質未出現明顯惡化", "股利政策可延續"],
            key_risks=["金融資產評價波動", "利率與匯率風險", "配息不如預期"],
        )
    if classification == "cyclical":
        return SectorProfile(
            company_name=company_name,
            industry_bucket="景氣循環股",
            valuation_method_primary="景氣中位獲利估值法",
            valuation_method_secondary="資產價值與股利能力輔助法",
            action_stance_fair_high_quality="hold",
            reasoning_summary="此標的屬景氣循環類型，估值必須避免直接把高峰獲利當作常態。",
            calculation_logic_summary="以正常化獲利對應保守估值倍數，再用資產價值與股利能力做輔助交叉驗證。",
            key_assumptions=["景氣中位數獲利可持續", "供需結構不長期失衡", "高股息不視為永久常態"],
            key_risks=["景氣反轉", "價格循環回落", "高配息不可持續"],
        )
    if classification == "defensive_dividend":
        return SectorProfile(
            company_name=company_name,
            industry_bucket="防禦型高股息股",
            valuation_method_primary="股利折現法",
            valuation_method_secondary="收益殖利率估值法",
            action_stance_fair_high_quality="hold",
            reasoning_summary="此標的偏防守型與收益型，估值主軸應放在配息持續性與合理殖利率。",
            calculation_logic_summary="先以可持續股利能力推算合理殖利率區間，再用穩定收益資產的價格區間交叉驗證。",
            key_assumptions=["股利穩定", "現金流品質穩健", "市場願給予防守溢價"],
            key_risks=["殖利率吸引力下降", "成長性不足", "利率環境改變"],
        )
    return SectorProfile(
        company_name=company_name,
        industry_bucket="高品質成長股",
        valuation_method_primary="成長型本益比法",
        valuation_method_secondary="自由現金流交叉驗證法",
        action_stance_fair_high_quality="hold",
        reasoning_summary="此標的較適合用成長與現金流並重的方式判斷合理價值。",
        calculation_logic_summary="以正常化 EPS 對應合理本益比區間估算，再用自由現金流能力做保守交叉驗證。",
        key_assumptions=["獲利維持成長", "現金流品質穩健", "估值倍數未大幅收縮"],
        key_risks=["成長放緩", "估值修正", "產業競爭升高"],
    )


def _clean_buffett3_rating(payload: dict[str, Any]) -> str:
    rating = str(payload.get("rating") or "").strip()
    if rating:
        mapping = {
            "非常昂貴": "高估",
            "昂貴": "高估",
            "合理偏高": "高估",
            "合理": "合理",
            "合理偏低": "低估",
            "便宜": "低估",
            "非常便宜": "低估",
        }
        return mapping.get(rating, rating)
    upside_downside = _safe_float(payload.get("upside_downside_pct"))
    if upside_downside >= 12:
        return "低估"
    if upside_downside <= -12:
        return "高估"
    return "合理"


def _clean_buffett3_action(payload: dict[str, Any]) -> str:
    signal = str(payload.get("signal") or "").strip().lower()
    mapping = {
        "buy": "買進",
        "accumulate": "分批布局",
        "hold": "持有",
        "reduce": "減碼",
        "avoid": "避開",
    }
    if signal in mapping:
        return mapping[signal]
    rating = _clean_buffett3_rating(payload)
    if rating == "低估":
        return "買進"
    if rating == "合理":
        return "持有"
    return "避開"


def _buffett3_comment(profile: SectorProfile) -> str:
    if profile.industry_bucket == "半導體成長股":
        return "Buffett 3.0 對高成長溢價接受度較低，因此結果通常會比市場定價更保守。"
    if profile.industry_bucket == "金融股":
        return "Buffett 3.0 對金融股的股利能力、ROE 與淨值要求較高，因此結果通常偏保守。"
    if profile.industry_bucket == "景氣循環股":
        return "Buffett 3.0 較重視景氣中位數獲利與資產價值，因此不會直接把高峰獲利常態化。"
    return "Buffett 3.0 對防禦型收益資產偏重安全邊際，因此估值通常比市場價格更嚴格。"


def _imfs_conclusion(results: dict[str, str]) -> str:
    gap = _safe_float(results.get("imfs_gap_pct"))
    if gap >= 0.1:
        return "\u5408\u7406\u504f\u4f4e\u4f30"
    if gap <= -0.15:
        return "\u9ad8\u4f30"
    return "\u5408\u7406"


def _imfs_action(results: dict[str, str]) -> str:
    signal = str(results.get("imfs_signal", "")).strip().lower()
    return {
        "discount": "\u504f\u591a",
        "fair_or_rich": "\u4fdd\u5b88",
    }.get(signal, "\u89c0\u5bdf")


def _imfs_comment(profile: SectorProfile) -> str:
    if profile.industry_bucket == "半導體成長股":
        return "IMFS 較能反映高品質成長股的溢價與市場願意給的評價。"
    if profile.industry_bucket == "金融股":
        return "IMFS 對金融股的成長支撐有限，因此估值通常不會像成長股那樣激進。"
    if profile.industry_bucket == "景氣循環股":
        return "IMFS 對景氣循環波動的懲罰較弱，因此結果常比保守模型更樂觀。"
    return "IMFS 對低成長收益型公司通常較保守。"


def _hybrid_conclusion(hybrid_target: float, current_price: float) -> str:
    if not hybrid_target:
        return "\u7121\u8cc7\u6599"
    diff = (hybrid_target - current_price) / current_price if current_price else 0.0
    if diff >= 0.1:
        return "\u504f\u4f4e\u4f30"
    if diff <= -0.1:
        return "\u504f\u9ad8\u4f30"
    return "\u5408\u7406"


def _quant_conclusion(score: float) -> str:
    if score >= 60:
        return "\u504f\u6b63\u5411"
    if score >= 45:
        return "\u4e2d\u6027"
    return "\u504f\u4e2d\u6027\u7565\u5f31"


def _build_news_summary(rows: list[dict[str, str]]) -> str:
    themes = [row.get("theme", "") for row in rows[:3] if row.get("theme")]
    if not themes:
        return "\u8fd1\u671f\u65b0\u805e\u6a23\u672c\u6709\u9650\u3002"
    theme_map = {
        "demand": "\u9700\u6c42\u52d5\u80fd",
        "earnings": "\u7372\u5229\u8207\u71df\u6536",
        "dividend": "\u914d\u606f",
        "industry_cycle": "\u7522\u696d\u5faa\u74b0",
        "guidance": "\u8ca1\u6e2c\u5c55\u671b",
    }
    translated = [theme_map.get(item, item) for item in themes]
    return f"\u8fd1\u671f\u65b0\u805e\u4e3b\u8ef8\u96c6\u4e2d\u5728\uff1a{'\u3001'.join(translated)}\u3002"


def _build_news_sentiment(rows: list[dict[str, str]]) -> str:
    bullish = sum(1 for row in rows if row.get("sentiment") == "bullish")
    bearish = sum(1 for row in rows if row.get("sentiment") == "bearish")
    if bullish > bearish:
        return "\u504f\u591a"
    if bearish > bullish:
        return "\u504f\u7a7a"
    return "\u4e2d\u6027"


def _build_news_comment(profile: SectorProfile, rows: list[dict[str, str]]) -> str:
    if rows:
        sentiment = _build_news_sentiment(rows)
        if sentiment == "偏多":
            return "近期新聞整體偏多，但也代表部分樂觀預期可能已反映在價格中。"
        if sentiment == "偏空":
            return "近期新聞整體偏空，代表市場對這檔標的的短中期風險意識較強。"
        return "近期新聞多空交錯，較適合把它當成脈絡訊號，而不是單一結論依據。"
    if profile.industry_bucket == "金融股":
        return "目前缺少即時新聞摘要時，仍應優先關注配息、淨值與金融市場波動。"
    if profile.industry_bucket == "景氣循環股":
        return "目前缺少即時新聞摘要時，仍應優先關注景氣、運價與供需結構變化。"
    if profile.industry_bucket == "防禦型高股息股":
        return "目前缺少即時新聞摘要時，仍應優先關注配息穩定性與收益資產評價。"
    return "目前缺少即時新聞摘要時，仍應優先關注成長動能、估值與產業地位。"


def _build_public_view(profile: SectorProfile, rows: list[dict[str, str]]) -> str:
    bullish = sum(1 for row in rows if row.get("sentiment") == "bullish")
    if profile.industry_bucket == "半導體成長股":
        return "\u504f\u6b63\u5411\uff0c\u5bb9\u6613\u63a5\u53d7\u53f0\u7a4d\u96fb\u4f5c\u70ba\u9ad8\u54c1\u8cea\u9577\u7dda\u6301\u80a1\u3002"
    if profile.industry_bucket == "金融股":
        return "\u504f\u6b63\u5411\uff0c\u5b58\u80a1\u65cf\u6703\u7279\u5225\u91cd\u8996\u914d\u606f\u8207\u91d1\u63a7\u9f8d\u982d\u5b9a\u4f4d\u3002"
    if profile.industry_bucket == "景氣循環股":
        return "\u504f\u6a02\u89c0\uff0c\u8f03\u5bb9\u6613\u628a\u9ad8\u80a1\u606f\u7576\u6210\u4e3b\u8981\u8cb7\u9032\u7406\u7531\u3002" if bullish else "\u504f\u4fdd\u5b88\u3002"
    return "\u504f\u7a69\u5065\u6b63\u5411\uff0c\u91cd\u8996\u5b58\u80a1\u8207\u914d\u606f\u3002"


def _build_institution_view(profile: SectorProfile, rows: list[dict[str, str]]) -> str:
    buy_count = sum(
        1 for row in rows if row.get("rating_normalized") in {"buy", "outperform", "strong_buy"}
    )
    if profile.industry_bucket == "半導體成長股":
        return "\u504f\u591a\uff0c\u4f46\u66f4\u91cd\u8996\u76ee\u6a19\u50f9\u8207\u7372\u5229\u80fd\u5426\u6301\u7e8c\u9a57\u8b49\u3002"
    if profile.industry_bucket == "金融股":
        return "\u504f\u4e2d\u6027\uff0c\u8a8d\u70ba\u50f9\u683c\u5927\u81f4\u843d\u5728\u5408\u7406\u5340\u9593\uff0c\u7f3a\u4e4f\u660e\u986f\u4f4e\u4f30\u7a7a\u9593\u3002"
    if profile.industry_bucket == "景氣循環股":
        return "\u504f\u4e2d\u6027\uff0c\u8a8d\u70ba\u5408\u7406\u50f9\u5df2\u53cd\u6620\u4e0d\u5c11\u914d\u606f\u8207\u666f\u6c23\u4fee\u5fa9\u9810\u671f\u3002"
    return "\u504f\u4e2d\u6027\uff0c\u5c0d\u9632\u79a6\u578b\u6a19\u7684\u7684\u8a55\u50f9\u591a\u4ee5\u6536\u76ca\u7a69\u5b9a\u6027\u70ba\u4e3b\u3002" if not buy_count else "\u504f\u591a\uff0c\u4f46\u4e0a\u884c\u7a7a\u9593\u4ecd\u53d7\u9650\u3002"


def _build_divergence_summary_clean(
    institutional_rows: list[dict[str, str]],
    public_rows: list[dict[str, str]],
    news_rows: list[dict[str, str]],
) -> str:
    institution_scores = [
        {"strong_buy": 1.0, "buy": 0.7, "outperform": 0.4, "hold": 0.0, "underperform": -0.5, "sell": -1.0}.get(
            row.get("rating_normalized", ""), 0.0
        )
        for row in institutional_rows
    ]
    public_scores = [
        {"buy": 1.0, "accumulate": 0.7, "hold": 0.0, "reduce": -0.5, "avoid": -1.0}.get(
            row.get("stance", "hold"), 0.0
        )
        for row in public_rows
    ]
    news_scores = [
        {"bullish": 1.0, "neutral": 0.0, "bearish": -1.0}.get(row.get("sentiment", "neutral"), 0.0)
        for row in news_rows
    ]
    inst = sum(institution_scores) / len(institution_scores) if institution_scores else 0.0
    pub = sum(public_scores) / len(public_scores) if public_scores else 0.0
    news = sum(news_scores) / len(news_scores) if news_scores else 0.0
    if abs(inst - pub) < 0.25:
        if news > 0.25:
            return "\u6cd5\u4eba\u8207\u516c\u773e\u65b9\u5411\u5927\u81f4\u4e00\u81f4\uff0c\u4e14\u8fd1\u671f\u65b0\u805e\u504f\u591a\u3002"
        if news < -0.25:
            return "\u6cd5\u4eba\u8207\u516c\u773e\u65b9\u5411\u5927\u81f4\u4e00\u81f4\uff0c\u4f46\u8fd1\u671f\u65b0\u805e\u504f\u7a7a\u3002"
        return "\u6cd5\u4eba\u8207\u516c\u773e\u65b9\u5411\u5927\u81f4\u4e00\u81f4\u3002"
    if pub > inst:
        return "\u516c\u773e\u89c0\u9ede\u6bd4\u6cd5\u4eba\u66f4\u6a02\u89c0\u3002"
    return "\u6cd5\u4eba\u89c0\u9ede\u6bd4\u516c\u773e\u66f4\u6a02\u89c0\u3002"


def _model_difference_explanation(profile: SectorProfile) -> str:
    if profile.industry_bucket == "半導體成長股":
        return "Buffett 3.0 \u5c0d\u9ad8\u6210\u9577\u6ea2\u50f9\u63a5\u53d7\u5ea6\u4f4e\uff0c\u56e0\u6b64\u4f30\u503c\u986f\u8457\u504f\u4f4e\uff1bIMFS \u8207\u7368\u7acb AI \u4f30\u503c\u8f03\u80fd\u53cd\u6620\u5e02\u5834\u5c0d AI \u8207\u7522\u696d\u5730\u4f4d\u7d66\u4e88\u7684\u6ea2\u50f9\uff1bHybrid \u5247\u843d\u5728\u4e2d\u9593\u5340\u9593\u3002"
    if profile.industry_bucket == "金融股":
        return "Buffett 3.0 \u8207 IMFS \u5c0d\u91d1\u878d\u80a1\u8f03\u4fdd\u5b88\uff0c\u5c0d\u914d\u606f\u8207 ROE \u8981\u6c42\u8f03\u9ad8\uff1bHybrid \u8207\u7368\u7acb AI \u66f4\u63a5\u8fd1\u5e02\u5834\u5c0d\u91d1\u63a7\u80a1\u300e\u5408\u7406\u4f46\u4e0d\u4fbf\u5b9c\u300f\u7684\u770b\u6cd5\u3002"
    if profile.industry_bucket == "景氣循環股":
        return "Buffett 3.0 \u8207 Hybrid \u5c0d\u9577\u69ae\u8f03\u63a5\u8fd1\uff0c\u56e0\u70ba\u5b83\u5011\u6c92\u6709\u628a\u666f\u6c23\u9ad8\u5cf0\u7372\u5229\u5b8c\u5168\u5e38\u614b\u5316\uff1bIMFS \u7684\u7d50\u679c\u986f\u8457\u504f\u9ad8\uff0c\u8f03\u5bb9\u6613\u9ad8\u4f30\u9ad8\u5ea6\u5faa\u74b0\u80a1\u3002"
    return "Buffett 3.0 \u8207 IMFS \u5c0d\u4e2d\u83ef\u96fb\u4fe1\u504f\u4fdd\u5b88\uff0c\u56e0\u70ba\u9019\u985e\u516c\u53f8\u6210\u9577\u6027\u6709\u9650\uff1bHybrid \u8207\u7368\u7acb AI \u8f03\u80fd\u53cd\u6620\u9632\u79a6\u578b\u8cc7\u7522\u5728\u5e02\u5834\u4e2d\u7684\u5408\u7406\u6ea2\u50f9\u3002"


def _build_final_summary(
    ticker: str,
    profile: SectorProfile,
    action_label: str,
    current_price: float,
    fair_value_base: float,
) -> str:
    if profile.industry_bucket == "半導體成長股":
        return f"{profile.company_name} 是高品質公司，但以目前股價 {current_price:.1f} 元對照獨立 AI 基準合理價 {fair_value_base:.1f} 元來看，較適合{action_label}，不宜追價。"
    if profile.industry_bucket == "金融股":
        return f"{profile.company_name} 屬於可持有的金融股，但以目前股價 {current_price:.1f} 元來看不算便宜，較適合{action_label}或等待更佳殖利率。"
    if profile.industry_bucket == "景氣循環股":
        return f"{profile.company_name} 目前較像合理區間內的高波動收益型標的，較適合{action_label}，不要把高股息直接等同於低風險。"
    if profile.industry_bucket == "防禦型高股息股":
        return f"{profile.company_name} 屬於穩定收益型標的，目前股價 {current_price:.1f} 元已接近合理區上緣，較適合作為防守配置{action_label}。"
    return f"{profile.company_name} 目前股價 {current_price:.1f} 元相對獨立 AI 基準合理價 {fair_value_base:.1f} 元，較適合採取 {action_label} 策略，避免在缺乏安全邊際時追價。"


def _change_conditions(profile: SectorProfile) -> list[str]:
    if profile.industry_bucket == "半導體成長股":
        return [
            "\u82e5\u80a1\u50f9\u986f\u8457\u4f4e\u65bc\u5408\u7406\u5340\u4e0b\u7de3\uff0c\u53ef\u8f49\u70ba\u504f\u591a\u3002",
            "\u82e5 AI \u9700\u6c42\u8207\u7372\u5229\u5c55\u671b\u518d\u660e\u986f\u4e0a\u4fee\uff0c\u5408\u7406\u50f9\u53ef\u4e0a\u8abf\u3002",
            "\u82e5\u9700\u6c42\u8207\u6bdb\u5229\u7387\u8f49\u5f31\uff0c\u61c9\u4e0b\u4fee\u8a55\u50f9\u3002",
        ]
    if profile.industry_bucket == "金融股":
        return [
            "\u82e5\u80a1\u50f9\u56de\u843d\u4e14\u6b96\u5229\u7387\u660e\u986f\u63d0\u5347\uff0c\u53ef\u8f49\u70ba\u504f\u591a\u3002",
            "\u82e5 ROE \u6301\u7e8c\u63d0\u5347\u4e14\u5e02\u5834\u7d66\u4e88\u66f4\u9ad8 PB\uff0c\u5408\u7406\u50f9\u53ef\u4e0a\u4fee\u3002",
            "\u82e5\u914d\u606f\u80fd\u529b\u8f49\u5f31\u6216\u6de8\u503c\u58d3\u529b\u5347\u9ad8\uff0c\u61c9\u4e0b\u4fee\u8a55\u50f9\u3002",
        ]
    if profile.industry_bucket == "景氣循環股":
        return [
            "\u82e5\u80a1\u50f9\u8dcc\u7834\u5408\u7406\u5340\u4e0b\u7de3\u4e14\u914d\u606f\u80fd\u529b\u672a\u60e1\u5316\uff0c\u53ef\u8f49\u70ba\u504f\u591a\u3002",
            "\u82e5\u666f\u6c23\u8207\u904b\u50f9\u6301\u7e8c\u512a\u65bc\u4e2d\u4f4d\u6578\uff0c\u5408\u7406\u50f9\u53ef\u5c0f\u5e45\u4e0a\u4fee\u3002",
            "\u82e5\u5168\u7403\u666f\u6c23\u8f49\u5f31\u6216\u4f9b\u7d66\u58d3\u529b\u52a0\u91cd\uff0c\u61c9\u4e0b\u4fee\u8a55\u50f9\u3002",
        ]
    if profile.industry_bucket == "防禦型高股息股":
        return [
            "\u82e5\u80a1\u50f9\u56de\u843d\u4e14\u6b96\u5229\u7387\u63d0\u5347\uff0c\u53ef\u8f49\u70ba\u504f\u591a\u3002",
            "\u82e5\u914d\u606f\u80fd\u529b\u6216\u73fe\u91d1\u6d41\u54c1\u8cea\u512a\u65bc\u9810\u671f\uff0c\u53ef\u5c0f\u5e45\u4e0a\u4fee\u5408\u7406\u50f9\u3002",
            "\u82e5\u6536\u76ca\u7a69\u5b9a\u6027\u53d7\u640d\uff0c\u61c9\u4e0b\u4fee\u8a55\u50f9\u3002",
        ]
    return [
        "\u82e5\u80a1\u50f9\u56de\u843d\u4e14\u6b96\u5229\u7387\u63d0\u5347\uff0c\u53ef\u8f49\u70ba\u504f\u591a\u3002",
        "\u82e5\u7372\u5229\u80fd\u898b\u5ea6\u6216\u6210\u9577\u8def\u5f91\u512a\u65bc\u9810\u671f\uff0c\u53ef\u5c0f\u5e45\u4e0a\u4fee\u5408\u7406\u50f9\u3002",
        "\u82e5\u57fa\u672c\u9762\u8f49\u5f31\u6216\u4f30\u503c\u58d3\u529b\u660e\u986f\u5347\u9ad8\uff0c\u61c9\u4e0b\u4fee\u8a55\u50f9\u3002",
    ]
