"""Simple lexical retrieval."""

from __future__ import annotations

from math import sqrt
import re

from citeproof.models import Claim, SourceChunk
from citeproof.text import expanded_tokens, normalize_extraction_artifacts

CLAIM_ANCHOR_RE = re.compile(
    r"\b(?:[A-Z]+[A-Za-z0-9.-]*\d+[A-Za-z0-9.-]*|[A-Z][A-Za-z]*[A-Z][A-Za-z0-9.]*|"
    r"[A-Z][a-z]+[A-Z][A-Za-z0-9.]*|[A-Z]{3,}[A-Za-z0-9.-]*)\b"
)
ANCHOR_MATCH_BONUS = 0.25


def retrieve_evidence(claim: Claim, chunks: list[SourceChunk], limit: int = 3) -> list[SourceChunk]:
    """Retrieve source chunks for a claim, scoped to cited keys when present."""

    candidates = _citation_scoped_chunks(claim, chunks)
    scored = [_score_chunk(claim.text, chunk) for chunk in candidates]
    scored = [chunk for chunk in scored if chunk.score > 0]
    return sorted(scored, key=lambda chunk: chunk.score, reverse=True)[:limit]


def cited_keys_present(claim: Claim, chunks: list[SourceChunk]) -> bool:
    """Return whether all cited keys have at least one loaded chunk."""

    available = {chunk.citation_key for chunk in chunks}
    return all(key in available for key in claim.citation_keys)


def _citation_scoped_chunks(claim: Claim, chunks: list[SourceChunk]) -> list[SourceChunk]:
    if not claim.citation_keys:
        return chunks
    cited = set(claim.citation_keys)
    return [chunk for chunk in chunks if chunk.citation_key in cited]


def _score_chunk(claim_text: str, chunk: SourceChunk) -> SourceChunk:
    claim_tokens = set(expanded_tokens(claim_text))
    chunk_tokens = set(expanded_tokens(chunk.text))
    if not claim_tokens or not chunk_tokens:
        return SourceChunk(**{**chunk.__dict__, "score": 0.0})
    overlap = len(claim_tokens & chunk_tokens)
    anchor_overlap = len(_claim_anchor_tokens(claim_text) & chunk_tokens)
    score = overlap / sqrt(len(claim_tokens) * len(chunk_tokens))
    score += anchor_overlap * ANCHOR_MATCH_BONUS
    return SourceChunk(**{**chunk.__dict__, "score": round(score, 4)})


def _claim_anchor_tokens(claim_text: str) -> set[str]:
    normalized = normalize_extraction_artifacts(claim_text)
    return {
        token
        for match in CLAIM_ANCHOR_RE.finditer(normalized)
        for token in expanded_tokens(match.group(0))
    }
