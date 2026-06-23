"""Context-preserving claim atomization."""

from __future__ import annotations

import re

from citeproof.models import AtomicClaim, Claim, ClaimGroup

CHECKABLE_VERBS = (
    "captures?",
    "computes?",
    "contains?",
    "decreases?",
    "improves?",
    "increases?",
    "outperforms?",
    "provides?",
    "reduces?",
    "solves?",
    "spans?",
    "trains?",
    "uses?",
)
VERB_PATTERN = "|".join(CHECKABLE_VERBS)
AND_SPLIT_RE = re.compile(
    rf"^(?P<subject>.+?)\s+(?P<first>(?:{VERB_PATTERN})\b.+?)\s+and\s+"
    rf"(?P<second>(?:{VERB_PATTERN})\b.+)$"
)


def atomize_claim(claim: Claim) -> ClaimGroup:
    """Split a claim into smaller checks while preserving original context."""

    text = claim.text.strip()
    match = AND_SPLIT_RE.match(text.rstrip("."))
    if not match:
        atoms = (_atomic(claim, text),)
    else:
        subject = match.group("subject")
        atoms = (
            _atomic(claim, f"{subject} {match.group('first').strip()}."),
            _atomic(claim, f"{subject} {match.group('second').strip()}."),
        )
    return ClaimGroup(original=claim, atoms=atoms)


def _atomic(claim: Claim, text: str) -> AtomicClaim:
    return AtomicClaim(
        text=re.sub(r"\s+", " ", text).strip(),
        context=claim.text,
        citation_keys=claim.citation_keys,
    )
