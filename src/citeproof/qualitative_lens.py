"""Deterministic qualitative scope and descriptor checks."""

from __future__ import annotations

import re

from citeproof.text import academic_token_overlap_ratio, tokenize

ONLY_RE = re.compile(r"\bonly\b", re.IGNORECASE)
MULTI_RE = re.compile(r"\b(one\s+of|among|several|multiple|both)\b", re.IGNORECASE)
UNIVERSAL_RE = re.compile(r"\b(all|every|universally)\b", re.IGNORECASE)
NARROW_RE = re.compile(r"\b(most|many|some|subset|not\s+all|majority)\b", re.IGNORECASE)
SIGNIFICANT_CLAIM_RE = re.compile(r"\b(significant|significantly)\b", re.IGNORECASE)
SIGNIFICANCE_NEGATION_RE = re.compile(
    r"\b("
    r"not\s+statistically\s+significant|"
    r"not\s+significant|"
    r"no\s+statistically\s+significant"
    r")\b",
    re.IGNORECASE,
)
SOTA_CLAIM_RE = re.compile(
    r"\b(?:achieves?|reaches?)\s+state[- ]of[- ]the[- ]art\b",
    re.IGNORECASE,
)
SOTA_NEGATION_RE = re.compile(
    r"\b(?:does\s+not|did\s+not|not)\s+"
    r"(?:achieve|reach)\s+state[- ]of[- ]the[- ]art\b",
    re.IGNORECASE,
)
GOOD_INDICATOR_CLAIM_RE = re.compile(r"\bgood\s+indicator\b", re.IGNORECASE)
GOOD_INDICATOR_NEGATION_RE = re.compile(
    r"\b(?:can\s+not|cannot|does\s+not|is\s+not|not)\s+"
    r"(?:be\s+)?(?:a\s+)?good\s+indicator\b",
    re.IGNORECASE,
)
TRACTABILITY_CLAIM_RE = re.compile(r"\b(?:tractable|tractably)\b", re.IGNORECASE)
INTRACTABILITY_EVIDENCE_RE = re.compile(
    r"\bintractable\b|"
    r"\b(?:must|need(?:s)?)\s+(?:be\s+)?used?\b.{0,60}\bapproximation\b|"
    r"\bapproximation\b.{0,60}\b(?:must|need(?:s)?)\s+(?:be\s+)?used?\b",
    re.IGNORECASE,
)
SUFFICIENCY_CLAIM_RE = re.compile(r"\b(?:sufficient|guaranteed)\b", re.IGNORECASE)
SUFFICIENCY_NEGATION_RE = re.compile(
    r"\b(?:does\s+not|did\s+not|doesn't|didn't)\s+work\b|"
    r"\bnot\s+(?:guaranteed|sufficient)\b",
    re.IGNORECASE,
)
REQUIRES_NO_RE = re.compile(
    r"\brequires?\s+no\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,60})",
    re.IGNORECASE,
)
REQUIRES_RE = re.compile(
    r"\brequires?\s+(?!no\b)(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,60})",
    re.IGNORECASE,
)
OBJECT_STOP_RE = re.compile(
    r"\b(?:for|during|with|and|but|while|whereas)\b",
    re.IGNORECASE,
)
TRIGGER_WORDS_RE = re.compile(
    r"\b("
    r"all|among|both|convolutional|every|majority|many|most|multiple|no|not|"
    r"of|offline|only|online|one|requires?|several|significant|significantly|"
    r"some|state|statistically|subset|the|three|transformer|universally"
    r")\b",
    re.IGNORECASE,
)

DESCRIPTOR_PAIRS = (
    ("transformer", "convolutional"),
    ("offline", "online"),
)


def inspect_qualitative_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return deterministic hard qualitative conflicts."""

    findings: list[str] = []
    findings.extend(_exclusivity_conflicts(claim, evidence))
    findings.extend(_significance_conflicts(claim, evidence))
    findings.extend(_sota_conflicts(claim, evidence))
    findings.extend(_indicator_conflicts(claim, evidence))
    findings.extend(_tractability_conflicts(claim, evidence))
    findings.extend(_sufficiency_conflicts(claim, evidence))
    findings.extend(_requirement_conflicts(claim, evidence))
    findings.extend(_descriptor_conflicts(claim, evidence))
    return tuple(findings)


def inspect_qualitative_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return weaker qualitative tensions that should block a supported label."""

    if (
        UNIVERSAL_RE.search(claim)
        and NARROW_RE.search(evidence)
        and _context_overlaps(claim, evidence)
    ):
        return ("Scope tension: evidence is narrower than the universal claim.",)
    return ()


