from __future__ import annotations

import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

from .base import AdapterBundle, AdapterReadiness
from ..config import WorkspacePaths
from ..csv_utils import read_csv_rows, write_csv_rows


def prepare_tw_hybrid_bundle(paths: WorkspacePaths, ticker: str) -> AdapterBundle:
    normalized_root = paths.normalized_root
    if not normalized_root.exists():
        raise FileNotFoundError(
            "Normalized data directory not found. Run normalize before preparing a model bundle."
        )

    bundle_root = paths.model_inputs_root / "tw_hybrid_model" / ticker
    bundle_root.mkdir(parents=True, exist_ok=True)

    price_rows = [
        row
        for row in read_csv_rows(normalized_root / "price_daily.csv")
        if row["ticker"] == ticker
    ]
    benchmark_rows = read_csv_rows(normalized_root / "benchmark_daily.csv")
    valuation_row = _find_first(
        read_csv_rows(normalized_root / "valuation_snapshot.csv"), "ticker", ticker
    )
    fundamentals_row = _find_first(
        read_csv_rows(normalized_root / "fundamentals_snapshot.csv"), "ticker", ticker
    )
    universe_row = _find_first(
        read_csv_rows(normalized_root / "universe_snapshot.csv"), "ticker", ticker
    )

    missing_inputs: list[str] = []
    warnings: list[str] = []

    if not price_rows:
        missing_inputs.append("price_daily")
    if not benchmark_rows:
        missing_inputs.append("benchmark_daily")
    if not valuation_row:
        warnings.append("valuation snapshot is missing for this ticker")
    if not fundamentals_row:
        warnings.append("fundamentals snapshot is missing for this ticker")
    else:
        warnings.append(
            "fundamentals are currently a snapshot without fiscal period metadata"
        )
    if valuation_row:
        warnings.append("valuation data is currently a snapshot without historical dates")
    if price_rows:
        warnings.append("adjusted_close is not available in the current shared price source")

    readiness = AdapterReadiness(
        status="ready" if not missing_inputs else "blocked",
        warnings=warnings,
        missing_inputs=missing_inputs,
    )

    generated_files = {
        "price_history": str(bundle_root / "price_history.csv"),
        "benchmark_history": str(bundle_root / "benchmark_history.csv"),
        "context": str(bundle_root / "context.json"),
    }

    if price_rows:
        write_csv_rows(
            Path(generated_files["price_history"]),
            list(price_rows[0].keys()),
            price_rows,
        )
    if benchmark_rows:
        write_csv_rows(
            Path(generated_files["benchmark_history"]),
            list(benchmark_rows[0].keys()),
            benchmark_rows,
        )

    context = {
        "model_id": "tw_hybrid_model",
        "ticker": ticker,
        "generated_from": str(paths.normalized_root),
        "source_model_root": str(paths.source_model_root),
        "readiness": asdict(readiness),
        "runtime_check": check_tw_hybrid_runtime(paths),
        "universe_snapshot": universe_row,
        "valuation_snapshot": valuation_row,
        "fundamentals_snapshot": fundamentals_row,
        "notes": [
            "This bundle prepares shared data for the TW hybrid model without rewriting model logic.",
            "The original source model still needs its own runtime dependencies before direct execution.",
        ],
    }
    Path(generated_files["context"]).write_text(
        json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return AdapterBundle(
        model_id="tw_hybrid_model",
        ticker=ticker,
        readiness=readiness,
        generated_files=generated_files,
        metadata={
            "price_rows": len(price_rows),
            "benchmark_rows": len(benchmark_rows),
            "has_universe_snapshot": universe_row is not None,
            "has_valuation_snapshot": valuation_row is not None,
            "has_fundamentals_snapshot": fundamentals_row is not None,
        },
    )


def check_tw_hybrid_runtime(paths: WorkspacePaths) -> dict[str, object]:
    required_modules = [
        "pandas",
        "numpy",
        "streamlit",
        "sklearn",
        "xgboost",
        "backtrader",
        "yfinance",
        "matplotlib",
        "requests",
    ]
    availability = {}
    for module_name in required_modules:
        availability[module_name] = importlib.util.find_spec(module_name) is not None

    strategy_path = paths.source_model_root / "strategy.py"
    app_path = paths.source_model_root / "app.py"
    missing_modules = [name for name, ok in availability.items() if not ok]
    import_check = _probe_strategy_import(strategy_path) if not missing_modules else {
        "importable": False,
        "error": "missing runtime modules",
    }
    return {
        "source_model_root_exists": paths.source_model_root.exists(),
        "strategy_py_exists": strategy_path.exists(),
        "app_py_exists": app_path.exists(),
        "module_availability": availability,
        "missing_modules": missing_modules,
        "strategy_import_check": import_check,
        "status": "ready"
        if not missing_modules and strategy_path.exists() and import_check.get("importable")
        else "blocked",
    }


def probe_tw_hybrid_strategy(paths: WorkspacePaths, ticker: str) -> dict[str, object]:
    runtime = check_tw_hybrid_runtime(paths)
    if runtime["status"] != "ready":
        return {
            "ticker": ticker,
            "status": "blocked",
            "runtime_check": runtime,
        }

    price_history_path = (
        paths.model_inputs_root / "tw_hybrid_model" / ticker / "price_history.csv"
    )
    if not price_history_path.exists():
        raise FileNotFoundError(
            "Price history bundle not found. Run prepare-tw-hybrid before probe."
        )

    import pandas as pd

    module_name = f"tw_hybrid_strategy_probe_{ticker}"
    strategy_module = _load_strategy_module(paths.source_model_root / "strategy.py", module_name)

    df = pd.read_csv(price_history_path)
    df = df.rename(
        columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]
    feature_df = strategy_module.compute_technical_features(df)
    latest = feature_df.dropna().iloc[-1]
    return {
        "ticker": ticker,
        "status": "ok",
        "source_strategy": str(paths.source_model_root / "strategy.py"),
        "feature_row_count": int(len(feature_df)),
        "latest_feature_date": str(feature_df.dropna().index[-1].date()),
        "latest_feature_snapshot": {
            "Close": float(latest["Close"]),
            "ret_20d": float(latest["ret_20d"]),
            "ma20_ratio": float(latest["ma20_ratio"]),
            "vol_20d": float(latest["vol_20d"]),
            "rsi14": float(latest["rsi14"]),
            "bb_pos": float(latest["bb_pos"]),
        },
    }


def _find_first(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str] | None:
    for row in rows:
        if row.get(key) == value:
            return row
    return None


def _probe_strategy_import(strategy_path: Path) -> dict[str, object]:
    if not strategy_path.exists():
        return {"importable": False, "error": "strategy.py not found"}
    try:
        module = _load_strategy_module(strategy_path, "tw_hybrid_strategy_runtime_check")
        return {
            "importable": True,
            "has_compute_technical_features": hasattr(module, "compute_technical_features"),
        }
    except Exception as exc:  # pragma: no cover - surfaced in runtime output
        return {"importable": False, "error": f"{type(exc).__name__}: {exc}"}


def _load_strategy_module(strategy_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, strategy_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create spec for {strategy_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
