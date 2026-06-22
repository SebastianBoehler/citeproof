from pathlib import Path

from citeproof.models import Claim, FailureMode, Label, SourceChunk
from citeproof.report import results_to_markdown
from citeproof.verifier import verify_claim, verify_claim_text, verify_draft


def test_verify_claim_detects_contradiction(tmp_path: Path) -> None:
    (tmp_path / "smith2024.txt").write_text(
        "Method X performed comparably to PPO, with no statistically significant improvement.",
        encoding="utf-8",
    )

    result = verify_claim_text(
        "Method X outperforms PPO on sparse-reward robotics tasks.",
        tmp_path,
        ["smith2024"],
    )

    assert result.label == Label.CONTRADICTED
    assert result.evidence
    assert result.failure_mode is not None
    assert result.trace is not None
    assert result.trace.review_action != "none"
    assert result.trace.final_failure_mode is not None


def test_verify_claim_does_not_allow_support_to_hide_contradiction() -> None:
    chunks = [
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="support",
            text="Method X improves accuracy.",
        ),
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="contradiction",
            text="Method X does not improve accuracy.",
        ),
    ]

    result = verify_claim(
        Claim("Method X improves accuracy.", ("smith2024",)),
        chunks,
        evidence_limit=2,
    )

    assert result.label == Label.CONTRADICTED
    assert result.failure_mode == FailureMode.NEGATION_CONFLICT
    assert result.trace is not None
    assert result.trace.review_action == "fix the result polarity or cite a matching source"
    rationales = result.trace.atom_verifications[0].rationales
    assert any(rationale.relation == "contradict" for rationale in rationales)
    assert any("does not improve accuracy" in rationale.text for rationale in rationales)


def test_verify_claim_flags_material_anchor_conflict() -> None:
    chunks = [
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="swap",
            text="Prefix Tuning improves accuracy over full fine-tuning on GLUE.",
        )
    ]

    result = verify_claim(
        Claim("LoRA improves accuracy over full fine-tuning on GLUE.", ("smith2024",)),
        chunks,
    )

    assert result.label == Label.CONTRADICTED
    assert result.failure_mode == FailureMode.ENTITY_CONFLICT
    assert result.trace is not None
    assert result.trace.review_action == "fix the entity or cite a matching source"


def test_verify_claim_flags_comparison_direction_conflict() -> None:
    chunks = [
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="reverse",
            text="Prefix Tuning outperforms LoRA on GLUE.",
        )
    ]

    result = verify_claim(
        Claim("LoRA outperforms Prefix Tuning on GLUE.", ("smith2024",)),
        chunks,
    )

    assert result.label == Label.CONTRADICTED
    assert result.failure_mode == FailureMode.COMPARISON_DIRECTION_CONFLICT
    assert result.trace is not None
    assert result.trace.review_action == "fix the comparison direction or cite a matching source"


def test_verify_claim_records_candidate_diagnostics() -> None:
    chunks = [
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="support",
            text="Method X improves accuracy.",
        ),
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="contradiction",
            text="Method X does not improve accuracy.",
        ),
    ]

    result = verify_claim(
        Claim("Method X improves accuracy.", ("smith2024",)),
        chunks,
        evidence_limit=2,
    )

    atom = result.trace.atom_verifications[0]
    assert atom.candidate_count == 2
    assert atom.support_candidate_count == 1
    assert atom.contradiction_candidate_count == 1
    assert atom.best_support_rank == 1
    assert atom.best_contradiction_rank == 2
    assert tuple(rationale.rank for rationale in atom.rationales) == (1, 2)


