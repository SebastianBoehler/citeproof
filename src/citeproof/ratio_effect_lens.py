"""Ratio effect checks where the null value is one."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RatioClaim:
    relation: str
    text: str


@dataclass(frozen=True)
class RatioEvidence:
    relation: str
    text: str


RATIO_METRIC = r"(?:hazard\s+ratio|odds\s+ratio|risk\s+ratio|relative\s+risk)"
RATIO_POINT_RE = re.compile(
    rf"\b(?P<metric>{RATIO_METRIC})\b"
    r"(?P<context>[^.;\n]{0,80}?)"
    r"\b(?:was|is|=|of)?\s*(?P<value>\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
RATIO_CI_RE = re.compile(
    rf"\b(?P<metric>{RATIO_METRIC})\b"
    r"[^;\n]{0,100}?\b(?:ci|confidence\s+interval)\b"
    r"[^()[\]]{0,40}[\[(]\s*"
    r"(?P<lower>[+-]?\d+(?:\.\d+)?)\s*,\s*"
    r"(?P<upper>[+-]?\d+(?:\.\d+)?)\s*[\])]",
    re.IGNORECASE,
)
BELOW_ONE_RE = re.compile(
    rf"\b{RATIO_METRIC}\b[^.;\n]{{0,60}}\b(?:below|less\s+than|under)\s+1\b",
    re.IGNORECASE,
)
ABOVE_ONE_RE = re.compile(
    rf"\b{RATIO_METRIC}\b[^.;\n]{{0,60}}\b(?:above|greater\s+than|over)\s+1\b",
    re.IGNORECASE,
)
EXCLUDES_NULL_RE = re.compile(
    rf"\b{RATIO_METRIC}\b[^.;\n]{{0,80}}\bexcludes?\s+(?:the\s+)?null(?:\s+value)?\b",
    re.IGNORECASE,
)
INCLUDES_NULL_RE = re.compile(
    rf"\b{RATIO_METRIC}\b[^.;\n]{{0,80}}\bincludes?\s+(?:the\s+)?null(?:\s+value)?\b",
    re.IGNORECASE,
)
NOT_SIGNIFICANT_RE = re.compile(
    rf"\b{RATIO_METRIC}\b[^.;\n]{{0,80}}\bnot\s+statistically\s+significant\b",
    re.IGNORECASE,
)
SIGNIFICANT_RE = re.compile(
    rf"\b{RATIO_METRIC}\b[^.;\n]{{0,80}}\bstatistically\s+significant\b",
    re.IGNORECASE,
)
NULL_VALUE = Decimal("1")


def inspect_ratio_effect_conflicts(
    claim: str,
    evidence: str,
    context_overlaps: bool,
) -> tuple[str, ...]:
    """Return hard conflicts for ratio effects against null value one."""

    if not context_overlaps and not (_metrics(claim) & _metrics(evidence)):
        return ()
    findings: list[str] = []
    for claim_relation in _point_claims(claim):
        for evidence_relation in _point_evidence(evidence):
            if claim_relation.relation != evidence_relation.relation:
                findings.append(
                    "Ratio effect conflict: claim says "
                    f"{claim_relation.text} while evidence says {evidence_relation.text}."
                )
    for claim_relation in _null_claims(claim):
        for evidence_relation in _ci_evidence(evidence):
            if claim_relation.relation != evidence_relation.relation:
                findings.append(
                    "Ratio effect conflict: claim says "
                    f"{claim_relation.text} while evidence says {evidence_relation.text}."
                )
    return tuple(dict.fromkeys(findings))


def _point_claims(text: str) -> tuple[RatioClaim, ...]:
    claims: list[RatioClaim] = []
    if BELOW_ONE_RE.search(text):
        claims.append(RatioClaim("below one", "ratio below 1"))
    if ABOVE_ONE_RE.search(text):
        claims.append(RatioClaim("above one", "ratio above 1"))
    return tuple(claims)


def _metrics(text: str) -> set[str]:
    return {
        re.sub(r"\s+", " ", match.group(0).casefold())
        for match in re.finditer(RATIO_METRIC, text, re.IGNORECASE)
    }


def _null_claims(text: str) -> tuple[RatioClaim, ...]:
    claims: list[RatioClaim] = []
    if INCLUDES_NULL_RE.search(text) or NOT_SIGNIFICANT_RE.search(text):
        claims.append(RatioClaim("includes null", "ratio includes null"))
    if EXCLUDES_NULL_RE.search(text) or (
        SIGNIFICANT_RE.search(text) and not NOT_SIGNIFICANT_RE.search(text)
    ):
        claims.append(RatioClaim("excludes null", "ratio excludes null"))
    return tuple(claims)


def _point_evidence(text: str) -> tuple[RatioEvidence, ...]:
    evidence: list[RatioEvidence] = []
    for match in RATIO_POINT_RE.finditer(text):
        context = match.group("context")
        if re.search(r"\b(?:ci|confidence\s+interval)\b", context, re.IGNORECASE):
            continue
        value = Decimal(match.group("value"))
        relation = "below one" if value < NULL_VALUE else "above one"
        if value == NULL_VALUE:
            relation = "at null"
        evidence.append(RatioEvidence(relation, f"{match.group('metric')} {match.group('value')}"))
    return tuple(evidence)


def _ci_evidence(text: str) -> tuple[RatioEvidence, ...]:
    evidence: list[RatioEvidence] = []
    for match in RATIO_CI_RE.finditer(text):
        lower = Decimal(match.group("lower"))
        upper = Decimal(match.group("upper"))
        relation = "includes null" if lower <= NULL_VALUE <= upper else "excludes null"
        evidence.append(RatioEvidence(relation, match.group(0)))
    return tuple(evidence)