def _exclusivity_conflicts(claim: str, evidence: str) -> list[str]:
    if ONLY_RE.search(claim) and MULTI_RE.search(evidence) and _context_overlaps(claim, evidence):
        return ["Exclusivity conflict: evidence describes one of multiple cases."]
    return []


def _significance_conflicts(claim: str, evidence: str) -> list[str]:
    if (
        SIGNIFICANT_CLAIM_RE.search(claim)
        and not SIGNIFICANCE_NEGATION_RE.search(claim)
        and SIGNIFICANCE_NEGATION_RE.search(evidence)
        and _context_overlaps(claim, evidence)
    ):
        return [
            "Significance conflict: evidence says the result is not statistically significant."
        ]
    return []


def _sota_conflicts(claim: str, evidence: str) -> list[str]:
    if (
        SOTA_CLAIM_RE.search(claim)
        and not SOTA_NEGATION_RE.search(claim)
        and SOTA_NEGATION_RE.search(evidence)
        and _context_overlaps(claim, evidence)
    ):
        return ["State-of-the-art conflict: evidence negates the claim."]
    return []


def _indicator_conflicts(claim: str, evidence: str) -> list[str]:
    if (
        GOOD_INDICATOR_CLAIM_RE.search(claim)
        and not GOOD_INDICATOR_NEGATION_RE.search(claim)
        and GOOD_INDICATOR_NEGATION_RE.search(evidence)
        and academic_token_overlap_ratio(claim, evidence) >= 0.5
    ):
        return ["Negation conflict: evidence says the measure is not a good indicator."]
    return []


def _tractability_conflicts(claim: str, evidence: str) -> list[str]:
    if (
        TRACTABILITY_CLAIM_RE.search(claim)
        and INTRACTABILITY_EVIDENCE_RE.search(evidence)
        and academic_token_overlap_ratio(claim, evidence) >= 0.45
    ):
        return ["Negation conflict: evidence says the claimed tractable problem is intractable."]
    return []


def _sufficiency_conflicts(claim: str, evidence: str) -> list[str]:
    if (
        SUFFICIENCY_CLAIM_RE.search(claim)
        and SUFFICIENCY_NEGATION_RE.search(evidence)
        and academic_token_overlap_ratio(claim, evidence) >= 0.4
    ):
        return ["Negation conflict: evidence negates the claimed sufficiency or guarantee."]
    return []


def _requirement_conflicts(claim: str, evidence: str) -> list[str]:
    claim_negative = [_clean_object(match.group("object")) for match in REQUIRES_NO_RE.finditer(claim)]
    evidence_positive = [_clean_object(match.group("object")) for match in REQUIRES_RE.finditer(evidence)]
    for negative in claim_negative:
        for positive in evidence_positive:
            if not _objects_overlap(negative, positive):
                continue
            object_tokens = set(tokenize(negative)) | set(tokenize(positive))
            if _context_overlaps(claim, evidence, object_tokens):
                return [
                    f"Requirement conflict: claim says no {negative} but evidence requires it."
                ]
    return []


def _descriptor_conflicts(claim: str, evidence: str) -> list[str]:
    for left, right in DESCRIPTOR_PAIRS:
        if (
            _has_descriptor(claim, left)
            and _has_descriptor(evidence, right)
            and _context_overlaps(claim, evidence)
        ):
            return [f"Descriptor conflict: claim says {left} while evidence says {right}."]
        if (
            _has_descriptor(claim, right)
            and _has_descriptor(evidence, left)
            and _context_overlaps(claim, evidence)
        ):
            return [f"Descriptor conflict: claim says {right} while evidence says {left}."]
    return []


def _has_descriptor(text: str, descriptor: str) -> bool:
    pattern = descriptor.replace("-", r"[-\s]+")
    return bool(re.search(rf"\b{pattern}\b", text, re.IGNORECASE))


def _clean_object(text: str) -> str:
    clipped = OBJECT_STOP_RE.split(text, maxsplit=1)[0]
    return clipped.strip(" .,:;()[]{}")


def _objects_overlap(left: str, right: str) -> bool:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return False
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens)) >= 0.67


def _context_overlaps(
    claim: str,
    evidence: str,
    excluded_tokens: set[str] | None = None,
) -> bool:
    claim_tokens = _context_tokens(claim, excluded_tokens)
    evidence_tokens = _context_tokens(evidence, excluded_tokens)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.67


def _context_tokens(text: str, excluded_tokens: set[str] | None = None) -> set[str]:
    tokens = set(tokenize(TRIGGER_WORDS_RE.sub(" ", text)))
    if excluded_tokens:
        tokens -= excluded_tokens
    return tokens
