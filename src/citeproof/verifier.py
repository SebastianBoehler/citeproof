"""Claim and draft verification orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from citeproof.entailment import judge_evidence
from citeproof.models import Claim, EvidenceJudgment, Label, SourceChunk, VerificationResult
from citeproof.parser import parse_claims
from citeproof.retrieval import cited_keys_present, retrieve_evidence
from citeproof.sources import build_chunks, load_sources

Judge = Callable[[str, str], EvidenceJudgment]


def verify_claim(
    claim: Claim,
    chunks: list[SourceChunk],
    evidence_limit: int = 3,
    judge: Judge = judge_evidence,
) -> VerificationResult:
    """Verify one claim against source chunks."""

    if claim.citation_keys and not cited_keys_present(claim, chunks):
        return VerificationResult(
            claim=claim.text,
            label=Label.UNCERTAIN,
            confidence=0.2,
            citations=claim.citation_keys,
            evidence=(),
            reason="At least one cited source key is missing from the loaded source set.",
        )

    retrieved = retrieve_evidence(claim, chunks, limit=evidence_limit)
    if not retrieved:
        return VerificationResult(
            claim=claim.text,
            label=Label.UNSUPPORTED,
            confidence=0.3,
            citations=claim.citation_keys,
            evidence=(),
            reason="No overlapping evidence was retrieved from the cited source.",
        )

    judgments = [(chunk, judge(claim.text, chunk.text)) for chunk in retrieved]
    chosen_chunk, chosen_judgment = _choose_judgment(judgments)
    evidence = tuple(chunk.to_evidence() for chunk, _judgment in judgments)
    return VerificationResult(
        claim=claim.text,
        label=chosen_judgment.label,
        confidence=round(chosen_judgment.confidence, 3),
        citations=claim.citation_keys,
        evidence=evidence,
        reason=f"{chosen_judgment.reason} Top source: {chosen_chunk.source_id}.",
    )


def verify_draft(
    draft_path: str | Path,
    source_dir: str | Path,
    judge: Judge = judge_evidence,
) -> list[VerificationResult]:
    """Verify every citation-bearing claim in a draft file."""

    draft = Path(draft_path).read_text(encoding="utf-8")
    claims = parse_claims(draft)
    chunks = build_chunks(load_sources(source_dir))
    return [verify_claim(claim, chunks, judge=judge) for claim in claims]


def verify_claim_text(
    claim_text: str,
    source_dir: str | Path,
    citation_keys: list[str] | None = None,
    judge: Judge = judge_evidence,
) -> VerificationResult:
    """Verify ad-hoc claim text against a source directory."""

    chunks = build_chunks(load_sources(source_dir))
    return verify_claim(Claim(claim_text, tuple(citation_keys or ())), chunks, judge=judge)


def _choose_judgment(
    judgments: list[tuple[SourceChunk, EvidenceJudgment]],
) -> tuple[SourceChunk, EvidenceJudgment]:
    priority = {
        Label.CONTRADICTED: 4,
        Label.SUPPORTED: 3,
        Label.PARTIALLY_SUPPORTED: 2,
        Label.UNSUPPORTED: 1,
        Label.UNCERTAIN: 0,
    }
    return max(judgments, key=lambda item: (priority[item[1].label], item[1].confidence))
