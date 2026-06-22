from pathlib import Path

from citeproof.models import Label
from citeproof.verifier import verify_draft


def test_verify_draft_localizes_supported_citation_clauses(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "lora2021.txt").write_text("LoRA improves accuracy on GLUE.", encoding="utf-8")
    (sources / "prefix2021.txt").write_text(
        "Prefix Tuning improves accuracy on SQuAD.", encoding="utf-8"
    )
    draft = tmp_path / "draft.md"
    draft.write_text(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, "
        "while Prefix Tuning improves accuracy on SQuAD \\cite{prefix2021}.",
        encoding="utf-8",
    )

    results = verify_draft(draft, sources)

    assert [result.label for result in results] == [Label.SUPPORTED, Label.SUPPORTED]
    assert [result.citations for result in results] == [("lora2021",), ("prefix2021",)]


def test_verify_draft_localizes_wrong_second_clause(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "lora2021.txt").write_text("LoRA improves accuracy on GLUE.", encoding="utf-8")
    (sources / "prefix2021.txt").write_text(
        "Prefix Tuning improves accuracy on SQuAD.", encoding="utf-8"
    )
    draft = tmp_path / "draft.md"
    draft.write_text(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, "
        "while Prefix Tuning improves accuracy on GLUE \\cite{prefix2021}.",
        encoding="utf-8",
    )

    results = verify_draft(draft, sources)

    assert results[0].label == Label.SUPPORTED
    assert results[1].label == Label.CONTRADICTED
    assert results[1].citations == ("prefix2021",)
