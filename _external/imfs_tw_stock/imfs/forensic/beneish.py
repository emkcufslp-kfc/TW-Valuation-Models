"""Beneish M-score contract and calculation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BeneishInputs:
    dsri: float
    gmi: float
    aqi: float
    sgi: float
    depi: float
    sgai: float
    lvgi: float
    tata: float


@dataclass(frozen=True)
class BeneishResult:
    score: float | None
    label: str
    warnings: tuple[str, ...] = ()

    @property
    def red_flag(self) -> bool:
        return self.label == "manipulation_risk"


MANIPULATION_RISK_THRESHOLD = -2.22


def beneish_m_score(inputs: BeneishInputs | None) -> BeneishResult:
    if inputs is None:
        return BeneishResult(None, "insufficient_data", ("missing Beneish inputs",))
    score = (
        -4.84
        + 0.920 * inputs.dsri
        + 0.528 * inputs.gmi
        + 0.404 * inputs.aqi
        + 0.892 * inputs.sgi
        + 0.115 * inputs.depi
        - 0.172 * inputs.sgai
        + 4.679 * inputs.tata
        - 0.327 * inputs.lvgi
    )
    label = "manipulation_risk" if score > MANIPULATION_RISK_THRESHOLD else "clean"
    return BeneishResult(score, label)
