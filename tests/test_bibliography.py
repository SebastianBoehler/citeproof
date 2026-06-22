from pathlib import Path

from citeproof.bibliography import parse_bibtex, verify_bibliography


def test_parse_bibtex_handles_nested_braces() -> None:
    entries = parse_bibtex(
        "@article{smith2024,\n"
        "  author = {Smith, Jane},\n"
        "  title = {{QLoRA}: Efficient Tuning},\n"
        "  journal = {Journal},\n"
        "  year = {2024}\n"
        "}\n"
    )

    assert entries["smith2024"].fields["title"] == "{QLoRA}: Efficient Tuning"


def test_verify_bibliography_reports_missing_and_unused(tmp_path: Path) -> None:
    tex = tmp_path / "paper.tex"
    bib = tmp_path / "refs.bib"
    tex.write_text("A cited claim \\cite{smith2024,missing2025}.", encoding="utf-8")
    bib.write_text(
        "@article{smith2024,\n"
        "  author = {Smith, Jane},\n"
        "  title = {Paper},\n"
        "  journal = {Journal},\n"
        "  year = {2024}\n"
        "}\n"
        "@misc{unused2024,\n"
        "  title = {Unused},\n"
        "  year = {2024}\n"
        "}\n",
        encoding="utf-8",
    )

    report = verify_bibliography(tex, bib)

    assert report.citation_count == 2
    assert report.missing_bib_entries == ["missing2025"]
    assert report.unused_bib_entries == ["unused2024"]
    assert report.error_count == 1
