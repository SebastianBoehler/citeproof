"""Claim and draft verification orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from citeproof.adjudicator import adjudicate_evidence, combine_atom_judgments
from citeproof.claims import atomize_claim
from citeproof.entailment import judge_evidence
from citeproof.models import (
    AtomVerification,
    Claim,
    ClaimVerificationTrace,
    EvidenceCandidate,
    EvidenceJudgment,
    FailureMode,
    Label,
    RationaleSpan,
    SourceChunk,
    VerificationResult,
)
from citeproof.parser import parse_claims
from citeproof.rationales import select_rationales
from citeproof.retrieval import cited_keys_present, retrieve_evidence
from citeproof.sources import build_chunks, load_sources

Judge = Callable[[str, str], EvidenceJudgment]

CHUNK_CANDIDATE_LIMIT = 8
RATIONALE_CANDIDATE_LIMIT = 5
RATIONALE_MIN_SCORE = 0.08


def verify_claim(
    claim: Claim,
    chunks: list[SourceChunk],
    evidence_limit: int = 3,
    judge: Judge = judge_evidence,
) -> VerificationResult:
    """Verify one claim against source chunks."""

    if claim.citation_keys and not cited_keys_present(claim, chunks):
        trace = ClaimVerificationTrace(
            claim=claim.text,
            citations=claim.citation_keys,
            source_gate_status="source_not_resolved",
            atom_verifications=(),
            final_label=Label.UNCERTAIN,
            final_confidence=0.2,
            final_failure_mode=FailureMode.SOURCE_NOT_RESOLVED,
            review_action="load cited source or fix citation key",
        )
        return VerificationResult(
            claim=claim.text,
            label=Label.UNCERTAIN,
            confidence=0.2,
            citations=claim.citation_keys,
            evidence=(),
            reason="At least one cited source key is missing from the loaded source set.",
            failure_mode=FailureMode.SOURCE_NOT_RESOLVED,
            trace=trace,
        )

    retrieved = retrieve_evidence(claim, chunks, limit=max(evidence_limit, CHUNK_CANDIDATE_LIMIT))
    if not retrieved:
        trace = ClaimVerificationTrace(
            claim=claim.text,
            citations=claim.citation_keys,
            source_gate_status="passed",
            atom_verifications=(),
            final_label=Label.UNSUPPORTED,
            final_confidence=0.3,
            final_failure_mode=FailureMode.WEAK_RETRIEVAL,
            review_action="find stronger evidence or remove citation",
        )
        return VerificationResult(
            claim=claim.text,
            label=Label.UNSUPPORTED,
            confidence=0.3,
            citations=claim.citation_keys,
            evidence=(),
            reason="No overlapping evidence was retrieved from the cited source.",
            failure_mode=FailureMode.WEAK_RETRIEVAL,
            trace=trace,
        )

    atom_verifications = _verify_atoms(claim, retrieved, judge)
    atom_judgment = combine_atom_judgments(
        [
            EvidenceJudgment(atom.label, atom.confidence, atom.reason, atom.failure_mode)
            for atom in atom_verifications
        ]
    )
    evidence = tuple(
        rationale.to_evidence()
        for atom in atom_verifications
        for rationale in atom.rationales
    )
    trace = ClaimVerificationTrace(
        claim=claim.text,
        citations=claim.citation_keys,
        source_gate_status="passed",
        atom_verifications=tuple(atom_verifications),
        final_label=atom_judgment.label,
        final_confidence=round(atom_judgment.confidence, 3),
        final_failure_mode=atom_judgment.failure_mode,
        review_action=_review_action(atom_judgment.failure_mode),
    )
    return VerificationResult(
        claim=claim.text,
        label=atom_judgment.label,
        confidence=round(atom_judgment.confidence, 3),
        citations=claim.citation_keys,
        evidence=evidence,
        reason=atom_judgment.reason,
        failure_mode=atom_judgment.failure_mode,
        trace=trace,
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


def _verify_atoms(claim: Claim, chunks: list[SourceChunk], judge: Judge) -> list[AtomVerification]:
    verifications: list[AtomVerification] = []
    group = atomize_claim(claim)
    for atom in group.atoms:
        atom_claim = Claim(atom.text, atom.citation_keys)
        candidates = select_rationales(
            atom_claim,
            chunks,
            limit=RATIONALE_CANDIDATE_LIMIT,
            min_score=RATIONALE_MIN_SCORE,
        )
        if not candidates:
            verifications.append(
                AtomVerification(
                    text=atom.text,
                    context=atom.context,
                    label=Label.UNSUPPORTED,
                    confidence=0.3,
                    rationales=(),
                    failure_mode=FailureMode.NO_RATIONALE_SPAN,
                    reason="No rationale span was selected for this atom.",
                )
            )
            continue
        judged_candidates = tuple(
            (candidate, adjudicate_evidence(atom.text, candidate.text, judge=judge))
            for candidate in candidates
        )
        judgment = _choose_candidate_judgment(judged_candidates)[1]
        rationales = tuple(
            RationaleSpan(
                source_id=candidate.source_id,
                citation_key=candidate.citation_key,
                text=candidate.text,
                page=candidate.page,
                relation=_relation_for(candidate_judgment.label),
                score=candidate.lexical_score,
                rank=rank,
            )
            for rank, (candidate, candidate_judgment) in enumerate(judged_candidates, start=1)
        )
        verifications.append(
            AtomVerification(
                text=atom.text,
                context=atom.context,
                label=judgment.label,
                confidence=round(judgment.confidence, 3),
                rationales=rationales,
                failure_mode=judgment.failure_mode,
                reason=judgment.reason,
                candidate_count=len(judged_candidates),
                support_candidate_count=_count_relation(judged_candidates, "support"),
                contradiction_candidate_count=_count_relation(judged_candidates, "contradict"),
                best_support_rank=_best_rank_for(judged_candidates, "support"),
                best_contradiction_rank=_best_rank_for(judged_candidates, "contradict"),
            )
        )
    return verifications


def _choose_candidate_judgment(
    judgments: tuple[tuple[EvidenceCandidate, EvidenceJudgment], ...],
) -> tuple[EvidenceCandidate, EvidenceJudgment]:
    priority = {
        Label.CONTRADICTED: 4,
        Label.SUPPORTED: 3,
        Label.PARTIALLY_SUPPORTED: 2,
        Label.UNCERTAIN: 1,
        Label.UNSUPPORTED: 0,
    }
    return max(judgments, key=lambda item: (priority[item[1].label], item[1].confidence))


def _count_relation(
    candidates: tuple[tuple[EvidenceCandidate, EvidenceJudgment], ...],
    relation: str,
) -> int:
    return sum(1 for _candidate, judgment in candidates if _relation_for(judgment.label) == relation)


def _best_rank_for(
    candidates: tuple[tuple[EvidenceCandidate, EvidenceJudgment], ...],
    relation: str,
) -> int | None:
    ranks = (
        candidate.rank
        for candidate, judgment in candidates
        if _relation_for(judgment.label) == relation
    )
    return min(ranks, default=None)


def _relation_for(label: Label) -> str:
    if label == Label.SUPPORTED:
        return "support"
    if label == Label.CONTRADICTED:
        return "contradict"
    if label == Label.UNSUPPORTED:
        return "neutral"
    return "undetermined"


def _review_action(mode: FailureMode | None) -> str:
    if mode is None:
        return "none"
    actions = {
        FailureMode.SOURCE_NOT_RESOLVED: "load cited source or fix citation key",
        FailureMode.WEAK_RETRIEVAL: "find stronger evidence or remove citation",
        FailureMode.NO_RATIONALE_SPAN: "find exact supporting span or narrow the claim",
        FailureMode.MISSING_ATOM_SUPPORT: "rewrite unsupported atom or add a better citation",
        FailureMode.NUMERIC_CONFLICT: "fix the numeric value or cite a matching source",
        FailureMode.YEAR_CONFLICT: "fix the year or cite a matching source",
        FailureMode.UNIT_CONFLICT: "fix the unit or cite a matching source",
        FailureMode.ENTITY_CONFLICT: "fix the entity or cite a matching source",
        FailureMode.NEGATION_CONFLICT: "fix the result polarity or cite a matching source",
        FailureMode.COMPARISON_DIRECTION_CONFLICT: (
            "fix the comparison direction or cite a matching source"
        ),
        FailureMode.HEDGED_EVIDENCE: "hedge the claim or cite stronger evidence",
        FailureMode.SCOPE_OVERSTATEMENT: "narrow the claim scope",
        FailureMode.SOURCE_SILENCE: "cite a source that states the claim or revise the claim",
        FailureMode.MODEL_DISAGREEMENT: "manually inspect model disagreement",
    }
    return actions.get(mode, "manually inspect cited evidence")
