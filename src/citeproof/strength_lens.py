"""Deterministic checks for claim-strength overstatements."""

from __future__ import annotations

import re

from citeproof.text import tokenize

MAGNITUDE_NOUNS = (
    "benefits?",
    "decreases?",
    "effects?",
    "gains?",
    "improvements?",
    "increases?",
    "reductions?",
)
MAGNITUDE_OBJECT = rf"(?:\w+\s+){{0,3}}(?:{'|'.join(MAGNITUDE_NOUNS)})"
STRONG_MAGNITUDE_RE = re.compile(
    rf"\b(?P<value>large|substantial)\s+{MAGNITUDE_OBJECT}\b",
    re.IGNORECASE,
)
WEAK_MAGNITUDE_RE = re.compile(
    rf"\b(?P<value>small|modest)\s+{MAGNITUDE_OBJECT}\b",
    re.IGNORECASE,
)
NO_OVERHEAD_RE = re.compile(r"\bno(?:\s+\w+){0,5}\s+overheads?\b", re.IGNORECASE)
WEAK_OVERHEAD_RE = re.compile(
    r"\b(?P<value>small|some|non[- ]?zero)(?:\s+\w+){0,5}\s+overheads?\b",
    re.IGNORECASE,
)
CAUSAL_CLAIM_RE = re.compile(
    r"\b(?P<value>causes|caused|proves|demonstrates)\b",
    re.IGNORECASE,
)
WEAK_CAUSAL_RE = re.compile(
    r"\b(?P<value>associated|correlated|suggests|may)\b",
    re.IGNORECASE,
)
RANKING_CLAIM_RE = re.compile(
    r"\b(?P<value>best|top[- ]performing|highest)\b",
    re.IGNORECASE,
)
WEAK_RANKING_RE = re.compile(r"\b(?P<value>competitive|comparable)\b", re.IGNORECASE)
COMPLETE_RE = re.compile(r"\b(?P<value>fully|completely)\b", re.IGNORECASE)
RECOVERY_RE = re.compile(r"\b(recovers?|reconstructs?|restores?)\b", re.IGNORECASE)
PARTIAL_RE = re.compile(r"\b(?P<value>partial|partially)\b", re.IGNORECASE)
TRIGGER_WORDS_RE = re.compile(
    r"\b("
    r"associated|best|caused|causes|comparable|competitive|completely|correlated|"
    r"demonstrates|fully|highest|large|may|modest|no|nonzero|overheads?|partial|"
    r"partially|proves|recovers?|reconstructs?|restores?|small|some|substantial|"
    r"suggests|top|performing|zero"
    r")\b",
    re.IGNORECASE,
)
CONTEXT_THRESHOLD = 0.67


def inspect_strength_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts where evidence directly weakens claim strength."""

    findings: list[str] = []
    claim_magnitude = STRONG_MAGNITUDE_RE.search(claim)
    evidence_magnitude = WEAK_MAGNITUDE_RE.search(evidence)
    if claim_magnitude and evidence_magnitude and _context_overlaps(claim, evidence):
        findings.append(
            "Magnitude conflict: claim says "
            f"{claim_magnitude.group('value').lower()} while evidence says "
            f"{evidence_magnitude.group('value').lower()}."
        )

    evidence_overhead = WEAK_OVERHEAD_RE.search(evidence)
    if NO_OVERHEAD_RE.search(claim) and evidence_overhead and _context_overlaps(claim, evidence):
        findings.append(
            "Overhead conflict: claim says no overhead while evidence says "
            f"{evidence_overhead.group('value').lower()} overhead."
        )

    return tuple(dict.fromkeys(findings))


def inspect_strength_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return softer strength tensions that should block full support."""

    findings: list[str] = []
    claim_causal = CAUSAL_CLAIM_RE.search(claim)
    evidence_causal = WEAK_CAUSAL_RE.search(evidence)
    if claim_causal and evidence_causal and _context_overlaps(claim, evidence):
        findings.append(
            "Causal overstatement tension: claim asserts causality while evidence is weaker."
        )

    claim_ranking = RANKING_CLAIM_RE.search(claim)
    evidence_ranking = WEAK_RANKING_RE.search(evidence)
    if claim_ranking and evidence_ranking and _context_overlaps(claim, evidence):
        findings.append(
            "Ranking overstatement tension: claim asserts top rank while evidence is weaker."
        )

    if (
        COMPLETE_RE.search(claim)
        and RECOVERY_RE.search(claim)
        and PARTIAL_RE.search(evidence)
        and _context_overlaps(claim, evidence)
    ):
        findings.append(
            "Completeness overstatement tension: claim asserts full recovery while evidence is partial."
        )

    return tuple(dict.fromkeys(findings))


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= (
        CONTEXT_THRESHOLD
    )


def _context_tokens(text: str) -> set[str]:
    normalized = re.sub(r"\bnon[- ]?zero\b", " ", text, flags=re.IGNORECASE)
    return set(tokenize(TRIGGER_WORDS_RE.sub(" ", normalized)))
