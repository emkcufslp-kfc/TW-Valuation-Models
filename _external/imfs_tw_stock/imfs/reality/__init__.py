"""Reality-validation overlay exports."""

from imfs.reality.models import (
    AuditEvent,
    BlockedAdjustment,
    DecisionHint,
    GapSeverity,
    RealityOverlayInput,
    RealityOverlayResult,
)
from imfs.reality.overlay import classify_gap_severity, derive_decision_hint, run_reality_overlay

__all__ = [
    "AuditEvent",
    "BlockedAdjustment",
    "DecisionHint",
    "GapSeverity",
    "RealityOverlayInput",
    "RealityOverlayResult",
    "classify_gap_severity",
    "derive_decision_hint",
    "run_reality_overlay",
]
