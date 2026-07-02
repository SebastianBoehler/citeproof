"""Numeric lower/upper-bound conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.quantities import QuantityMention, quantity_mentions
from citeproof.text import tokenize

LOWER_BOUND = "lower"
UPPER_BOUND = "upper"
EXACT_BOUND = "exact"

LOWER_BOUND_RE = re.compile(
    r"\b(over|more\s+than|greater\s+than|at\s+least|no\s+less\s+than)\b",
    re.IGNORECASE,
)
UPPER_BOUND_RE = re.compile(
    r"\b(up\s+to|at\s+most|no\s+more\s+than|under|less\s+than)\b",
    re.IGNORECASE,
)
STRICT_LOWER_BOUND_RE = re.compile(r"\b(over|more\s+than|greater\s+than)\b", re.IGNORECASE)
STRICT_UPPER_BOUND_RE = re.compile(r"\b(under|less\s+than)\b", re.IGNORECASE)
EXACT_BOUND_RE = re.compile(r"\b(exactly)\b", re.IGNORECASE)
BOUND_CONTEXT_STOP_RE = re.compile(
    r"\b(?:at\s+least|at\s+most|greater\s+than|less\s+than|more\s+than|"
    r"no\s+less\s+than|no\s+more\s+than|up\s+to|over|under|exactly)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BoundQuantity:
    mention: QuantityMention
    bound: str
    context_tokens: frozenset[str]
    strict: bool = False


def inspect_numeric_bound_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts between incompatible quantity bounds."""

    findings: list[str] = []
    for claim_bound in _bound_quantities(claim):
        for evidence_bound in _bound_quantities(evidence):
            if claim_bound.mention.unit != evidence_bound.mention.unit:
                continue
            if not _bound_context_overlaps(claim_bound, evidence_bound):
                continue
            if _bounds_conflict(claim_bound, evidence_bound):
                findings.append(_bound_finding("Numeric bound conflict", claim_bound, evidence_bound))
    return tuple(findings)


def inspect_numeric_bound_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return weaker same-value bound tensions."""

    findings: list[str] = []
    for claim_bound in _bound_quantities(claim):
        for evidence_bound in _bound_quantities(evidence):
            if claim_bound.mention.unit != evidence_bound.mention.unit:
                continue
            if not _bound_context_overlaps(claim_bound, evidence_bound):
                continue
            if _bounds_tense(claim_bound, evidence_bound):
                findings.append(_bound_finding("Numeric bound tension", claim_bound, evidence_bound))
    return tuple(findings)


def _bound_quantities(text: str) -> list[BoundQuantity]:
    bounds: list[BoundQuantity] = []
    cursor = 0
    for mention in quantity_mentions(text):
        start = text.find(mention.text, cursor)
        if start == -1:
            start = text.find(mention.text)
        cursor = max(start + len(mention.text), cursor)
        context = text[max(0, start - 32) : start]
        bound, strict = _bound_category(context)
        bounds.append(BoundQuantity(mention, bound, _bound_context_tokens(text, mention), strict))
    return bounds


def _bound_context_tokens(text: str, mention: QuantityMention) -> frozenset[str]:
    context = text.replace(mention.text, " ")
    context = BOUND_CONTEXT_STOP_RE.sub(" ", context)
    tokens = set(tokenize(context))
    tokens.update(token.casefold() for token in re.findall(r"\b[A-Z]\b", context))
    return frozenset(tokens)


def _bound_context_overlaps(claim: BoundQuantity, evidence: BoundQuantity) -> bool:
    if not claim.context_tokens or not evidence.context_tokens:
        return False
    overlap = claim.context_tokens & evidence.context_tokens
    return len(overlap) / min(len(claim.context_tokens), len(evidence.context_tokens)) >= 0.75


def _bound_category(prefix: str) -> tuple[str, bool]:
    if LOWER_BOUND_RE.search(prefix):
        return LOWER_BOUND, bool(STRICT_LOWER_BOUND_RE.search(prefix))
    if UPPER_BOUND_RE.search(prefix):
        return UPPER_BOUND, bool(STRICT_UPPER_BOUND_RE.search(prefix))
    if EXACT_BOUND_RE.search(prefix):
        return EXACT_BOUND, False
    return EXACT_BOUND, False


def _bounds_conflict(claim: BoundQuantity, evidence: BoundQuantity) -> bool:
    if claim.bound == LOWER_BOUND and evidence.bound == UPPER_BOUND:
        return _empty_lower_upper(claim, evidence)
    if claim.bound == UPPER_BOUND and evidence.bound == LOWER_BOUND:
        return _empty_lower_upper(evidence, claim)
    if claim.bound == LOWER_BOUND and evidence.bound == EXACT_BOUND:
        return evidence.mention.number < claim.mention.number
    if claim.bound == UPPER_BOUND and evidence.bound == EXACT_BOUND:
        return evidence.mention.number > claim.mention.number
    if claim.bound == EXACT_BOUND and evidence.bound == LOWER_BOUND:
        return claim.mention.number < evidence.mention.number
    if claim.bound == EXACT_BOUND and evidence.bound == UPPER_BOUND:
        return claim.mention.number > evidence.mention.number
    return False


def _bounds_tense(claim: BoundQuantity, evidence: BoundQuantity) -> bool:
    if claim.mention.number != evidence.mention.number:
        return False
    return (
        _strict_bound_against_exact(claim, evidence)
        or _strict_bound_against_exact(evidence, claim)
    )


def _empty_lower_upper(lower: BoundQuantity, upper: BoundQuantity) -> bool:
    if lower.mention.number > upper.mention.number:
        return True
    if lower.mention.number == upper.mention.number:
        return lower.strict or upper.strict
    return False


def _strict_bound_against_exact(bound: BoundQuantity, exact: BoundQuantity) -> bool:
    return bound.strict and bound.bound in {LOWER_BOUND, UPPER_BOUND} and exact.bound == EXACT_BOUND


def _bound_finding(label: str, claim: BoundQuantity, evidence: BoundQuantity) -> str:
    return (
        f"{label} for {claim.mention.unit}: "
        f"claim {claim.mention.text} vs evidence {evidence.mention.text}"
    )
