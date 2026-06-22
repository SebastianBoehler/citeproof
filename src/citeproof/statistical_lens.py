"""Controlled statistical reporting conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

CONTEXT_STOPWORDS = {
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "has",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "with",
}


@dataclass(frozen=True)
class StatisticalGroup:
    label: str
    values: tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True)
class PValueClaim:
    relation: str
    value: Decimal
    text: str


GROUPS = (
    StatisticalGroup(
        "Confidence interval",
        (
            ("includes zero", (r"\bincludes?\s+zero\b",)),
            ("excludes zero", (r"\bexcludes?\s+zero\b",)),
        ),
    ),
    StatisticalGroup(
        "F1 averaging",
        (
            ("macro-F1", (r"\bmacro[- ]?f1\b",)),
            ("micro-F1", (r"\bmicro[- ]?f1\b",)),
        ),
    ),
    StatisticalGroup(
        "Summary statistic",
        (
            ("mean", (r"\bmean\b",)),
            ("median", (r"\bmedian\b",)),
        ),
    ),
    StatisticalGroup(
        "Uncertainty statistic",
        (
            ("standard deviation", (r"\bstandard\s+deviation\b",)),
            ("standard error", (r"\bstandard\s+error\b",)),
        ),
    ),
    StatisticalGroup(
        "Pairedness",
        (
            ("paired", (r"\bpaired\b",)),
            ("unpaired", (r"\bunpaired\b",)),
        ),
    ),
    StatisticalGroup(
        "Tail count",
        (
            ("one-tailed", (r"\bone[- ]tailed\b",)),
            ("two-tailed", (r"\btwo[- ]tailed\b",)),
        ),
    ),
    StatisticalGroup(
        "Test family",
        (
            ("parametric", (r"\bparametric\b",)),
            ("nonparametric", (r"\bnon[- ]?parametric\b",)),
        ),
    ),
)

VALUE_TERMS_RE = re.compile(
    r"\b("
    r"excludes?|includes?|macro[- ]?f1|mean|median|micro[- ]?f1|non[- ]?parametric|"
    r"one[- ]tailed|paired|parametric|standard\s+deviation|standard\s+error|"
    r"p[- ]?value|p|significant|statistically|two[- ]tailed|unpaired|zero"
    r")\b",
    re.IGNORECASE,
)
P_VALUE_RE = re.compile(
    r"\bp(?:[- ]?value)?\s*"
    r"(?:(?P<symbol><=|>=|<|>|=)|"
    r"(?P<word>less\s+than|below|under|greater\s+than|above|"
    r"at\s+least|no\s+less\s+than|at\s+most|no\s+more\s+than|"
    r"equal\s+to|equals?|is|was))?\s*"
    r"(?P<value>\d?\.\d+|\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
NOT_SIGNIFICANT_RE = re.compile(r"\bnot\s+statistically\s+significant\b", re.IGNORECASE)
SIGNIFICANT_RE = re.compile(r"\bstatistically\s+significant\b", re.IGNORECASE)
DEFAULT_SIGNIFICANCE_THRESHOLD = Decimal("0.05")


def inspect_statistical_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return deterministic hard conflicts for controlled statistical reporting."""

    findings: list[str] = []
    findings.extend(_p_value_conflicts(claim, evidence))
    for group in GROUPS:
        claim_values = set(_mentioned_values(group, claim))
        evidence_values = set(_mentioned_values(group, evidence))
        if not claim_values or not evidence_values or claim_values & evidence_values:
            continue
        for claim_value in claim_values:
            for evidence_value in evidence_values:
                if _context_overlaps(claim, evidence):
                    findings.append(
                        f"{group.label} conflict: claim says {claim_value} "
                        f"while evidence says {evidence_value}."
                    )
    return tuple(dict.fromkeys(findings))


