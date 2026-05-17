from __future__ import annotations

import importlib
import sys
from pathlib import Path

from .config import WorkspacePaths


def add_source_paths(paths: WorkspacePaths) -> dict[str, Path]:
    roots = {
        "imfs": paths.imfs_source_root,
        "tw_buffett_quant": paths.quant_source_root,
        "tw_hybrid": paths.hybrid_source_root,
    }
    for root in roots.values():
        if root.exists() and str(root) not in sys.path:
            sys.path.insert(0, str(root))
    return roots


def import_imfs_modules(paths: WorkspacePaths) -> dict[str, object]:
    roots = add_source_paths(paths)
    _require_source_root("IMFS", roots["imfs"])
    return {
        "models": importlib.import_module("imfs.data.models"),
        "routing": importlib.import_module("imfs.routing.route_classifier"),
        "engine": importlib.import_module("imfs.valuation.engine"),
    }


def import_tw_buffett_quant_modules(paths: WorkspacePaths) -> dict[str, object]:
    roots = add_source_paths(paths)
    _require_source_root("TW Buffett Quant", roots["tw_buffett_quant"])
    return {
        "strict_mode": importlib.import_module("strict_mode_engine"),
        "criteria": importlib.import_module("criteria_config"),
    }


def import_tw_hybrid_modules(paths: WorkspacePaths) -> dict[str, object]:
    roots = add_source_paths(paths)
    _require_source_root("TW Hybrid", roots["tw_hybrid"])
    return {
        "strategy": importlib.import_module("strategy"),
    }


def _require_source_root(model_name: str, root: Path) -> None:
    if root.exists():
        return
    raise FileNotFoundError(
        f"{model_name} source root not found: {root}. "
        "Set the corresponding TVM_*_SOURCE_ROOT environment variable or place the source under _external/."
    )
