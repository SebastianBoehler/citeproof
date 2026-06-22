"""Sentence-window rationale selection."""

from __future__ import annotations

from collections import Counter
from math import sqrt

from citeproof.models import Claim, EvidenceCandidate, SourceChunk
from citeproof.text import split_sentences, tokenize


def select_rationales(
    claim: Claim,
    chunks: list[SourceChunk],
    limit: int = 3,
    min_score: float = 0.12,
    window_radius: int = 1,
) -> tuple[EvidenceCandidate, ...]:
    """Return sentence/window evidence candidates for a claim."""

    scored: list[EvidenceCandidate] = []
    for chunk in chunks:
        for window in _sentence_windows(chunk.text, window_radius):
            score = _lexical_score(claim.text, window)
            if score >= min_score:
                scored.append(_candidate(chunk, window, score))
    ranked = sorted(scored, key=lambda item: item.lexical_score, reverse=True)[:limit]
    return tuple(
        EvidenceCandidate(
            source_id=item.source_id,
            citation_key=item.citation_key,
            text=item.text,
            chunk_id=item.chunk_id,
            title=item.title,
            page=item.page,
            lexical_score=item.lexical_score,
            semantic_score=item.semantic_score,
            rerank_score=item.rerank_score,
            rank=index,
            retrieval_method=item.retrieval_method,
        )
        for index, item in enumerate(ranked, start=1)
    )


def _sentence_windows(text: str, radius: int) -> tuple[str, ...]:
    sentences = split_sentences(text)
    if not sentences:
        return ()
    windows = []
    for index, _sentence in enumerate(sentences):
        start = max(0, index - radius)
        end = min(len(sentences), index + radius + 1)
        windows.append(" ".join(sentences[start:end]))
    return tuple(dict.fromkeys(windows))


def _candidate(chunk: SourceChunk, text: str, score: float) -> EvidenceCandidate:
    return EvidenceCandidate(
        source_id=chunk.source_id,
        citation_key=chunk.citation_key,
        text=text,
        chunk_id=chunk.chunk_id,
        title=chunk.title,
        page=chunk.page,
        lexical_score=round(score, 4),
        retrieval_method="sentence_window",
    )


def _lexical_score(claim: str, evidence: str) -> float:
    claim_terms = tokenize(claim)
    evidence_terms = tokenize(evidence)
    if not claim_terms or not evidence_terms:
        return 0.0
    claim_counts = Counter(claim_terms)
    evidence_counts = Counter(evidence_terms)
    overlap = sum(min(count, evidence_counts[term]) for term, count in claim_counts.items())
    return overlap / sqrt(len(claim_terms) * len(evidence_terms))
