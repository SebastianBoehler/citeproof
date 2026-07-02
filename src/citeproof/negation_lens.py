"""Deterministic negation and comparator conflict checks."""

from __future__ import annotations

import re

from citeproof.numeric_bound_lens import (
    inspect_numeric_bound_conflicts,
    inspect_numeric_bound_tensions,
)
from citeproof.quantities import quantity_mentions
from citeproof.text import tokenize

NEGATED_USE_RE = re.compile(
    r"\b(?:does\s+not|did\s+not|not)\s+use\s+"
    r"(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
CLAIM_USE_RE = re.compile(
    r"\b(?:uses?|used|using)\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
CLAIM_DEPENDENCY_RE = re.compile(
    r"\b(?:requires?|depends?\s+on|relies?\s+on|applies?)\s+"
    r"(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
CLAIM_TRAIN_OBJECT_RE = re.compile(
    r"\b(?:trains?|training)\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
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
AVOID_RE = re.compile(
    r"\b(?:avoids?|avoid(?:ing)?|eliminates?|no|not\s+necessary)\s+"
    r"(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
NOT_NECESSARY_OBJECT_RE = re.compile(
    r"\b(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80}?)\s+"
    r"(?:is|are|was|were)\s+not\s+necessary\b",
    re.IGNORECASE,
)
POSITIVE_DIRECTION_RE = re.compile(r"\b(increase[sd]?|higher)\b", re.IGNORECASE)
NEGATIVE_DIRECTION_RE = re.compile(r"\b(decrease[sd]?|lower|reduced)\b", re.IGNORECASE)
OBJECT_STOP_RE = re.compile(
    r"\b(?:but|although|while|whereas|and|or|by|for|with|during|from|than|when)\b",
    re.IGNORECASE,
)
CONTRASTED_USE_RE = re.compile(r"\bbut\s+uses?\b", re.IGNORECASE)


def inspect_negation_and_comparator_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return deterministic negation, direction, and bound conflicts."""

    findings = (
        _explicit_negation_conflicts(claim, evidence)
        + _direction_conflicts(claim, evidence)
        + list(inspect_numeric_bound_conflicts(claim, evidence))
    )
    return tuple(findings)


def inspect_negation_and_comparator_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return weaker bound tensions that should block a supported label."""

    return inspect_numeric_bound_tensions(claim, evidence)


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
    for match in CLAIM_DEPENDENCY_RE.finditer(text):
        objects.append(("dependency", _clean_object(match.group("object"))))
    for match in CLAIM_TRAIN_OBJECT_RE.finditer(text):
        objects.append(("training", _clean_object(match.group("object"))))
    for match in CLAIM_TRAIN_RE.finditer(text):
        predicate = match.group("predicate").replace("-", " ").lower()
        objects.append((predicate, _clean_object(match.group("object"))))
    return [(predicate, obj) for predicate, obj in objects if obj]


def _evidence_negated_objects(text: str) -> list[str]:
    objects: list[str] = []
    for pattern in (NEGATED_USE_RE, NEGATED_TRAIN_RE, WITHOUT_RE, AVOID_RE, NOT_NECESSARY_OBJECT_RE):
        for match in pattern.finditer(text):
            obj = _clean_object(match.group("object"))
            if obj and not _negation_has_affirmative_scope(text, match, obj):
                objects.append(obj)
    return objects


def _negation_has_affirmative_scope(text: str, match: re.Match[str], obj: str) -> bool:
    raw_object = match.group("object")
    tail = text[match.end() : match.end() + 120]
    if " for " in f" {raw_object.lower()} " and CONTRASTED_USE_RE.search(tail):
        return True
    if CONTRASTED_USE_RE.search(tail):
        return True
    return _has_affirmative_use_after(text, match.end(), obj)


def _has_affirmative_use_after(text: str, start: int, obj: str) -> bool:
    for match in CLAIM_USE_RE.finditer(text, start):
        if _objects_overlap(obj, _clean_object(match.group("object"))):
            return True
    return False


def _clean_object(text: str) -> str:
    clipped = OBJECT_STOP_RE.split(text, maxsplit=1)[0]
    return clipped.strip(" .,:;()[]{}")


def _objects_overlap(left: str, right: str) -> bool:
    left_tokens = _object_tokens(left)
    right_tokens = _object_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    overlap = left_tokens & right_tokens
    return len(overlap) / min(len(left_tokens), len(right_tokens)) >= 0.67


def _object_tokens(text: str) -> set[str]:
    aliases = {
        "labels": "label",
        "modeling": "model",
        "modelling": "model",
        "models": "model",
    }
    return {aliases.get(token, token) for token in tokenize(text)}


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
