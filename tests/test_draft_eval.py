from pathlib import Path

from citeproof.evals.draft import run_draft_eval


def test_draft_eval_scores_missing_and_fabricated_sources(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "real2024.md").write_text(
        "Adaptive replay improves sample efficiency in sparse-reward manipulation tasks.",
        encoding="utf-8",
    )
    (sources / "fabricated2025.md").write_text(
        "Fictional Citation Optimizer achieves perfect citation verification.",
        encoding="utf-8",
    )
    draft = tmp_path / "draft.md"
    draft.write_text(
        "Adaptive replay improves sample efficiency [@real2024].\n"
        "GhostNet improves all tasks [@ghost2025].\n"
        "Fictional Citation Optimizer achieves perfect citation verification [@fabricated2025].",
        encoding="utf-8",
    )
    expected = tmp_path / "expected.jsonl"
    expected.write_text(
        '{"id":"supported","claim_contains":"Adaptive replay","expected_label":"supported"}\n'
        '{"id":"missing","claim_contains":"GhostNet","expected_label":"uncertain"}\n'
        '{"id":"fabricated","claim_contains":"Fictional Citation","expected_label":"uncertain"}\n',
        encoding="utf-8",
    )
    bib = tmp_path / "refs.bib"
    bib.write_text(
        "@article{real2024,\n"
        "  author = {Jones, Ada},\n"
        "  title = {Adaptive Replay},\n"
        "  journal = {Journal},\n"
        "  year = {2024}\n"
        "}\n",
        encoding="utf-8",
    )

    result = run_draft_eval(draft, sources, expected, bib)

    assert [case["pass"] for case in result["cases"]] == [True, True, True]
