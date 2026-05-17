from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AdapterReadiness:
    status: str
    warnings: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)


@dataclass
class AdapterBundle:
    model_id: str
    ticker: str
    readiness: AdapterReadiness
    generated_files: dict[str, str]
    metadata: dict[str, object]
