"""Contrastive exclusion checks for high-overlap evidence."""

from __future__ import annotations

import re

from citeproof.text import tokenize

CONTRAST_CUE_RE = re.compile(
    r"\b(?:rather\s+than|instead\s+of|as\s+opposed\s+to)\b",
    re.IGNORECASE,
)
EXCLUDED_PHRASE_RE = re.compile(
    r"\b(?:rather\s+than|instead\s+of|as\s+opposed\s+to)\s+"
    r"(?P<object>[^.;:,]+)",
    re.IGNORECASE,
)
CUE_TOKENS = {"rather", "than", "instead", "opposed"}
MIN_EXCLUDED_TOKEN_COUNT = 2
MIN_EXCLUDED_COVERAGE = 0.67
MIN_CONTEXT_OVERLAP = 0.5


def inspect_contrast_exclusion_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return conflicts where evidence explicitly excludes the claimed phrase."""

    if CONTRAST_CUE_RE.search(claim):
        return ()
    findings: list[str] = []
    claim_tokens = set(tokenize(claim))
    evidence_tokens = set(tokenize(evidence))
    for excluded in _excluded_phrases(evidence):
        excluded_tokens = set(tokenize(excluded))
        if len(excluded_tokens) < MIN_EXCLUDED_TOKEN_COUNT:
            continue
        if not _covered_by_claim(excluded_tokens, claim_tokens):
            continue
        if not _context_overlaps(claim_tokens, evidence_tokens, excluded_tokens):
            continue
        findings.append(
            "Contrast exclusion conflict: evidence explicitly excludes a phrase "
            "asserted by the claim."
        )
    return tuple(dict.fromkeys(findings))


def _excluded_phrases(text: str) -> tuple[str, ...]:
    return tuple(match.group("object").strip() for match in EXCLUDED_PHRASE_RE.finditer(text))


def _covered_by_claim(excluded_tokens: set[str], claim_tokens: set[str]) -> bool:
    return len(excluded_tokens & claim_tokens) / len(excluded_tokens) >= MIN_EXCLUDED_COVERAGE


def _context_overlaps(
    claim_tokens: set[str],
    evidence_tokens: set[str],
    excluded_tokens: set[str],
) -> bool:
    claim_context = claim_tokens - excluded_tokens
    evidence_context = evidence_tokens - excluded_tokens - CUE_TOKENS
    if not claim_context or not evidence_context:
        return False
    return (
        len(claim_context & evidence_context) / min(len(claim_context), len(evidence_context))
        >= MIN_CONTEXT_OVERLAP
    )
