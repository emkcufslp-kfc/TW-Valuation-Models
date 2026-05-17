"""Small sector mapping helpers used before route classification."""

from __future__ import annotations

from imfs.data.models import SecurityProfile


def normalized_sector(profile: SecurityProfile) -> str:
    text = f"{profile.sector} {profile.industry}".lower()
    if any(term in text for term in ("bank", "financial", "insurance", "securities")):
        return "financials"
    if any(term in text for term in ("semiconductor", "software", "technology", "ai", "cloud")):
        return "technology"
    if any(term in text for term in ("steel", "chemical", "materials", "commodity")):
        return "cyclicals"
    if any(term in text for term in ("utility", "telecom", "consumer staples")):
        return "defensive"
    return profile.sector.lower().strip() or "unknown"

