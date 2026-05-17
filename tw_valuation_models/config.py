from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _module_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser() if value else default


DEFAULT_WORKSPACE_ROOT = _path_from_env("TVM_WORKSPACE_ROOT", _module_workspace_root())
DEFAULT_SHARED_DATA_ROOT = _path_from_env(
    "TVM_SHARED_DATA_ROOT",
    DEFAULT_WORKSPACE_ROOT / "artifacts" / "shared_data",
)
DEFAULT_SOURCE_MODEL_ROOT = _path_from_env(
    "TVM_SOURCE_MODEL_ROOT",
    DEFAULT_WORKSPACE_ROOT / "_external" / "tw_hybrid_model",
)


@dataclass(frozen=True)
class WorkspacePaths:
    workspace_root: Path
    shared_data_root: Path = DEFAULT_SHARED_DATA_ROOT
    source_model_root: Path = DEFAULT_SOURCE_MODEL_ROOT

    @property
    def artifacts_root(self) -> Path:
        return self.workspace_root / "artifacts"

    @property
    def normalized_root(self) -> Path:
        return self.artifacts_root / "normalized"

    @property
    def validation_root(self) -> Path:
        return self.artifacts_root / "validation"

    @property
    def model_inputs_root(self) -> Path:
        return self.artifacts_root / "model_inputs"

    @property
    def runtime_root(self) -> Path:
        return self.artifacts_root / "runtime"

    @property
    def on_demand_root(self) -> Path:
        return self.runtime_root / "on_demand"

    @property
    def on_demand_results_root(self) -> Path:
        return self.on_demand_root / "model_results"

    @property
    def on_demand_datasets_root(self) -> Path:
        return self.on_demand_root / "datasets"

    @property
    def external_models_root(self) -> Path:
        return self.workspace_root / "_external"

    @property
    def imfs_source_root(self) -> Path:
        return _path_from_env(
            "TVM_IMFS_SOURCE_ROOT",
            self.external_models_root / "imfs_tw_stock",
        )

    @property
    def quant_source_root(self) -> Path:
        return _path_from_env(
            "TVM_QUANT_SOURCE_ROOT",
            self.external_models_root / "tw_buffett_quant",
        )

    @property
    def hybrid_source_root(self) -> Path:
        return _path_from_env(
            "TVM_HYBRID_SOURCE_ROOT",
            self.source_model_root,
        )

    @property
    def final_module_shared_root(self) -> Path:
        return self.shared_data_root / "final_module"

    @property
    def final_module_raw_root(self) -> Path:
        return self.final_module_shared_root / "raw"

    @property
    def final_module_manifest_root(self) -> Path:
        return self.final_module_shared_root / "manifests"

    @property
    def final_module_artifacts_root(self) -> Path:
        return self.artifacts_root / "final_module"

    @property
    def final_module_normalized_root(self) -> Path:
        return self.final_module_artifacts_root / "normalized"

    @property
    def final_module_payload_root(self) -> Path:
        return self.final_module_artifacts_root / "payloads"

    @property
    def final_module_independent_ai_root(self) -> Path:
        return self.final_module_payload_root / "independent_ai"

    @property
    def final_module_commentary_root(self) -> Path:
        return self.final_module_payload_root / "final_commentary"
