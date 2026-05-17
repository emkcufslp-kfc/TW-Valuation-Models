"""Structured validation results used across IMFS engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    field: str | None = None


@dataclass
class ValidationReport:
    subject: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(issue.severity == Severity.ERROR for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == Severity.WARNING)

    def add(
        self,
        code: str,
        message: str,
        severity: Severity = Severity.ERROR,
        field: str | None = None,
    ) -> None:
        self.issues.append(ValidationIssue(code, message, severity, field))

    def merge(self, other: "ValidationReport") -> None:
        self.issues.extend(other.issues)

