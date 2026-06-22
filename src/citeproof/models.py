"""Shared data models for CiteProof."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class Label(StrEnum):
    """Claim verification labels."""

    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"
    UNCERTAIN = "uncertain"


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
class VerificationResult:
    """A claim verification result with evidence and rationale."""

    claim: str
    label: Label
    confidence: float
    citations: tuple[str, ...]
    evidence: tuple[EvidenceSpan, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["label"] = self.label.value
        return data


@dataclass(frozen=True)
class EvidenceJudgment:
    """A single evidence-vs-claim judgment."""

    label: Label
    confidence: float
    reason: str
