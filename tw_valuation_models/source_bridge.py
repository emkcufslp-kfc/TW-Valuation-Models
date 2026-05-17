from __future__ import annotations

import importlib
import sys
from pathlib import Path

from .config import WorkspacePaths


def add_source_paths(paths: WorkspacePaths) -> dict[str, Path]:
    roots = {
        "imfs": Path(r"D:\Claude projects\IMFS_TW_Stock"),
        "tw_buffett_quant": Path(r"D:\Claude projects\TWSE aihedge\tw-buffett-quant-app"),
        "tw_hybrid": Path(
            r"D:\Claude projects\TW hybrid model\台股法說會估值\Taiwwan-stock-hybrid-model"
        ),
    }
    for root in roots.values():
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
    return roots


def import_imfs_modules(paths: WorkspacePaths) -> dict[str, object]:
    add_source_paths(paths)
    return {
        "models": importlib.import_module("imfs.data.models"),
        "routing": importlib.import_module("imfs.routing.route_classifier"),
        "engine": importlib.import_module("imfs.valuation.engine"),
    }


def import_tw_buffett_quant_modules(paths: WorkspacePaths) -> dict[str, object]:
    add_source_paths(paths)
    return {
        "strict_mode": importlib.import_module("strict_mode_engine"),
        "criteria": importlib.import_module("criteria_config"),
    }


def import_tw_hybrid_modules(paths: WorkspacePaths) -> dict[str, object]:
    add_source_paths(paths)
    return {
        "strategy": importlib.import_module("strategy"),
    }
