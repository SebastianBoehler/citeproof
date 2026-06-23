"""Heuristic evidence-vs-claim labeling."""

from __future__ import annotations

import re

from citeproof.causal_support import has_causal_design_support
from citeproof.fact_lenses import compatible_bounded_quantity, inspect_facts
from citeproof.metric_support import has_metric_definition_support
from citeproof.models import EvidenceJudgment, Label
from citeproof.quantities import quantity_mentions
from citeproof.survey_support import has_survey_claim_support
from citeproof.text import academic_token_overlap_ratio, token_overlap_ratio

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
UNIVERSAL_CLAIM_RE = re.compile(r"\b(all|always|any|every|universally)\b", re.IGNORECASE)
SCOPED_EVIDENCE_RE = re.compile(
    r"\b(five|some|subset|simulated|sparse-reward|weaker|limited|only|strongest)\b",
    re.IGNORECASE,
)
METRIC_RE = re.compile(r"\b(f1(?:\s+score)?|accuracy)\b", re.IGNORECASE)
RESOURCE_REDUCTION_CLAIM_RE = re.compile(
    r"\b(reduce|reduces|reduced|lower|lowers|decrease|decreases)\b",
    re.IGNORECASE,
)
SAMPLE_EFFICIENCY_CLAIM_RE = re.compile(r"\bsample\s+efficiency\b", re.IGNORECASE)
SAMPLE_EFFICIENCY_IMPROVE_RE = re.compile(
    r"\b(improve|improves|improved|increase|increases|increased)\b",
    re.IGNORECASE,
)
TIME_REDUCTION_EVIDENCE_RE = re.compile(
    r"\b(?:fewer|less|reduced|half\s+as\s+many)\s+"
    r"(?:training\s+)?(?:hours?|minutes?|seconds?|time)\b|"
    r"\b(?:reduc(?:e|es|ed|ing)|lowers?|decreas(?:e|es|ed|ing))\s+"
    r"(?:training\s+)?(?:hours?|minutes?|seconds?|time)\b|"
    r"\b(?:training\s+)?(?:hours?|minutes?|seconds?|time)\s+"
    r"(?:were|was\s+)?(?:reduced|lower)\b|"
    r"\bless\s+wall[- ]clock\s+time\b",
    re.IGNORECASE,
)
SAMPLE_REDUCTION_EVIDENCE_RE = re.compile(
    r"\b(?:improves?|improved|increases?|increased)\s+sample\s+efficiency\b|"
    r"\b(?:fewer|less|reduced)\s+"
    r"(?:(?:environment\s+)?interactions?|(?:training\s+)?samples?|examples?)\b|"
    r"\b(?:(?:environment\s+)?interactions?|(?:training\s+)?samples?|examples?)\s+"
    r"(?:were|was\s+)?(?:reduced|lower)\b",
    re.IGNORECASE,
)
RESOURCE_NEGATION_RE = re.compile(
    r"\b(does\s+not|did\s+not|failed\s+to|no\s+reduction|no\s+fewer|no\s+less|without)\b",
    re.IGNORECASE,
)
TIME_RESOURCE_TERM_RE = re.compile(
    r"\b(?:training\s+)?(?:hours?|minutes?|seconds?|time)\b|"
    r"\bwall[- ]clock\b",
    re.IGNORECASE,
)
SAMPLE_RESOURCE_TERM_RE = re.compile(
    r"\b(?:environment\s+)?interactions?\b|"
    r"\b(?:training\s+)?samples?\b|"
    r"\bexamples?\b",
    re.IGNORECASE,
)


