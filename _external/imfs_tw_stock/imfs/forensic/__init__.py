"""Forensic accounting modules."""

from imfs.forensic.altman import ForensicScore, altman_z_prime_score, altman_z_score
from imfs.forensic.beneish import (
    MANIPULATION_RISK_THRESHOLD,
    BeneishInputs,
    BeneishResult,
    beneish_m_score,
)
from imfs.forensic.report import ForensicReport

__all__ = [
    "BeneishInputs",
    "BeneishResult",
    "ForensicReport",
    "ForensicScore",
    "MANIPULATION_RISK_THRESHOLD",
    "altman_z_prime_score",
    "altman_z_score",
    "beneish_m_score",
]
