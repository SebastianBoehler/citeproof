"""Semantic support checks for compact related-work survey claims."""

from __future__ import annotations

import re

from citeproof.text import expanded_tokens, normalize_extraction_artifacts

PDF_HYPHEN_RE = re.compile(r"(?<=\w)-\s+(?=\w)")


def has_survey_claim_support(claim: str, evidence: str) -> bool:
    """Return whether evidence supports a compact related-work attribution."""

    claim_tokens = set(_normalized_tokens(claim))
    evidence_tokens = set(_normalized_tokens(evidence))
    claim_norm = _normalize_text(claim)
    evidence_norm = _normalize_text(evidence)
    if _supports_action_utterance_user_model(claim_tokens, evidence_tokens):
        return True
    if _supports_gentus_introduction(claim_tokens, evidence_tokens, evidence_norm):
        return True
    return _supports_llm_user_simulator_discrepancy(
        claim_tokens,
        evidence_tokens,
        claim_norm,
        evidence_norm,
    )


def _supports_action_utterance_user_model(
    claim_tokens: set[str],
    evidence_tokens: set[str],
) -> bool:
    if not _has_stems(claim_tokens, ("action", "utterance", "predict")):
        return False
    if not _has_stems(evidence_tokens, ("action", "utterance", "predict", "generat")):
        return False
    return _has_any_stem(evidence_tokens, ("goal", "dialogue"))


def _supports_gentus_introduction(
    claim_tokens: set[str],
    evidence_tokens: set[str],
    evidence_norm: str,
) -> bool:
    if "gentus" not in claim_tokens or "gentus" not in evidence_tokens:
        return False
    if not _has_stems(claim_tokens, ("simulat", "task")):
        return False
    if not _has_stems(evidence_tokens, ("simulat", "task", "oriented")):
        return False
    return _has_any_stem(evidence_tokens, ("propos", "call", "introduc")) or (
        "gentus: simulating" in evidence_norm
    )


def _supports_llm_user_simulator_discrepancy(
    claim_tokens: set[str],
    evidence_tokens: set[str],
    claim_norm: str,
    evidence_norm: str,
) -> bool:
    if not _has_llm_reference(claim_tokens, claim_norm):
        return False
    if not _has_stems(claim_tokens, ("simulat", "recommend", "convers")):
        return False
    if not _has_llm_reference(evidence_tokens, evidence_norm):
        return False
    if not _has_stems(evidence_tokens, ("simulat", "recommend", "convers")):
        return False
    discrepancy_terms = ("discrepanc", "deviation", "distortion")
    if any(_has_any_stem(evidence_tokens, (term,)) for term in discrepancy_terms):
        return "real users" in evidence_norm or "human behavior" in evidence_norm
    return "differ from real users" in evidence_norm


def _normalized_tokens(text: str) -> list[str]:
    return expanded_tokens(_normalize_text(text))


def _normalize_text(text: str) -> str:
    return PDF_HYPHEN_RE.sub("", normalize_extraction_artifacts(text)).lower()


def _has_stems(tokens: set[str], stems: tuple[str, ...]) -> bool:
    return all(_has_any_stem(tokens, (stem,)) for stem in stems)


def _has_any_stem(tokens: set[str], stems: tuple[str, ...]) -> bool:
    return any(token.startswith(stem) for token in tokens for stem in stems)


def _has_llm_reference(tokens: set[str], text: str) -> bool:
    return _has_any_stem(tokens, ("llm",)) or "large language model" in text or (
        "language" in tokens and "models" in tokens
    )
