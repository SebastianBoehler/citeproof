"""P-value relation checks for statistical citation verification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PValueClaim:
    relation: str
    value: Decimal
    text: str


P_VALUE_RE = re.compile(
    r"(?<![-A-Za-z])\bp(?:[- ]?value)?\s*"
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


def inspect_p_value_conflicts(
    claim: str,
    evidence: str,
    context_overlaps: bool,
) -> tuple[str, ...]:
    """Return hard conflicts for incompatible p-value relations."""

    if not context_overlaps:
        return ()
    findings: list[str] = []
    for claim_value in _p_value_claims(claim):
        for evidence_value in _p_value_claims(evidence):
            if _relations_conflict(claim_value, evidence_value):
                findings.append(
                    "P-value conflict: claim says "
                    f"{claim_value.text} while evidence says {evidence_value.text}."
                )
    return tuple(dict.fromkeys(findings))


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
