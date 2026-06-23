"""Sentence-window rationale selection."""

from __future__ import annotations

from collections import Counter
from math import sqrt
import re

from citeproof.metric_support import has_metric_definition_support
from citeproof.models import Claim, EvidenceCandidate, SourceChunk
from citeproof.text import expanded_tokens, split_sentences, tokenize

CONFLICT_RERANK_BONUS = 0.22
METRIC_SUPPORT_RERANK_BONUS = 0.3
CONFLICT_CUE_RE = re.compile(
    r"\b("
    r"unchanged|no\s+change|no\s+difference|no\s+improvement|no\s+reduction|"
    r"does\s+not\s+improve|did\s+not\s+improve|failed\s+to\s+improve|"
    r"not\s+statistically\s+significant|comparable\s+to|equivalent\s+to|worse\s+than"
    r")\b",
    re.IGNORECASE,
)
SOURCE_IDENTITY_RE = re.compile(
    r"^(?P<subject>.+?)\s+is\s+(?:an?|the)\s+.+\b(?:benchmark|collection|corpus|dataset)\b",
    re.IGNORECASE,
)
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")


def select_rationales(
    claim: Claim,
    chunks: list[SourceChunk],
    limit: int = 3,
    min_score: float = 0.12,
    window_radius: int = 1,
) -> tuple[EvidenceCandidate, ...]:
    """Return sentence/window evidence candidates for a claim."""

    scored: list[EvidenceCandidate] = []
    identity_groups = _source_identity_token_groups(claim.text)
    for chunk in chunks:
        for window in _sentence_windows(chunk.text, window_radius):
            if identity_groups and not _matches_identity_group(identity_groups, expanded_tokens(window)):
                continue
            lexical_score = _lexical_score(claim.text, window)
            if lexical_score < min_score:
                continue
            rerank_score = (
                lexical_score
                + _conflict_rerank_bonus(window)
                + _metric_support_rerank_bonus(claim.text, window)
            )
            scored.append(_candidate(chunk, window, lexical_score, rerank_score))
    ranked = sorted(
        scored,
        key=lambda item: (item.rerank_score or item.lexical_score, item.lexical_score),
        reverse=True,
    )[:limit]
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


def _candidate(
    chunk: SourceChunk,
    text: str,
    lexical_score: float,
    rerank_score: float,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        source_id=chunk.source_id,
        citation_key=chunk.citation_key,
        text=text,
        chunk_id=chunk.chunk_id,
        title=chunk.title,
        page=chunk.page,
        lexical_score=round(lexical_score, 4),
        rerank_score=round(rerank_score, 4),
        retrieval_method="sentence_window",
    )


def _lexical_score(claim: str, evidence: str) -> float:
    claim_terms = expanded_tokens(claim)
    evidence_terms = expanded_tokens(evidence)
    if not claim_terms or not evidence_terms:
        return 0.0
    claim_counts = Counter(claim_terms)
    evidence_counts = Counter(evidence_terms)
    overlap = sum(min(count, evidence_counts[term]) for term, count in claim_counts.items())
    return overlap / sqrt(len(claim_terms) * len(evidence_terms))


def _conflict_rerank_bonus(text: str) -> float:
    return CONFLICT_RERANK_BONUS if CONFLICT_CUE_RE.search(text) else 0.0


def _metric_support_rerank_bonus(claim: str, text: str) -> float:
    return METRIC_SUPPORT_RERANK_BONUS if has_metric_definition_support(claim, text) else 0.0


def _source_identity_token_groups(claim: str) -> tuple[frozenset[str], ...]:
    match = SOURCE_IDENTITY_RE.match(claim)
    if not match:
        return ()
    subject = match.group("subject")
    camel_spaced = CAMEL_BOUNDARY_RE.sub(" ", subject)
    groups = [
        frozenset(term for term in tokenize(source) if len(term) > 3)
        for source in (subject, camel_spaced)
    ]
    return tuple(dict.fromkeys(group for group in groups if group))


def _matches_identity_group(groups: tuple[frozenset[str], ...], window_tokens: list[str]) -> bool:
    return any(all(_has_identity_term(term, window_tokens) for term in group) for group in groups)


def _has_identity_term(term: str, window_tokens: list[str]) -> bool:
    return any(
        token == term
        or (len(token) >= 4 and len(term) >= 4 and (token.startswith(term) or term.startswith(token)))
        for token in window_tokens
    )
