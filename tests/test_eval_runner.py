from pathlib import Path

from citeproof.evals.runner import run_eval_file


def test_eval_runner_reports_false_supported_rate(tmp_path: Path) -> None:
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        '{"claim":"A improves B.","evidence":"A improves B.","expected_label":"supported"}\n'
        '{"claim":"A improves B.","evidence":"A does not improve B.","expected_label":"contradicted"}\n',
        encoding="utf-8",
    )

    summary = run_eval_file(dataset)

    assert summary.total == 2
    assert summary.false_supported_rate == 0.0
