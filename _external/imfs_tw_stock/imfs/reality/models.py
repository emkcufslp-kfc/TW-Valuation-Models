"""Reality-validation overlay contracts for Phase 5A."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from imfs.data.models import FinancialSnapshot, PriceRecord, SecurityProfile
from imfs.decision import Decision
from imfs.forensic import ForensicReport
from imfs.routing import RouteDecision
from imfs.valuation import ValuationResult


class GapSeverity(str, Enum):
    UNAVAILABLE = "unavailable"
    IMMATERIAL = "immaterial"
    MINOR = "minor"
    MATERIAL = "material"
    SEVERE = "severe"


class DecisionHint(str, Enum):
    NEEDS_MANUAL_REVIEW = "needs_manual_review"
    IMPROVE_DATA_QUALITY = "improve_data_quality"
    FORENSIC_CAUTION = "forensic_caution"
    REVIEW_UPSIDE = "review_upside"
    REVIEW_DOWNSIDE = "review_downside"
    MONITOR = "monitor"


@dataclass(frozen=True)
class AuditEvent:
    rule_id: str
    outcome: str
    message: str


@dataclass(frozen=True)
class BlockedAdjustment:
    rule_id: str
    reason: str


@dataclass(frozen=True)
class RealityOverlayInput:
    profile: SecurityProfile
    price: PriceRecord
    financials: FinancialSnapshot
    route: RouteDecision
    valuation: ValuationResult
    forensic: ForensicReport
    decision: Decision


@dataclass(frozen=True)
class RealityOverlayResult:
    ticker: str
    original_fair_value: float | None
    adjusted_fair_value: float | None
    gap_severity: GapSeverity
    decision_hint: DecisionHint
    data_quality_score: float
    forensic_risk_score: float
    adjustment_audit_log: tuple[AuditEvent, ...] = ()
    blocked_adjustments: tuple[BlockedAdjustment, ...] = ()
    inputs: dict[str, float | str | None] = field(default_factory=dict)

    @property
    def effective_fair_value(self) -> float | None:
        if self.adjusted_fair_value is not None:
            return self.adjusted_fair_value
        return self.original_fair_value
