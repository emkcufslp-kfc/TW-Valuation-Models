"""Deterministic post-valuation reality overlay."""

from __future__ import annotations

from imfs.forensic.altman import ForensicScore
from imfs.forensic.beneish import BeneishResult
from imfs.validation import (
    ValidationReport,
    validate_financial_snapshot,
    validate_price_record,
    validate_security_profile,
)

from .models import (
    AuditEvent,
    BlockedAdjustment,
    DecisionHint,
    GapSeverity,
    RealityOverlayInput,
    RealityOverlayResult,
)


def run_reality_overlay(item: RealityOverlayInput) -> RealityOverlayResult:
    profile_report = validate_security_profile(item.profile)
    price_report = validate_price_record(item.price)
    financial_report = validate_financial_snapshot(item.financials, as_of=item.price.trade_date)
    data_quality = _data_quality_score(profile_report, price_report, financial_report)
    forensic_risk = _forensic_risk_score(item.forensic.altman, item.forensic.beneish)
    severity = classify_gap_severity(item.valuation.valuation_gap_pct)
    hint = derive_decision_hint(
        item.decision.explanation,
        gap_severity=severity,
        data_quality_score=data_quality,
        forensic_risk_score=forensic_risk,
        valuation_gap_pct=item.valuation.valuation_gap_pct,
    )

    audit_log: list[AuditEvent] = [
        AuditEvent(
            rule_id="preserve_original_fair_value",
            outcome="applied",
            message="Reality overlay preserves the base valuation as the immutable original fair value.",
        ),
        AuditEvent(
            rule_id="overlay_annotation_only",
            outcome="applied",
            message="First build slice annotates valuation gaps and risks without repricing the base route output.",
        ),
    ]
    blocked: list[BlockedAdjustment] = [
        BlockedAdjustment(
            rule_id="fair_value_adjustment_deferred",
            reason="Adjusted fair value is disabled in the first overlay slice until explicit repricing rules are implemented.",
        )
    ]

    if data_quality < 0.60:
        blocked.append(
            BlockedAdjustment(
                rule_id="data_quality_gate",
                reason="Data quality score is below the minimum threshold for any future fair-value adjustment rules.",
            )
        )
        audit_log.append(
            AuditEvent(
                rule_id="data_quality_gate",
                outcome="blocked",
                message=f"Data quality score {data_quality:.2f} blocks any adjustment logic.",
            )
        )
    if forensic_risk >= 0.70:
        blocked.append(
            BlockedAdjustment(
                rule_id="forensic_risk_gate",
                reason="Forensic risk score is elevated, so the overlay records caution instead of repricing.",
            )
        )
        audit_log.append(
            AuditEvent(
                rule_id="forensic_risk_gate",
                outcome="blocked",
                message=f"Forensic risk score {forensic_risk:.2f} blocks any adjustment logic.",
            )
        )
    if severity == GapSeverity.UNAVAILABLE:
        audit_log.append(
            AuditEvent(
                rule_id="gap_severity_unavailable",
                outcome="blocked",
                message="Valuation gap severity could not be classified because usable valuation data is missing.",
            )
        )

    return RealityOverlayResult(
        ticker=item.profile.ticker,
        original_fair_value=item.valuation.intrinsic_value_per_share,
        adjusted_fair_value=None,
        gap_severity=severity,
        decision_hint=hint,
        data_quality_score=data_quality,
        forensic_risk_score=forensic_risk,
        adjustment_audit_log=tuple(audit_log),
        blocked_adjustments=tuple(blocked),
        inputs={
            "valuation_gap_pct": item.valuation.valuation_gap_pct,
            "route": item.route.route.value,
            "base_verdict": item.decision.verdict.value,
            "current_price": item.price.close,
        },
    )


def classify_gap_severity(valuation_gap_pct: float | None) -> GapSeverity:
    if valuation_gap_pct is None:
        return GapSeverity.UNAVAILABLE
    absolute_gap = abs(valuation_gap_pct)
    if absolute_gap < 0.10:
        return GapSeverity.IMMATERIAL
    if absolute_gap < 0.25:
        return GapSeverity.MINOR
    if absolute_gap < 0.50:
        return GapSeverity.MATERIAL
    return GapSeverity.SEVERE


def derive_decision_hint(
    decision_explanation: str,
    *,
    gap_severity: GapSeverity,
    data_quality_score: float,
    forensic_risk_score: float,
    valuation_gap_pct: float | None,
) -> DecisionHint:
    del decision_explanation
    if data_quality_score < 0.60:
        return DecisionHint.IMPROVE_DATA_QUALITY
    if gap_severity == GapSeverity.UNAVAILABLE:
        return DecisionHint.NEEDS_MANUAL_REVIEW
    if forensic_risk_score >= 0.70:
        return DecisionHint.FORENSIC_CAUTION
    if valuation_gap_pct is not None and valuation_gap_pct >= 0.25:
        return DecisionHint.REVIEW_UPSIDE
    if valuation_gap_pct is not None and valuation_gap_pct <= -0.15:
        return DecisionHint.REVIEW_DOWNSIDE
    return DecisionHint.MONITOR


def _data_quality_score(*reports: ValidationReport) -> float:
    error_count = sum(report.error_count for report in reports)
    warning_count = sum(report.warning_count for report in reports)
    score = 1.0 - (error_count * 0.45) - (warning_count * 0.10)
    return max(0.0, min(1.0, score))


def _forensic_risk_score(altman: ForensicScore, beneish: BeneishResult) -> float:
    altman_risk = _altman_risk_value(altman)
    beneish_risk = _beneish_risk_value(beneish)
    average_risk = (altman_risk + beneish_risk) / 2.0
    elevated_single_signal = max(altman_risk, beneish_risk) * 0.85
    return round(max(average_risk, elevated_single_signal), 4)


def _altman_risk_value(score: ForensicScore) -> float:
    if score.label == "distress":
        return 1.0
    if score.label == "grey_zone":
        return 0.60
    if score.label == "safe":
        return 0.15
    return 0.50


def _beneish_risk_value(result: BeneishResult) -> float:
    if result.label == "manipulation_risk":
        return 1.0
    if result.label == "clean":
        return 0.15
    return 0.50
