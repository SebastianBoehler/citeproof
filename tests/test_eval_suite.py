import json
from pathlib import Path

import pytest

from citeproof.cli import main
from citeproof.evals.suite import run_eval_suite


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_eval_suite_resolves_manifest_relative_paths(tmp_path: Path) -> None:
    suite_dir = tmp_path / "suite"
    suite_dir.mkdir()
    _write_jsonl(
        suite_dir / "cases.jsonl",
        [
            {
                "id": "supported",
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "supported",
            },
            {
                "id": "contradicted",
                "claim": "A improves B.",
                "evidence": "A does not improve B.",
                "expected_label": "contradicted",
            },
        ],
    )
    manifest = suite_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [{"name": "tiny", "path": "cases.jsonl", "split": "heldout"}],
                "gates": {"max_false_supported_rate": 0.0, "min_accuracy": 1.0},
            }
        ),
        encoding="utf-8",
    )

    report = run_eval_suite(manifest)

    assert report["aggregate"]["total"] == 2
    assert report["datasets"][0]["name"] == "tiny"
    assert report["datasets"][0]["split"] == "heldout"
    assert report["datasets"][0]["summary"]["false_supported_rate"] == 0.0
    assert all(gate["pass"] for gate in report["gates"])


def test_eval_suite_reports_benchmark_layer_metadata(tmp_path: Path) -> None:
    suite_dir = tmp_path / "suite"
    suite_dir.mkdir()
    _write_jsonl(
        suite_dir / "cases.jsonl",
        [
            {
                "id": "supported",
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "supported",
            }
        ],
    )
    manifest = suite_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": "real-regression",
                        "path": "cases.jsonl",
                        "split": "real_paper_regression",
                        "layer": "regression",
                        "source_type": "real_paper",
                        "locked": False,
                    }
                ],
                "benchmark_layers": {
                    "regression": {
                        "purpose": "Known cases for CI regression checks.",
                        "claimable": False,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    report = run_eval_suite(manifest)

    dataset = report["datasets"][0]
    assert dataset["layer"] == "regression"
    assert dataset["source_type"] == "real_paper"
    assert dataset["locked"] is False
    assert report["layers"]["regression"]["summary"]["total"] == 1
    assert report["layer_policy"]["regression"]["claimable"] is False


def test_eval_suite_reports_failing_gate(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    _write_jsonl(
        dataset,
        [
            {
                "id": "false-supported",
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
                "datasets": [{"name": "bad", "path": "cases.jsonl"}],
                "gates": {"max_false_supported_rate": 0.0},
            }
        ),
        encoding="utf-8",
    )

    report = run_eval_suite(manifest)

    assert report["aggregate"]["false_supported_rate"] == 1.0
    assert report["gates"] == [
        {
            "name": "max_false_supported_rate",
            "actual": 1.0,
            "threshold": 0.0,
            "pass": False,
        }
    ]
    assert report["datasets"][0]["failures"][0]["id"] == "false-supported"


def test_eval_suite_rejects_unknown_gate(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    _write_jsonl(
        dataset,
        [
            {
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "supported",
            }
        ],
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [{"name": "tiny", "path": "cases.jsonl"}],
                "gates": {"unknown_gate": 0.0},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported eval-suite gate"):
        run_eval_suite(manifest)


def test_eval_suite_cli_returns_zero_for_passing_gates(tmp_path: Path, capsys) -> None:
    dataset = tmp_path / "cases.jsonl"
    _write_jsonl(
        dataset,
        [{"claim": "A improves B.", "evidence": "A improves B.", "expected_label": "supported"}],
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [{"name": "tiny", "path": "cases.jsonl"}],
                "gates": {"max_false_supported_rate": 0.0},
            }
        ),
        encoding="utf-8",
    )

    code = main(["eval-suite", str(manifest)])

    captured = capsys.readouterr()
    assert code == 0
    assert '"passed": true' in captured.out


def test_eval_suite_cli_returns_two_for_failing_gates(tmp_path: Path, capsys) -> None:
    dataset = tmp_path / "cases.jsonl"
    _write_jsonl(
        dataset,
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
                "datasets": [{"name": "bad", "path": "cases.jsonl"}],
                "gates": {"max_false_supported_rate": 0.0},
            }
        ),
        encoding="utf-8",
    )

    code = main(["eval-suite", str(manifest)])

    captured = capsys.readouterr()
    assert code == 2
    assert '"passed": false' in captured.out
