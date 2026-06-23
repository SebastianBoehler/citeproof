import json
from pathlib import Path

from citeproof.cli import main
from citeproof.evals.suite import run_eval_suite


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_layer_gates_do_not_gate_ungated_heldout_layer(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "regression.jsonl",
        [
            {
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "supported",
            }
        ],
    )
    _write_jsonl(
        tmp_path / "heldout.jsonl",
        [
            {
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "unsupported",
            }
        ],
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": "regression",
                        "path": "regression.jsonl",
                        "layer": "regression",
                    },
                    {
                        "name": "heldout",
                        "path": "heldout.jsonl",
                        "layer": "heldout_real",
                        "locked": True,
                    },
                ],
                "layer_gates": {
                    "regression": {
                        "max_false_supported_rate": 0.0,
                        "min_accuracy": 1.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    report = run_eval_suite(manifest)

    assert report["passed"] is True
    assert report["layers"]["heldout_real"]["summary"]["accuracy"] == 0.0
    assert report["layer_gates"]["regression"][0]["pass"] is True
    assert "heldout_real" not in report["layer_gates"]


def test_eval_suite_cli_returns_two_for_failing_layer_gate(tmp_path: Path, capsys) -> None:
    _write_jsonl(
        tmp_path / "regression.jsonl",
        [
            {
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "unsupported",
            }
        ],
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": "regression",
                        "path": "regression.jsonl",
                        "layer": "regression",
                    }
                ],
                "layer_gates": {"regression": {"max_false_supported_rate": 0.0}},
            }
        ),
        encoding="utf-8",
    )

    code = main(["eval-suite", str(manifest)])

    captured = capsys.readouterr()
    assert code == 2
    assert '"passed": false' in captured.out
