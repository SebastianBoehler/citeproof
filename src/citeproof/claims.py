"""Context-preserving claim atomization."""

from __future__ import annotations

import re

from citeproof.models import AtomicClaim, Claim, ClaimGroup

AND_SPLIT_RE = re.compile(
    r"^(?P<subject>[A-Z][A-Za-z0-9_.-]+)\s+(?P<first>.+?)\s+and\s+"
    r"(?P<second>(?:spans|contains|uses|trains|provides|computes|captures|"
    r"improves|reduces|increases|decreases|outperforms)\b.+)$"
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
