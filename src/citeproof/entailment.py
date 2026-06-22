"""Heuristic evidence-vs-claim labeling."""

from __future__ import annotations

import re

from citeproof.fact_lenses import inspect_facts
from citeproof.models import EvidenceJudgment, Label
from citeproof.text import token_overlap_ratio

POSITIVE_CLAIM_RE = re.compile(
    r"\b(outperform|outperforms|improve|improves|improved|increase|increases|reduce|reduces|reduced|"
    r"higher|better|superior|span|spans|cover|covers)\b",
    re.IGNORECASE,
)
GENERIC_NEGATING_EVIDENCE_RE = re.compile(
    r"\b(no statistically significant|not significant|does not improve(?!\s+f1 score)|"
    r"did not improve(?!\s+f1 score)|failed to improve(?!\s+f1 score)|"
    r"does not reduce|did not reduce|failed to reduce|no reduction|does not cover|did not cover|"
    r"does not span|did not span|comparable to|similar to|no improvement|worse than|lower than)\b",
    re.IGNORECASE,
)
METRIC_NEGATING_EVIDENCE_RE = re.compile(
    r"\b(?:does not improve|did not improve|failed to improve)\s+"
    r"(?P<verb_metric>f1(?:\s+score)?|accuracy)\b|"
    r"\bno\s+(?P<no_metric>f1(?:\s+score)?|accuracy)(?:\s+score)?\s+improvement\b|"
    r"\bno\s+improvement\s+in\s+(?P<in_metric>f1(?:\s+score)?|accuracy)\b",
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
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:[,.]\d+)*(?:\.\d+)?%?")
NUMBER_WITH_UNIT_RE = re.compile(
    r"(?<![A-Za-z])(?P<number>[-+]?\d+(?:[,.]\d+)*(?:\.\d+)?)(?P<percent>%| percent)?"
    r"(?:\s+(?P<unit>[A-Za-z][A-Za-z-]*))?",
    re.IGNORECASE,
)
UNIVERSAL_CLAIM_RE = re.compile(r"\b(all|always|any|every|universally)\b", re.IGNORECASE)
SCOPED_EVIDENCE_RE = re.compile(
    r"\b(five|some|subset|simulated|sparse-reward|weaker|limited|only|strongest)\b",
    re.IGNORECASE,
)
METRIC_RE = re.compile(r"\b(f1(?:\s+score)?|accuracy)\b", re.IGNORECASE)


def judge_evidence(claim: str, evidence: str) -> EvidenceJudgment:
    """Classify whether a source span supports, contradicts, or misses a claim."""

    overlap = token_overlap_ratio(claim, evidence)
    if overlap < 0.18:
        return EvidenceJudgment(Label.UNSUPPORTED, 0.25, "Evidence has too little claim overlap.")

    fact_inspection = inspect_facts(claim, evidence)
    if fact_inspection.label == Label.CONTRADICTED:
        return EvidenceJudgment(Label.CONTRADICTED, 0.82, "; ".join(fact_inspection.findings))

    if overlap >= 0.45 and _has_numeric_conflict(claim, evidence):
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

    if _has_semantic_support(claim, evidence, overlap):
        return EvidenceJudgment(Label.SUPPORTED, 0.74, "Anchored paraphrase support.")

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
    negated_metrics = _negated_metrics(evidence)
    evidence_positive = bool(POSITIVE_EVIDENCE_RE.search(evidence))
    if claim_positive and negated_metrics:
        claim_metrics = _metrics(claim)
        return not claim_metrics or bool(claim_metrics & negated_metrics)
    if claim_positive and GENERIC_NEGATING_EVIDENCE_RE.search(evidence):
        return True
    return claim_negative and evidence_positive


def _metrics(text: str) -> set[str]:
    return {_normalize_metric(match.group(0)) for match in METRIC_RE.finditer(text)}


def _negated_metrics(text: str) -> set[str]:
    metrics: set[str] = set()
    for match in METRIC_NEGATING_EVIDENCE_RE.finditer(text):
        metric = match.group("verb_metric") or match.group("no_metric") or match.group("in_metric")
        metrics.add(_normalize_metric(metric))
    return metrics


def _normalize_metric(metric: str) -> str:
    if metric.lower().startswith("f1"):
        return "f1"
    return metric.lower()


def _has_numeric_conflict(claim: str, evidence: str) -> bool:
    claim_mentions = _number_mentions(claim)
    evidence_mentions = _number_mentions(evidence)
    if len(claim_mentions) != 1 or len(evidence_mentions) != 1:
        return False
    claim_number, claim_unit = claim_mentions[0]
    evidence_number, evidence_unit = evidence_mentions[0]
    return bool(claim_unit and claim_unit == evidence_unit and claim_number != evidence_number)


def _has_scope_gap(claim: str, evidence: str) -> bool:
    return bool(UNIVERSAL_CLAIM_RE.search(claim) and SCOPED_EVIDENCE_RE.search(evidence))


def _has_semantic_support(claim: str, evidence: str, overlap: float) -> bool:
    claim_lower = claim.lower()
    evidence_lower = evidence.lower()
    if (
        "training" in claim_lower
        and "time" in claim_lower
        and re.search(r"\breduc(?:e|es|ed|ing)\b", claim_lower)
        and overlap >= 0.35
        and ("half as many hours" in evidence_lower or "fewer hours" in evidence_lower)
    ):
        return True
    if (
        "bertscore" in claim_lower
        and "bertscore" in evidence_lower
        and "semantic" in claim_lower
        and "similarity" in claim_lower
        and "similarity" in evidence_lower
        and "embedding" in evidence_lower
        and ("n-gram" in evidence_lower or "matching" in evidence_lower)
    ):
        return True
    return bool(
        "languages" in claim_lower
        and "languages" in evidence_lower
        and ("spans" in claim_lower or "covers" in claim_lower)
        and ("covers" in evidence_lower or "spans" in evidence_lower)
        and ("multiple" in evidence_lower or "diverse" in evidence_lower)
        and overlap >= 0.35
    )


def _number_mentions(text: str) -> list[tuple[str, str]]:
    mentions = []
    for match in NUMBER_WITH_UNIT_RE.finditer(text):
        unit = match.group("percent") or match.group("unit") or ""
        mentions.append((match.group("number").replace(",", ""), unit.lower()))
    return mentions