def _p_value_conflicts(claim: str, evidence: str) -> list[str]:
    if not _context_overlaps(claim, evidence):
        return []
    findings: list[str] = []
    for claim_value in _p_value_claims(claim):
        for evidence_value in _p_value_claims(evidence):
            if _relations_conflict(claim_value, evidence_value):
                findings.append(
                    "P-value conflict: claim says "
                    f"{claim_value.text} while evidence says {evidence_value.text}."
                )
    return findings


def _p_value_claims(text: str) -> tuple[PValueClaim, ...]:
    explicit = tuple(_explicit_p_values(text))
    if explicit:
        return explicit
    if NOT_SIGNIFICANT_RE.search(text):
        return (PValueClaim("ge", DEFAULT_SIGNIFICANCE_THRESHOLD, "not statistically significant"),)
    if SIGNIFICANT_RE.search(text):
        return (PValueClaim("lt", DEFAULT_SIGNIFICANCE_THRESHOLD, "statistically significant"),)
    return ()


def _explicit_p_values(text: str) -> tuple[PValueClaim, ...]:
    values: list[PValueClaim] = []
    for match in P_VALUE_RE.finditer(text):
        relation = _normalize_relation(match.group("symbol") or match.group("word") or "=")
        values.append(PValueClaim(relation, Decimal(match.group("value")), match.group(0)))
    return tuple(values)


def _normalize_relation(value: str) -> str:
    normalized = value.casefold().strip()
    relations = {
        "<": "lt",
        "less than": "lt",
        "below": "lt",
        "under": "lt",
        "<=": "le",
        "at most": "le",
        "no more than": "le",
        ">": "gt",
        "greater than": "gt",
        "above": "gt",
        ">=": "ge",
        "at least": "ge",
        "no less than": "ge",
        "=": "eq",
        "equal to": "eq",
        "equals": "eq",
        "equal": "eq",
        "is": "eq",
        "was": "eq",
    }
    return relations[normalized]


def _relations_conflict(claim: PValueClaim, evidence: PValueClaim) -> bool:
    if evidence.relation == "eq":
        return not _value_satisfies(evidence.value, claim)
    if claim.relation == "eq":
        return _bound_excludes_value(evidence, claim.value)
    return _bounds_exclude_each_other(claim, evidence)


def _value_satisfies(value: Decimal, relation: PValueClaim) -> bool:
    if relation.relation == "lt":
        return value < relation.value
    if relation.relation == "le":
        return value <= relation.value
    if relation.relation == "gt":
        return value > relation.value
    if relation.relation == "ge":
        return value >= relation.value
    return value == relation.value


def _bound_excludes_value(bound: PValueClaim, value: Decimal) -> bool:
    if bound.relation == "lt":
        return value >= bound.value
    if bound.relation == "le":
        return value > bound.value
    if bound.relation == "gt":
        return value <= bound.value
    if bound.relation == "ge":
        return value < bound.value
    return bound.value != value


def _bounds_exclude_each_other(claim: PValueClaim, evidence: PValueClaim) -> bool:
    claim_upper = claim.relation in {"lt", "le"}
    evidence_lower = evidence.relation in {"gt", "ge"}
    if claim_upper and evidence_lower:
        return evidence.value >= claim.value
    claim_lower = claim.relation in {"gt", "ge"}
    evidence_upper = evidence.relation in {"lt", "le"}
    return bool(claim_lower and evidence_upper and evidence.value <= claim.value)


def _mentioned_values(group: StatisticalGroup, text: str) -> tuple[str, ...]:
    values: list[str] = []
    for value, patterns in group.values:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            values.append(value)
    if group.label == "Test family" and "nonparametric" in values:
        values = [value for value in values if value != "parametric"]
    return tuple(values)


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.67


def _context_tokens(text: str) -> set[str]:
    terms = re.findall(r"[a-z0-9]+", VALUE_TERMS_RE.sub(" ", text).lower())
    return {term for term in terms if term not in CONTEXT_STOPWORDS and not term.isdigit()}
