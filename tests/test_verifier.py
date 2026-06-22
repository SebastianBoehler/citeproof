from pathlib import Path

from citeproof.models import Label
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
