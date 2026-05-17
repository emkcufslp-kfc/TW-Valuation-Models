from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_SHARED_DATA_ROOT = Path(r"D:\Claude projects\主觀看盤\data")
DEFAULT_SOURCE_MODEL_ROOT = Path(
    r"D:\Claude projects\TW hybrid model\台股法說會估值\Taiwwan-stock-hybrid-model"
)
DEFAULT_WORKSPACE_ROOT = Path(r"D:\Codex projects\TW Valuation models")


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
