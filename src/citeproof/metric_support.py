"""Semantic support checks for common metric-definition claims."""

from __future__ import annotations

from citeproof.text import expanded_tokens, normalize_extraction_artifacts


def has_metric_definition_support(claim: str, evidence: str) -> bool:
    """Return whether evidence supports compact metric-definition wording."""

    claim_tokens = set(expanded_tokens(claim))
    evidence_tokens = set(expanded_tokens(evidence))
    evidence_norm = normalize_extraction_artifacts(evidence).lower()
    if _supports_weak_dialogue_correlation(claim_tokens, evidence_tokens, evidence_norm):
        return True
    if _supports_bertscore_definition(claim_tokens, evidence_tokens):
        return True
    return _supports_bleurt_definition(claim_tokens, evidence_tokens, evidence_norm)


def _supports_weak_dialogue_correlation(
    claim_tokens: set[str],
    evidence_tokens: set[str],
    evidence_norm: str,
) -> bool:
    claim_terms = {"word", "overlap", "metrics", "correlate", "human", "dialogue"}
    evidence_terms = {"word", "overlap", "metrics", "human", "dialogue"}
    if not claim_terms <= claim_tokens or not evidence_terms <= evidence_tokens:
        return False
    return "weak" in evidence_norm or "small positive correlation" in evidence_norm


def _supports_bertscore_definition(claim_tokens: set[str], evidence_tokens: set[str]) -> bool:
    if "bertscore" not in claim_tokens or "bertscore" not in evidence_tokens:
        return False
    if "contextual" not in evidence_tokens or not _has_stem(evidence_tokens, "embedding"):
        return False
    return bool({"semantic", "surface", "exact", "matching"} & evidence_tokens)


def _supports_bleurt_definition(
    claim_tokens: set[str],
    evidence_tokens: set[str],
    evidence_norm: str,
) -> bool:
    if "bleurt" not in claim_tokens or "bleurt" not in evidence_tokens:
        return False
    if not {"learned", "metric"} <= evidence_tokens:
        return False
    robustness_terms = ("robust", "robustness", "distribution drift", "out-of-domain")
    return any(term in evidence_norm for term in robustness_terms)


def _has_stem(tokens: set[str], stem: str) -> bool:
    return any(token.startswith(stem) for token in tokens)