def judge_evidence(claim: str, evidence: str) -> EvidenceJudgment:
    """Classify whether a source span supports, contradicts, or misses a claim."""

    overlap = token_overlap_ratio(claim, evidence)
    survey_support = has_survey_claim_support(claim, evidence)
    semantic_support = survey_support or _has_semantic_support(claim, evidence, overlap)
    if overlap < 0.18 and not semantic_support:
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

    if fact_inspection.label == Label.PARTIALLY_SUPPORTED and not (
        survey_support and _is_hedge_only(fact_inspection.findings)
    ):
        return EvidenceJudgment(
            Label.PARTIALLY_SUPPORTED, 0.68, "; ".join(fact_inspection.findings)
        )

    if overlap >= 0.38 and _has_scope_gap(claim, evidence):
        return EvidenceJudgment(
            Label.PARTIALLY_SUPPORTED,
            0.68,
            "Evidence supports a narrower claim than the draft states.",
        )

    resource_claim = _claims_resource_reduction(claim)
    if overlap >= 0.68 and not resource_claim:
        return EvidenceJudgment(Label.SUPPORTED, min(0.95, 0.55 + overlap / 2), "Strong lexical support.")

    if semantic_support:
        return EvidenceJudgment(Label.SUPPORTED, 0.74, "Anchored paraphrase support.")

    if overlap >= 0.38 and resource_claim:
        return EvidenceJudgment(
            Label.PARTIALLY_SUPPORTED,
            min(0.78, 0.42 + overlap / 2),
            "Evidence mentions the resource dimension but not the claimed reduction.",
        )

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
    claim_mentions = quantity_mentions(claim)
    evidence_mentions = quantity_mentions(evidence)
    if len(claim_mentions) != 1 or len(evidence_mentions) != 1:
        return False
    claim_mention = claim_mentions[0]
    evidence_mention = evidence_mentions[0]
    return (
        claim_mention.unit == evidence_mention.unit
        and claim_mention.number != evidence_mention.number
        and not compatible_bounded_quantity((claim_mention,), (evidence_mention,), claim, evidence)
    )


def _has_scope_gap(claim: str, evidence: str) -> bool:
    return bool(UNIVERSAL_CLAIM_RE.search(claim) and SCOPED_EVIDENCE_RE.search(evidence))


def _is_hedge_only(findings: tuple[str, ...]) -> bool:
    return bool(findings) and all(
        "hedged" in finding.lower() or "inconclusive" in finding.lower()
        for finding in findings
    )


def _has_semantic_support(claim: str, evidence: str, overlap: float) -> bool:
    claim_lower = claim.lower()
    evidence_lower = evidence.lower()
    if _has_resource_reduction_support(claim, evidence, overlap):
        return True
    if _claims_resource_reduction(claim):
        return False
    if has_causal_design_support(claim, evidence, overlap):
        return True
    if has_metric_definition_support(claim, evidence):
        return True
    if has_survey_claim_support(claim, evidence):
        return True
    academic_overlap = academic_token_overlap_ratio(claim, evidence)
    if overlap >= 0.4 and academic_overlap >= 0.68:
        return True
    if overlap >= 0.3 and academic_overlap >= 0.75:
        return True
    return bool(
        "languages" in claim_lower
        and "languages" in evidence_lower
        and ("spans" in claim_lower or "covers" in claim_lower)
        and ("covers" in evidence_lower or "spans" in evidence_lower)
        and ("multiple" in evidence_lower or "diverse" in evidence_lower)
        and overlap >= 0.35
    )


def _has_resource_reduction_support(claim: str, evidence: str, overlap: float) -> bool:
    if overlap < 0.35:
        return False
    if _claims_training_time_reduction(claim):
        return _has_affirmative_resource_reduction(
            evidence, TIME_REDUCTION_EVIDENCE_RE, TIME_RESOURCE_TERM_RE
        )
    if _claims_sample_efficiency_reduction(claim):
        return _has_affirmative_resource_reduction(
            evidence, SAMPLE_REDUCTION_EVIDENCE_RE, SAMPLE_RESOURCE_TERM_RE
        )
    return False


def _claims_resource_reduction(claim: str) -> bool:
    return _claims_training_time_reduction(claim) or _claims_sample_efficiency_reduction(claim)


def _claims_training_time_reduction(claim: str) -> bool:
    claim_lower = claim.lower()
    return bool(
        "training" in claim_lower
        and "time" in claim_lower
        and RESOURCE_REDUCTION_CLAIM_RE.search(claim)
    )


def _claims_sample_efficiency_reduction(claim: str) -> bool:
    return bool(
        SAMPLE_EFFICIENCY_CLAIM_RE.search(claim)
        and (
            SAMPLE_EFFICIENCY_IMPROVE_RE.search(claim)
            or RESOURCE_REDUCTION_CLAIM_RE.search(claim)
        )
    )


def _has_affirmative_resource_reduction(
    evidence: str,
    reduction_pattern: re.Pattern[str],
    resource_term_pattern: re.Pattern[str],
) -> bool:
    return bool(
        reduction_pattern.search(evidence)
        and not _has_nearby_match(
            RESOURCE_NEGATION_RE, resource_term_pattern, evidence, max_gap=80
        )
    )


def _has_nearby_match(
    left_pattern: re.Pattern[str],
    right_pattern: re.Pattern[str],
    text: str,
    *,
    max_gap: int = 60,
) -> bool:
    lefts = tuple(left_pattern.finditer(text))
    rights = tuple(right_pattern.finditer(text))
    return any(abs(left.start() - right.start()) <= max_gap for left in lefts for right in rights)
