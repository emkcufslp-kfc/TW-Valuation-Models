from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters.tw_hybrid import (
    check_tw_hybrid_runtime,
    prepare_tw_hybrid_bundle,
    probe_tw_hybrid_strategy,
)
from .config import (
    DEFAULT_SHARED_DATA_ROOT,
    DEFAULT_SOURCE_MODEL_ROOT,
    DEFAULT_WORKSPACE_ROOT,
    WorkspacePaths,
)
from .dataset import build_top100_dataset
from .deps import bootstrap_local_deps
from .final_module_data import (
    build_final_module_snapshot,
    fetch_final_module_sources,
    run_final_module_pilot,
)
from .final_module_payloads import build_final_module_payloads
from .portfolio_builder import build_all_model_results
from .shared_data import discover_shared_data, normalize_shared_data, validate_shared_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TW valuation models integration CLI")
    parser.add_argument(
        "--workspace-root",
        default=str(DEFAULT_WORKSPACE_ROOT),
        help="Workspace root for artifacts output.",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="Override shared data root.",
    )
    parser.add_argument(
        "--source-model-root",
        default=None,
        help="Override source model root for adapter preparation.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("discover", help="Inspect shared data layout.")
    subparsers.add_parser("normalize", help="Build normalized tables under artifacts.")
    subparsers.add_parser("validate", help="Run validation on normalized tables.")

    top100_parser = subparsers.add_parser(
        "build-top100", help="Build the integrated TOP100 dataset and download missing inputs."
    )
    top100_parser.add_argument("--top-n", type=int, default=100, help="Number of TW stocks to include.")

    results_parser = subparsers.add_parser(
        "build-results", help="Run all integrated model wrappers for the TOP100 dataset."
    )
    results_parser.add_argument("--top-n", type=int, default=100, help="Number of TW stocks to include.")

    run_all_parser = subparsers.add_parser(
        "run-all",
        help="Run normalization, validation, TOP100 dataset build, and model result generation.",
    )
    run_all_parser.add_argument("--top-n", type=int, default=100, help="Number of TW stocks to include.")

    prepare_parser = subparsers.add_parser(
        "prepare-tw-hybrid", help="Prepare shared-data bundle for TW hybrid model."
    )
    prepare_parser.add_argument("--ticker", required=True, help="TW ticker, e.g. 2330")
    final_fetch_parser = subparsers.add_parser(
        "fetch-final-module-sources",
        help="Download pilot final-module source pages into the shared data root.",
    )
    final_fetch_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Optional ticker filter, e.g. 2330 2881",
    )
    final_fetch_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download raw source files even if cached locally.",
    )
    final_build_parser = subparsers.add_parser(
        "build-final-module-snapshot",
        help="Build final-module normalized tables from the curated pilot source catalog.",
    )
    final_build_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Optional ticker filter, e.g. 2330 2881",
    )
    final_run_parser = subparsers.add_parser(
        "run-final-module-pilot",
        help="Download pilot final-module sources and build normalized snapshot tables.",
    )
    final_run_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Optional ticker filter, e.g. 2330 2881",
    )
    final_run_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download raw source files even if cached locally.",
    )
    final_payload_parser = subparsers.add_parser(
        "build-final-module-payloads",
        help="Build independent AI and final commentary payloads for the final-module pilot tickers.",
    )
    final_payload_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Optional ticker filter, e.g. 2330 2881",
    )
    subparsers.add_parser(
        "check-tw-hybrid-runtime",
        help="Inspect whether the local environment can execute the source TW hybrid model.",
    )
    probe_parser = subparsers.add_parser(
        "probe-tw-hybrid",
        help="Load the source TW hybrid strategy and run its feature engineering on a prepared bundle.",
    )
    probe_parser.add_argument("--ticker", required=True, help="TW ticker, e.g. 2330")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    bootstrap_local_deps(Path(args.workspace_root))
    paths = WorkspacePaths(
        workspace_root=Path(args.workspace_root),
        shared_data_root=Path(args.data_root) if args.data_root else DEFAULT_SHARED_DATA_ROOT,
        source_model_root=Path(args.source_model_root) if args.source_model_root else DEFAULT_SOURCE_MODEL_ROOT,
    )

    if args.command == "discover":
        print(json.dumps(discover_shared_data(paths), indent=2, ensure_ascii=False))
        return 0
    if args.command == "normalize":
        print(json.dumps(normalize_shared_data(paths), indent=2, ensure_ascii=False))
        return 0
    if args.command == "validate":
        print(json.dumps(validate_shared_data(paths), indent=2, ensure_ascii=False))
        return 0
    if args.command == "build-top100":
        print(json.dumps(build_top100_dataset(paths, top_n=args.top_n), indent=2, ensure_ascii=False))
        return 0
    if args.command == "build-results":
        print(json.dumps(build_all_model_results(paths, top_n=args.top_n), indent=2, ensure_ascii=False))
        return 0
    if args.command == "run-all":
        payload = {
            "normalize": normalize_shared_data(paths),
            "validate": validate_shared_data(paths),
            "build_top100": build_top100_dataset(paths, top_n=args.top_n),
            "build_results": build_all_model_results(paths, top_n=args.top_n),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if args.command == "prepare-tw-hybrid":
        bundle = prepare_tw_hybrid_bundle(paths, ticker=args.ticker)
        print(
            json.dumps(
                {
                    "model_id": bundle.model_id,
                    "ticker": bundle.ticker,
                    "readiness": {
                        "status": bundle.readiness.status,
                        "warnings": bundle.readiness.warnings,
                        "missing_inputs": bundle.readiness.missing_inputs,
                    },
                    "generated_files": bundle.generated_files,
                    "metadata": bundle.metadata,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "fetch-final-module-sources":
        print(
            json.dumps(
                fetch_final_module_sources(
                    paths, tickers=args.tickers, overwrite=args.overwrite
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "build-final-module-snapshot":
        print(
            json.dumps(
                build_final_module_snapshot(paths, tickers=args.tickers),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "run-final-module-pilot":
        print(
            json.dumps(
                run_final_module_pilot(
                    paths, tickers=args.tickers, overwrite=args.overwrite
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "build-final-module-payloads":
        print(
            json.dumps(
                build_final_module_payloads(paths, tickers=args.tickers),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "check-tw-hybrid-runtime":
        print(json.dumps(check_tw_hybrid_runtime(paths), indent=2, ensure_ascii=False))
        return 0
    if args.command == "probe-tw-hybrid":
        print(json.dumps(probe_tw_hybrid_strategy(paths, ticker=args.ticker), indent=2, ensure_ascii=False))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
