"""Decision policy for IMFS 2.1."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from imfs.forensic.report import ForensicReport
from imfs.valuation.result import ValuationResult


class Verdict(str, Enum):
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    AVOID = "Avoid / Sell"
    NO_DECISION = "No Decision"


@dataclass(frozen=True)
class Decision:
    ticker: str
    verdict: Verdict
    confidence: float
    explanation: str


def decide(
    valuation: ValuationResult,
    forensic: ForensicReport,
    *,
    buy_gap: float = 0.20,
    sell_gap: float = -0.15,
) -> Decision:
    if forensic.red_flag:
        return Decision(
            valuation.ticker,
            Verdict.AVOID,
            min(0.95, 0.60 + forensic.confidence * 0.35),
            "Forensic red flag overrides valuation.",
        )
    if not valuation.usable or valuation.valuation_gap_pct is None:
        return Decision(
            valuation.ticker,
            Verdict.NO_DECISION,
            min(valuation.confidence, forensic.confidence),
            "Insufficient usable valuation data.",
        )
    confidence = min(1.0, (valuation.confidence + forensic.confidence) / 2.0)
    if valuation.valuation_gap_pct >= buy_gap:
        return Decision(
            valuation.ticker,
            Verdict.BUY,
            confidence,
            f"Intrinsic value is {valuation.valuation_gap_pct:.1%} above current price.",
        )
    if valuation.valuation_gap_pct <= sell_gap:
        return Decision(
            valuation.ticker,
            Verdict.SELL,
            confidence,
            f"Intrinsic value is {abs(valuation.valuation_gap_pct):.1%} below current price.",
        )
    return Decision(
        valuation.ticker,
        Verdict.HOLD,
        confidence,
        "Valuation gap is within the hold band.",
    )

