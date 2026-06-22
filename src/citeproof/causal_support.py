"""Semantic support checks for causal-design evidence."""

from __future__ import annotations

import re

from citeproof.text import token_overlap_ratio

MIN_CAUSAL_SUPPORT_OVERLAP = 0.5

CAUSAL_CLAIM_RE = re.compile(
    r"\b(?:causes?|caused|causal|causally|"
    r"leads?\s+to|led\s+to|results?\s+in|resulted\s+in|drives?|drove)\b",
    re.IGNORECASE,
)
CAUSAL_DESIGN_RE = re.compile(
    r"\b(?:randomi[sz]ed|randomi[sz]ation|randomly\s+assigned|"
    r"controlled\s+(?:trial|experiment|intervention)|treatment\s+arm|"
    r"control\s+(?:group|arm))\b",
    re.IGNORECASE,
)
AFFIRMATIVE_RESULT_RE = re.compile(
    r"\b(?:improves?|improved|increases?|increased|reduces?|reduced|"
    r"lowers?|lowered|decreases?|decreased|raises?|raised|"
    r"outperforms?|outperformed)\b",
    re.IGNORECASE,
)
NEGATED_RESULT_RE = re.compile(
    r"\b(?:does\s+not|did\s+not|failed\s+to|no)\s+"
    r"(?:improve|increase|reduce|lower|decrease|raise|outperform)\b",
    re.IGNORECASE,
)


def has_causal_design_support(claim: str, evidence: str, overlap: float | None = None) -> bool:
    """Return true when explicit causal-design evidence supports a causal claim."""

    score = token_overlap_ratio(claim, evidence) if overlap is None else overlap
    return bool(
        score >= MIN_CAUSAL_SUPPORT_OVERLAP
        and CAUSAL_CLAIM_RE.search(claim)
        and CAUSAL_DESIGN_RE.search(evidence)
        and AFFIRMATIVE_RESULT_RE.search(evidence)
        and not NEGATED_RESULT_RE.search(evidence)
    )
