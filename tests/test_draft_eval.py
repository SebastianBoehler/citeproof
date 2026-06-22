from pathlib import Path

from citeproof.evals.draft import run_draft_eval
from citeproof.models import EvidenceJudgment, Label


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


def test_draft_eval_reports_trace_diagnostics(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "methodx.md").write_text(
        "Method X performed comparably to PPO, with no statistically significant improvement.",
        encoding="utf-8",
    )
    draft = tmp_path / "draft.md"
    draft.write_text("Method X outperforms PPO [@methodx].", encoding="utf-8")
    expected = tmp_path / "expected.jsonl"
    expected.write_text(
        '{"id":"contradicted","claim_contains":"Method X","expected_label":"contradicted",'
        '"expected_failure_mode":"negation_conflict"}\n',
        encoding="utf-8",
    )

    result = run_draft_eval(draft, sources, expected)
    case = result["cases"][0]

    assert case["pass"]
    assert case["false_supported"] is False
    assert case["failure_mode"] == "negation_conflict"
    assert case["failure_mode_pass"] is True
    assert case["source_gate_status"] == "passed"
    assert case["candidate_count"] >= 1
    assert case["contradiction_candidate_count"] >= 1
    assert case["best_contradiction_rank"] == 1


def test_draft_eval_accepts_custom_judge(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "real2024.md").write_text("A improves B.", encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text("A improves B [@real2024].", encoding="utf-8")
    expected = tmp_path / "expected.jsonl"
    expected.write_text(
        '{"id":"custom","claim_contains":"A improves B","expected_label":"contradicted"}\n',
        encoding="utf-8",
    )

    def judge(_claim: str, _evidence: str) -> EvidenceJudgment:
        return EvidenceJudgment(Label.CONTRADICTED, 0.91, "custom judge")

    result = run_draft_eval(draft, sources, expected, judge=judge)

    assert result["cases"][0]["predicted_label"] == "contradicted"
    assert result["cases"][0]["pass"]


def test_eval_draft_cli_accepts_verifier_args(tmp_path: Path, monkeypatch, capsys) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text("", encoding="utf-8")
    expected = tmp_path / "expected.jsonl"
    expected.write_text("", encoding="utf-8")

    import citeproof.cli as cli

    def fake_run_draft_eval(draft_path, source_dir, expected_path, bib_path=None, judge=None):
        assert draft_path == str(draft)
        assert source_dir == str(sources)
        assert expected_path == str(expected)
        assert bib_path is None
        assert judge is not None
        return {"summary": "{}", "cases": []}

    monkeypatch.setattr(cli, "run_draft_eval", fake_run_draft_eval)
    code = cli.main(
        [
            "eval-draft",
            str(draft),
            "--sources",
            str(sources),
            "--expected",
            str(expected),
            "--verifier",
            "heuristic",
        ]
    )

    assert code == 0
    assert "{}" in capsys.readouterr().out
