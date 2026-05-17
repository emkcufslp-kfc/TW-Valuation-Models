from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def summarize_manifest_for_ticker(manifest: dict[str, Any], ticker: str) -> dict[str, Any]:
    ticker_text = str(ticker or "").strip()
    if not ticker_text:
        return {"statement_route": "unknown", "domain_coverage": [], "covered_domains": [], "missing_domains": []}

    financial_tickers = {str(item) for item in manifest.get("financial_tickers", [])}
    statement_route = "financial" if ticker_text in financial_tickers else "general"

    domain_rows: list[dict[str, Any]] = []
    for entry in manifest.get("entries", []):
        requested = {str(item) for item in entry.get("requested_tickers", [])}
        covered = {str(item) for item in entry.get("covered_tickers", [])}
        missing = {str(item) for item in entry.get("missing_tickers", [])}

        if ticker_text in covered:
            coverage_status = "covered"
        elif ticker_text in missing:
            coverage_status = "missing"
        elif ticker_text in requested:
            coverage_status = "requested_not_materialized"
        else:
            coverage_status = "not_requested"

        domain_rows.append(
            {
                "domain": entry.get("domain"),
                "source_name": entry.get("source_name"),
                "target_file": Path(str(entry.get("target_path", ""))).name if entry.get("target_path") else None,
                "row_count": entry.get("row_count"),
                "coverage_status": coverage_status,
                "requested_for_ticker": ticker_text in requested,
                "covered_for_ticker": ticker_text in covered,
                "missing_for_ticker": ticker_text in missing,
                "covered_count": len(covered),
                "missing_count": len(missing),
            }
        )

    return {
        "statement_route": statement_route,
        "domain_coverage": domain_rows,
        "covered_domains": [row["domain"] for row in domain_rows if row["coverage_status"] == "covered"],
        "missing_domains": [row["domain"] for row in domain_rows if row["coverage_status"] == "missing"],
    }


def build_buffett3_export_notes(payload: dict[str, Any]) -> dict[str, Any]:
    valuation_legs = payload.get("valuation_legs", [])
    modifiers = payload.get("modifiers", {})
    ready_legs: list[dict[str, Any]] = []
    pending_legs: list[dict[str, Any]] = []

    for leg in valuation_legs:
        simplified = {
            "name": leg.get("name"),
            "status": leg.get("status"),
            "weight": leg.get("weight"),
            "blended_value": leg.get("blended_value"),
            "notes": leg.get("notes", []),
        }
        if str(leg.get("status", "")).lower() == "ready":
            ready_legs.append(simplified)
        else:
            pending_legs.append(simplified)

    modifier_rows = []
    for name, modifier in modifiers.items():
        modifier_rows.append(
            {
                "name": name,
                "selected_bucket": modifier.get("selected_bucket"),
                "modifier_value": modifier.get("modifier_value"),
                "reason": modifier.get("reason"),
                "data_source": modifier.get("data_source"),
            }
        )

    takeaways = [
        {
            "topic": "classification",
            "value": payload.get("classification"),
            "reason": payload.get("classification_reason"),
        },
        {
            "topic": "valuation_leg_readiness",
            "ready_leg_count": len(ready_legs),
            "pending_leg_count": len(pending_legs),
        },
        {
            "topic": "risk_flags",
            "data_quality_flags": payload.get("data_quality_flags", []),
            "manual_review_flags": payload.get("manual_review_flags", []),
        },
    ]

    blockers = payload.get("normalized_inputs", {}).get("cyclical_ev_ebitda_blockers", [])
    if blockers:
        takeaways.append({"topic": "cyclical_ev_ebitda_blockers", "blockers": blockers})

    return {
        "ready_valuation_legs": ready_legs,
        "pending_valuation_legs": pending_legs,
        "modifier_summary": modifier_rows,
        "takeaways": takeaways,
    }


def build_model_ranking_comparison(results_df: pd.DataFrame, top_n: int = 20) -> dict[str, Any]:
    specs = {
        "buffett3": {"column": "buffett3_mos", "ascending": False, "label": "Buffett 3.0", "metric_label": "margin_of_safety_pct"},
        "quant": {"column": "quant_score", "ascending": False, "label": "Quant", "metric_label": "score"},
        "hybrid": {"column": "hybrid_return_pct", "ascending": False, "label": "Hybrid", "metric_label": "expected_return_pct"},
    }

    rankings: dict[str, list[dict[str, Any]]] = {}
    for model_id, spec in specs.items():
        subset = results_df[["ticker", "name", spec["column"]]].copy()
        subset = subset.dropna(subset=[spec["column"]]).sort_values(spec["column"], ascending=spec["ascending"]).head(top_n)
        rows = []
        for index, (_, row) in enumerate(subset.iterrows(), start=1):
            rows.append(
                {
                    "rank": index,
                    "ticker": str(row["ticker"]),
                    "name": row["name"],
                    spec["metric_label"]: float(row[spec["column"]]),
                }
            )
        rankings[model_id] = rows

    pairwise = []
    model_ids = list(specs.keys())
    for left_index in range(len(model_ids)):
        for right_index in range(left_index + 1, len(model_ids)):
            left_id = model_ids[left_index]
            right_id = model_ids[right_index]
            left_tickers = [row["ticker"] for row in rankings[left_id]]
            right_tickers = [row["ticker"] for row in rankings[right_id]]
            overlap = [ticker for ticker in left_tickers if ticker in set(right_tickers)]
            pairwise.append(
                {
                    "left_model": specs[left_id]["label"],
                    "right_model": specs[right_id]["label"],
                    "top_n": top_n,
                    "overlap_count": len(overlap),
                    "overlap_tickers": overlap,
                }
            )

    shared_top = set(rankings[model_ids[0]][i]["ticker"] for i in range(len(rankings[model_ids[0]]))) if rankings[model_ids[0]] else set()
    for model_id in model_ids[1:]:
        shared_top &= {row["ticker"] for row in rankings[model_id]}

    return {
        "top_n": top_n,
        "models": {model_id: {"label": specs[model_id]["label"], "metric_label": specs[model_id]["metric_label"], "rankings": rankings[model_id]} for model_id in model_ids},
        "pairwise_overlap": pairwise,
        "shared_top_tickers_all_models": sorted(shared_top),
    }
