"""Deterministic negation and comparator conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.quantities import QuantityMention, quantity_mentions
from citeproof.text import tokenize

LOWER_BOUND = "lower"
UPPER_BOUND = "upper"
EXACT_BOUND = "exact"

NEGATED_USE_RE = re.compile(
    r"\b(?:does\s+not|did\s+not|not)\s+use\s+"
    r"(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
CLAIM_USE_RE = re.compile(
    r"\b(?:uses?|used|using)\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
NEGATED_TRAIN_RE = re.compile(
    r"\b(?:was\s+not|were\s+not|not)\s+"
    r"(?P<predicate>trained|pretrained|fine[- ]tuned)\s+on\s+"
    r"(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
CLAIM_TRAIN_RE = re.compile(
    r"\b(?P<predicate>trained|pretrained|fine[- ]tuned)\s+on\s+"
    r"(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
WITHOUT_RE = re.compile(
    r"\bwithout\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
POSITIVE_DIRECTION_RE = re.compile(r"\b(increase[sd]?|higher|more)\b", re.IGNORECASE)
NEGATIVE_DIRECTION_RE = re.compile(r"\b(decrease[sd]?|lower|less|reduced)\b", re.IGNORECASE)
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
OBJECT_STOP_RE = re.compile(
    r"\b(?:but|although|while|whereas|and|with|during|from|than)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BoundQuantity:
    mention: QuantityMention
    bound: str
    strict: bool = False


def inspect_negation_and_comparator_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return deterministic negation, direction, and bound conflicts."""

    findings = (
        _explicit_negation_conflicts(claim, evidence)
        + _direction_conflicts(claim, evidence)
        + _numeric_bound_conflicts(claim, evidence)
    )
    return tuple(findings)


def inspect_negation_and_comparator_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return weaker bound tensions that should block a supported label."""

    return tuple(_numeric_bound_tensions(claim, evidence))


def _explicit_negation_conflicts(claim: str, evidence: str) -> list[str]:
    findings: list[str] = []
    for predicate, claim_object in _claim_objects(claim):
        for negated_object in _evidence_negated_objects(evidence):
            if _objects_overlap(claim_object, negated_object):
                findings.append(f"Negation conflict: evidence negates {predicate} of {claim_object}")
                break
    return findings


def _claim_objects(text: str) -> list[tuple[str, str]]:
    objects: list[tuple[str, str]] = []
    for match in CLAIM_USE_RE.finditer(text):
        objects.append(("use", _clean_object(match.group("object"))))
    for match in CLAIM_TRAIN_RE.finditer(text):
        predicate = match.group("predicate").replace("-", " ").lower()
        objects.append((predicate, _clean_object(match.group("object"))))
    return [(predicate, obj) for predicate, obj in objects if obj]


def _evidence_negated_objects(text: str) -> list[str]:
    objects: list[str] = []
    for pattern in (NEGATED_USE_RE, NEGATED_TRAIN_RE, WITHOUT_RE):
        for match in pattern.finditer(text):
            obj = _clean_object(match.group("object"))
            if obj:
                objects.append(obj)
    return objects


def _clean_object(text: str) -> str:
    clipped = OBJECT_STOP_RE.split(text, maxsplit=1)[0]
    return clipped.strip(" .,:;()[]{}")


def _objects_overlap(left: str, right: str) -> bool:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return False
    overlap = left_tokens & right_tokens
    return len(overlap) / min(len(left_tokens), len(right_tokens)) >= 0.67


def _direction_conflicts(claim: str, evidence: str) -> list[str]:
    claim_direction = _direction(claim)
    evidence_direction = _direction(evidence)
    if not claim_direction or not evidence_direction or claim_direction == evidence_direction:
        return []
    if not _direction_context_overlaps(claim, evidence):
        return []
    return [
        "Direction conflict: claim says "
        f"{claim_direction} while evidence says {evidence_direction}"
    ]


def _direction(text: str) -> str | None:
    positive = bool(POSITIVE_DIRECTION_RE.search(text))
    negative = bool(NEGATIVE_DIRECTION_RE.search(text))
    if positive == negative:
        return None
    return "increased" if positive else "decreased"


def _direction_context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _direction_context_tokens(claim)
    evidence_tokens = _direction_context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.5


def _direction_context_tokens(text: str) -> set[str]:
    stripped = POSITIVE_DIRECTION_RE.sub(" ", text)
    stripped = NEGATIVE_DIRECTION_RE.sub(" ", stripped)
    for mention in quantity_mentions(text):
        stripped = stripped.replace(mention.text, " ")
    return set(tokenize(stripped))


def _numeric_bound_conflicts(claim: str, evidence: str) -> list[str]:
    findings: list[str] = []
    for claim_bound in _bound_quantities(claim):
        for evidence_bound in _bound_quantities(evidence):
            if claim_bound.mention.unit != evidence_bound.mention.unit:
                continue
            if _bounds_conflict(claim_bound, evidence_bound):
                findings.append(_bound_finding("Numeric bound conflict", claim_bound, evidence_bound))
    return findings


def _numeric_bound_tensions(claim: str, evidence: str) -> list[str]:
    findings: list[str] = []
    for claim_bound in _bound_quantities(claim):
        for evidence_bound in _bound_quantities(evidence):
            if claim_bound.mention.unit != evidence_bound.mention.unit:
                continue
            if _bounds_tense(claim_bound, evidence_bound):
                findings.append(_bound_finding("Numeric bound tension", claim_bound, evidence_bound))
    return findings


def _bound_quantities(text: str) -> list[BoundQuantity]:
    bounds: list[BoundQuantity] = []
    cursor = 0
    for mention in quantity_mentions(text):
        start = text.find(mention.text, cursor)
        if start == -1:
            start = text.find(mention.text)
        cursor = max(start + len(mention.text), cursor)
        context = text[max(0, start - 32) : start]
        bounds.append(BoundQuantity(mention, *_bound_category(context)))
    return bounds


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
