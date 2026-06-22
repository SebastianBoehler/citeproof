"""Shared data models for CiteProof."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from typing import Any, cast


class Label(StrEnum):
    """Claim verification labels."""

    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"
    UNCERTAIN = "uncertain"


class FailureMode(StrEnum):
    """Structured reasons a claim cannot be strictly verified."""

    MISSING_BIBLIOGRAPHY_KEY = "missing_bibliography_key"
    METADATA_NOT_VERIFIED = "metadata_not_verified"
    SOURCE_NOT_RESOLVED = "source_not_resolved"
    WEAK_RETRIEVAL = "weak_retrieval"
    NO_RATIONALE_SPAN = "no_rationale_span"
    MISSING_ATOM_SUPPORT = "missing_atom_support"
    NUMERIC_CONFLICT = "numeric_conflict"
    YEAR_CONFLICT = "year_conflict"
    UNIT_CONFLICT = "unit_conflict"
    ENTITY_CONFLICT = "entity_conflict"
    NEGATION_CONFLICT = "negation_conflict"
    COMPARISON_DIRECTION_CONFLICT = "comparison_direction_conflict"
    SCOPE_OVERSTATEMENT = "scope_overstatement"
    HEDGED_EVIDENCE = "hedged_evidence"
    SOURCE_SILENCE = "source_silence"
    MODEL_DISAGREEMENT = "model_disagreement"
    CONFLICTING_SOURCES = "conflicting_sources"


@dataclass(frozen=True)
class Claim:
    """An atomic draft claim and its citation keys."""

    text: str
    citation_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class AtomicClaim:
    """A smaller checkable claim with original local context preserved."""

    text: str
    context: str
    citation_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaimGroup:
    """A parsed claim and its atomic subclaims."""

    original: Claim
    atoms: tuple[AtomicClaim, ...]


@dataclass(frozen=True)
class Source:
    """A loaded source document."""

    source_id: str
    text: str
    citation_key: str
    title: str | None = None
    path: str | None = None
    pages: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceChunk:
    """A searchable source chunk."""

    source_id: str
    text: str
    citation_key: str
    chunk_id: str
    title: str | None = None
    page: int | None = None
    score: float = 0.0

    def to_evidence(self) -> "EvidenceSpan":
        return EvidenceSpan(
            source_id=self.source_id,
            text=self.text,
            citation_key=self.citation_key,
            page=self.page,
            score=self.score,
            title=self.title,
        )


@dataclass(frozen=True)
class EvidenceSpan:
    """A source span used to judge a claim."""

    source_id: str
    text: str
    citation_key: str | None = None
    page: int | None = None
    score: float = 0.0
    title: str | None = None


@dataclass(frozen=True)
class EvidenceCandidate:
    """A retrieved evidence candidate with retrieval diagnostics."""

    source_id: str
    citation_key: str
    text: str
    chunk_id: str
    title: str | None = None
    page: int | None = None
    lexical_score: float = 0.0
    semantic_score: float | None = None
    rerank_score: float | None = None
    rank: int = 0
    retrieval_method: str = "lexical"

    def to_evidence(self) -> EvidenceSpan:
        return EvidenceSpan(
            source_id=self.source_id,
            text=self.text,
            citation_key=self.citation_key,
            page=self.page,
            score=self.lexical_score,
            title=self.title,
        )

    def to_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], _serialize(self))


@dataclass(frozen=True)
class RationaleSpan:
    """Evidence text selected as the rationale for an atomic judgment."""

    source_id: str
    citation_key: str
    text: str
    page: int | None = None
    section: str | None = None
    relation: str = "undetermined"
    score: float = 0.0
    rank: int = 0

    def to_evidence(self) -> EvidenceSpan:
        return EvidenceSpan(
            source_id=self.source_id,
            text=self.text,
            citation_key=self.citation_key,
            page=self.page,
            score=self.score,
        )


@dataclass(frozen=True)
class AtomVerification:
    """Verification result for one atomic claim."""

    text: str
    context: str
    label: Label
    confidence: float
    rationales: tuple[RationaleSpan, ...] = ()
    failure_mode: FailureMode | None = None
    reason: str = ""
    candidate_count: int = 0
    support_candidate_count: int = 0
    contradiction_candidate_count: int = 0
    best_support_rank: int | None = None
    best_contradiction_rank: int | None = None


@dataclass(frozen=True)
class ClaimVerificationTrace:
    """Strict verifier trace for source gates, atoms, and final review action."""

    claim: str
    citations: tuple[str, ...]
    source_gate_status: str
    atom_verifications: tuple[AtomVerification, ...]
    final_label: Label
    final_confidence: float
    final_failure_mode: FailureMode | None
    review_action: str


@dataclass(frozen=True)
class VerificationResult:
    """A claim verification result with evidence and rationale."""

    claim: str
    label: Label
    confidence: float
    citations: tuple[str, ...]
    evidence: tuple[EvidenceSpan, ...]
    reason: str
    failure_mode: FailureMode | None = None
    trace: ClaimVerificationTrace | None = None

    def to_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], _serialize(self))


@dataclass(frozen=True)
class EvidenceJudgment:
    """A single evidence-vs-claim judgment."""

    label: Label
    confidence: float
    reason: str
    failure_mode: FailureMode | None = None


@dataclass(frozen=True)
class FactInspection:
    """Deterministic fact-lens result for one claim/evidence pair."""

    label: Label | None
    findings: tuple[str, ...] = ()


def _serialize(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return tuple(_serialize(item) for item in value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {_serialize(key): _serialize(item) for key, item in value.items()}
    return value
