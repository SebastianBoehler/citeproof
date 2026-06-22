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
