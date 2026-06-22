"""Heuristic evidence-vs-claim labeling."""

from __future__ import annotations

import re

from citeproof.models import EvidenceJudgment, Label
from citeproof.text import token_overlap_ratio

POSITIVE_CLAIM_RE = re.compile(
    r"\b(outperform|outperforms|improve|improves|improved|increase|increases|higher|better|superior)\b",
    re.IGNORECASE,
)
NEGATING_EVIDENCE_RE = re.compile(
    r"\b(no statistically significant|not significant|does not improve|did not improve|"
    r"failed to improve|comparable to|similar to|no improvement|worse than|lower than)\b",
    re.IGNORECASE,
)
NEGATIVE_CLAIM_RE = re.compile(
    r"\b(no improvement|does not improve|not significant|worse than|lower than|comparable to)\b",
    re.IGNORECASE,
)
POSITIVE_EVIDENCE_RE = re.compile(
    r"\b(significantly improves|outperforms|improves|improved|higher than|better than|superior to)\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?")
UNIVERSAL_CLAIM_RE = re.compile(r"\b(all|always|any|every|universally)\b", re.IGNORECASE)
SCOPED_EVIDENCE_RE = re.compile(
    r"\b(five|some|subset|simulated|sparse-reward|weaker|limited|only|strongest)\b",
    re.IGNORECASE,
)


def judge_evidence(claim: str, evidence: str) -> EvidenceJudgment:
    """Classify whether a source span supports, contradicts, or misses a claim."""

    overlap = token_overlap_ratio(claim, evidence)
    if overlap < 0.18:
        return EvidenceJudgment(Label.UNSUPPORTED, 0.25, "Evidence has too little claim overlap.")

    if _has_numeric_conflict(claim, evidence):
        return EvidenceJudgment(
            Label.CONTRADICTED,
            0.82,
            "Claim and evidence share context but contain conflicting numeric values.",
        )

    if _has_polarity_conflict(claim, evidence):
        return EvidenceJudgment(
            Label.CONTRADICTED,
            0.78,
            "Evidence uses an incompatible polarity for the claimed result.",
        )

    if overlap >= 0.38 and _has_scope_gap(claim, evidence):
        return EvidenceJudgment(
            Label.PARTIALLY_SUPPORTED,
            0.68,
            "Evidence supports a narrower claim than the draft states.",
        )

    if overlap >= 0.68:
        return EvidenceJudgment(Label.SUPPORTED, min(0.95, 0.55 + overlap / 2), "Strong lexical support.")

    if overlap >= 0.38:
        return EvidenceJudgment(
            Label.PARTIALLY_SUPPORTED,
            min(0.78, 0.42 + overlap / 2),
            "Evidence covers part of the claim but not all content.",
        )

    return EvidenceJudgment(Label.UNSUPPORTED, 0.35, "Evidence is related but does not support the claim.")


def _has_polarity_conflict(claim: str, evidence: str) -> bool:
    claim_positive = bool(POSITIVE_CLAIM_RE.search(claim))
    claim_negative = bool(NEGATIVE_CLAIM_RE.search(claim))
    evidence_negative = bool(NEGATING_EVIDENCE_RE.search(evidence))
    evidence_positive = bool(POSITIVE_EVIDENCE_RE.search(evidence))
    return (claim_positive and evidence_negative) or (claim_negative and evidence_positive)


def _has_numeric_conflict(claim: str, evidence: str) -> bool:
    claim_numbers = set(NUMBER_RE.findall(claim))
    evidence_numbers = set(NUMBER_RE.findall(evidence))
    return bool(claim_numbers and evidence_numbers and claim_numbers.isdisjoint(evidence_numbers))


def _has_scope_gap(claim: str, evidence: str) -> bool:
    return bool(UNIVERSAL_CLAIM_RE.search(claim) and SCOPED_EVIDENCE_RE.search(evidence))
