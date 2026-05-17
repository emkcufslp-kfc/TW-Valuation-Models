"""Forensic report aggregation."""

from __future__ import annotations

from dataclasses import dataclass

from imfs.forensic.altman import ForensicScore
from imfs.forensic.beneish import BeneishResult


@dataclass(frozen=True)
class ForensicReport:
    ticker: str
    altman: ForensicScore
    beneish: BeneishResult

    @property
    def red_flag(self) -> bool:
        return self.altman.red_flag or self.beneish.red_flag

    @property
    def confidence(self) -> float:
        available = int(self.altman.score is not None) + int(self.beneish.score is not None)
        return available / 2.0

    @property
    def label(self) -> str:
        if self.red_flag:
            return "red_flag"
        if self.confidence < 1.0:
            return "partial"
        return "clean"

