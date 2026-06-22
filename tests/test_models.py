from dataclasses import asdict

from citeproof.models import (
    AtomVerification,
    ClaimVerificationTrace,
    EvidenceSpan,
    EvidenceCandidate,
    FailureMode,
    Label,
    RationaleSpan,
    VerificationResult,
)


def test_atom_trace_serializes_candidate_diagnostics() -> None:
    rationale = RationaleSpan(
        source_id="paper",
        citation_key="smith2024",
        text="Method X improves sample efficiency.",
        page=3,
        relation="support",
        score=0.91,
        rank=2,
    )
    atom = AtomVerification(
        text="Method X improves sample efficiency.",
        context="Method X improves sample efficiency.",
        label=Label.SUPPORTED,
        confidence=0.91,
        rationales=(rationale,),
        reason="Rationale supports the atom.",
        candidate_count=5,
        support_candidate_count=3,
        contradiction_candidate_count=1,
        best_support_rank=2,
        best_contradiction_rank=4,
    )
    default_atom = AtomVerification(
        text="Method X is sample efficient.",
        context="Method X improves sample efficiency.",
        label=Label.UNSUPPORTED,
        confidence=0.2,
        reason="No supporting rationale.",
    )
    trace = ClaimVerificationTrace(
        claim="Method X improves sample efficiency.",
        citations=("smith2024",),
        source_gate_status="passed",
        atom_verifications=(atom, default_atom),
        final_label=Label.SUPPORTED,
        final_confidence=0.91,
        final_failure_mode=None,
        review_action="none",
    )
    result = VerificationResult(
        claim="Method X improves sample efficiency.",
        label=Label.SUPPORTED,
        confidence=0.91,
        citations=("smith2024",),
        evidence=(),
        reason="All atomic subclaims are supported.",
        trace=trace,
    )

    data = result.to_dict()

    atom_data = data["trace"]["atom_verifications"][0]
    assert atom_data["candidate_count"] == 5
    assert atom_data["support_candidate_count"] == 3
    assert atom_data["contradiction_candidate_count"] == 1
    assert atom_data["best_support_rank"] == 2
    assert atom_data["best_contradiction_rank"] == 4
    assert atom_data["rationales"][0]["rank"] == 2

    default_atom_data = data["trace"]["atom_verifications"][1]
    assert default_atom_data["candidate_count"] == 0
    assert default_atom_data["support_candidate_count"] == 0
    assert default_atom_data["contradiction_candidate_count"] == 0
    assert default_atom_data["best_support_rank"] is None
    assert default_atom_data["best_contradiction_rank"] is None

    asdict_atom = asdict(atom)
    assert asdict_atom["candidate_count"] == 5
    assert asdict_atom["rationales"][0]["rank"] == 2


def test_verification_result_serializes_trace_and_failure_mode() -> None:
    rationale = RationaleSpan(
        source_id="paper",
        citation_key="smith2024",
        text="Method X improves sample efficiency.",
        page=3,
        relation="support",
        score=0.91,
    )
    atom = AtomVerification(
        text="Method X improves sample efficiency.",
        context="Method X improves sample efficiency.",
        label=Label.SUPPORTED,
        confidence=0.91,
        rationales=(rationale,),
        failure_mode=FailureMode.WEAK_RETRIEVAL,
        reason="Rationale supports the atom.",
    )
    trace = ClaimVerificationTrace(
        claim="Method X improves sample efficiency.",
        citations=("smith2024",),
        source_gate_status="passed",
        atom_verifications=(atom,),
        final_label=Label.SUPPORTED,
        final_confidence=0.91,
        final_failure_mode=FailureMode.WEAK_RETRIEVAL,
        review_action="none",
    )
    result = VerificationResult(
        claim="Method X improves sample efficiency.",
        label=Label.SUPPORTED,
        confidence=0.91,
        citations=("smith2024",),
        evidence=(),
        reason="All atomic subclaims are supported.",
        failure_mode=FailureMode.WEAK_RETRIEVAL,
        trace=trace,
    )

    data = result.to_dict()

    assert data["label"] == "supported"
    assert data["failure_mode"] == "weak_retrieval"
    assert data["trace"]["final_label"] == "supported"
    assert data["trace"]["final_failure_mode"] == "weak_retrieval"
    assert data["trace"]["atom_verifications"][0]["failure_mode"] == "weak_retrieval"
    assert data["trace"]["atom_verifications"][0]["rationales"][0]["relation"] == "support"


def test_verification_result_to_dict_preserves_existing_tuple_shape() -> None:
    evidence = EvidenceSpan(
        source_id="paper",
        citation_key="smith2024",
        text="Method X improves sample efficiency.",
        page=3,
        score=0.91,
    )
    result = VerificationResult(
        claim="Method X improves sample efficiency.",
        label=Label.SUPPORTED,
        confidence=0.91,
        citations=("smith2024",),
        evidence=(evidence,),
        reason="Evidence supports the claim.",
    )

    data = result.to_dict()

    assert data["citations"] == ("smith2024",)
    assert data["evidence"] == (
        {
            "source_id": "paper",
            "text": "Method X improves sample efficiency.",
            "citation_key": "smith2024",
            "page": 3,
            "score": 0.91,
            "title": None,
        },
    )


def test_evidence_candidate_serializes_scores() -> None:
    candidate = EvidenceCandidate(
        source_id="paper",
        citation_key="smith2024",
        text="The adapter used 4 GPUs.",
        chunk_id="paper:p1:0",
        page=1,
        lexical_score=0.7,
        semantic_score=None,
        rerank_score=None,
        rank=1,
        retrieval_method="sentence_window",
    )

    assert candidate.to_dict()["lexical_score"] == 0.7
    assert candidate.to_dict()["retrieval_method"] == "sentence_window"