def test_lower_ranked_contradiction_blocks_supported() -> None:
    chunks = [
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="support-1",
            text="Method X improves accuracy over baseline.",
        ),
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="support-2",
            text="Method X improves accuracy over baseline in table 1.",
        ),
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="support-3",
            text="Method X improves accuracy over baseline across validation data.",
        ),
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="support-4",
            text="Method X improves accuracy over baseline for robotics tasks.",
        ),
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="contradiction",
            text="Method X does not improve accuracy over the baseline.",
        ),
    ]

    result = verify_claim(
        Claim("Method X improves accuracy over baseline.", ("smith2024",)),
        chunks,
        evidence_limit=1,
    )

    atom = result.trace.atom_verifications[0]
    assert result.label == Label.CONTRADICTED
    assert atom.best_support_rank == 1
    assert atom.best_contradiction_rank == 2
    assert atom.contradiction_candidate_count == 1


def test_verify_draft_marks_missing_source_uncertain(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "smith2024.txt").write_text(
        "Method X performed comparably to PPO.",
        encoding="utf-8",
    )
    draft = tmp_path / "draft.md"
    draft.write_text("Claim text \\cite{missing2026}.", encoding="utf-8")

    results = verify_draft(draft, source_dir)

    assert results[0].label == Label.UNCERTAIN


def test_verify_claim_includes_trace_for_supported_result(tmp_path: Path) -> None:
    (tmp_path / "smith2024.txt").write_text(
        "Training with Method X required half as many hours as the baseline.",
        encoding="utf-8",
    )

    result = verify_claim_text(
        "Method X reduces training time.",
        tmp_path,
        ["smith2024"],
    )
    data = result.to_dict()

    assert result.label == Label.SUPPORTED
    assert data["failure_mode"] is None
    assert data["trace"]["source_gate_status"] == "passed"
    assert data["trace"]["atom_verifications"][0]["rationales"]
    assert len(data["trace"]["atom_verifications"][0]["rationales"]) == 1
    assert data["trace"]["atom_verifications"][0]["label"] == "supported"


def test_verify_claim_reports_failure_mode_for_missing_source(tmp_path: Path) -> None:
    (tmp_path / "smith2024.txt").write_text("Method X improves accuracy.", encoding="utf-8")

    result = verify_claim_text(
        "Method X improves accuracy.",
        tmp_path,
        ["missing2026"],
    )

    assert result.label == Label.UNCERTAIN
    assert result.failure_mode.value == "source_not_resolved"
    assert result.trace.final_failure_mode.value == "source_not_resolved"


def test_verify_claim_reports_weak_retrieval_when_source_has_no_overlap(tmp_path: Path) -> None:
    (tmp_path / "smith2024.txt").write_text("Bananas ripen in baskets.", encoding="utf-8")

    result = verify_claim_text(
        "Quantum flux regulates enzymes.",
        tmp_path,
        ["smith2024"],
    )

    assert result.label == Label.UNSUPPORTED
    assert result.failure_mode == FailureMode.WEAK_RETRIEVAL
    assert result.trace is not None
    assert result.trace.final_failure_mode == FailureMode.WEAK_RETRIEVAL
    assert result.trace.review_action == "find stronger evidence or remove citation"


def test_partial_trace_preserves_atom_failure_mode(tmp_path: Path) -> None:
    (tmp_path / "smith2024.txt").write_text(
        "Method X improves some robotics tasks.",
        encoding="utf-8",
    )

    result = verify_claim_text(
        "Method X improves all robotics tasks.",
        tmp_path,
        ["smith2024"],
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert result.failure_mode == FailureMode.SCOPE_OVERSTATEMENT
    assert result.trace is not None
    assert result.trace.final_failure_mode == FailureMode.SCOPE_OVERSTATEMENT
    assert result.trace.review_action == "narrow the claim scope"


def test_markdown_report_includes_failure_mode_and_atoms_for_traced_result(
    tmp_path: Path,
) -> None:
    (tmp_path / "smith2024.txt").write_text(
        "Training with Method X required half as many hours as the baseline.",
        encoding="utf-8",
    )
    result = verify_claim_text(
        "Method X reduces training time.",
        tmp_path,
        ["smith2024"],
    )

    report = results_to_markdown([result])

    assert "**Failure mode:** none" in report
    assert "**Atoms:**" in report
    assert "- `supported` Method X reduces training time." in report
