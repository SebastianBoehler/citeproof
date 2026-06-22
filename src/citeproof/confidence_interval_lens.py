"""Confidence interval numeric relation checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ConfidenceInterval:
    relation: str
    text: str


CI_RANGE_RE = re.compile(
    r"\b(?:\d+(?:\.\d+)?%\s+)?(?:confidence\s+interval|ci)\b"
    r"[^()[\]]{0,60}[\[(]\s*"
    r"(?P<lower>[+-]?\d+(?:\.\d+)?)\s*,\s*"
    r"(?P<upper>[+-]?\d+(?:\.\d+)?)\s*[\])]",
    re.IGNORECASE,
)
EXCLUDES_ZERO_RE = re.compile(r"\bexcludes?\s+zero\b", re.IGNORECASE)
INCLUDES_ZERO_RE = re.compile(r"\bincludes?\s+zero\b", re.IGNORECASE)
NOT_SIGNIFICANT_RE = re.compile(r"\bnot\s+statistically\s+significant\b", re.IGNORECASE)
SIGNIFICANT_RE = re.compile(r"\bstatistically\s+significant\b", re.IGNORECASE)


def inspect_confidence_interval_conflicts(
    claim: str,
    evidence: str,
    context_overlaps: bool,
) -> tuple[str, ...]:
    """Return hard conflicts for numeric confidence intervals and zero relation."""

    if not context_overlaps:
        return ()
    findings: list[str] = []
    for claim_interval in _claim_relations(claim):
        for evidence_interval in _numeric_intervals(evidence):
            if claim_interval.relation != evidence_interval.relation:
                findings.append(
                    "Confidence interval conflict: claim says "
                    f"{claim_interval.text} while evidence interval "
                    f"{evidence_interval.text} {evidence_interval.relation}."
                )
    return tuple(dict.fromkeys(findings))


def _claim_relations(text: str) -> tuple[ConfidenceInterval, ...]:
    if INCLUDES_ZERO_RE.search(text):
        return (ConfidenceInterval("includes zero", "includes zero"),)
    if EXCLUDES_ZERO_RE.search(text):
        return (ConfidenceInterval("excludes zero", "excludes zero"),)
    if NOT_SIGNIFICANT_RE.search(text):
        return (ConfidenceInterval("includes zero", "not statistically significant"),)
    if SIGNIFICANT_RE.search(text):
        return (ConfidenceInterval("excludes zero", "statistically significant"),)
    return ()


def _numeric_intervals(text: str) -> tuple[ConfidenceInterval, ...]:
    intervals: list[ConfidenceInterval] = []
    for match in CI_RANGE_RE.finditer(text):
        lower = Decimal(match.group("lower"))
        upper = Decimal(match.group("upper"))
        relation = "includes zero" if lower <= 0 <= upper else "excludes zero"
        intervals.append(ConfidenceInterval(relation, match.group(0)))
    return tuple(intervals)
