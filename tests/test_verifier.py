from pathlib import Path

from citeproof.models import FailureMode, Label
from citeproof.report import results_to_markdown
from citeproof.verifier import verify_claim_text, verify_draft


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
