import json
from pathlib import Path

import pytest

from citeproof.benchmark_compare import build_classifier, compare_eval_suite
from citeproof.cli import main


def test_compare_eval_suite_reports_method_metrics(tmp_path: Path) -> None:
    manifest = _write_suite(tmp_path)

    report = compare_eval_suite(manifest, ["citeproof", "heuristic", "lexical"])

    by_method = {entry["method"]: entry for entry in report["methods"]}
    assert by_method["citeproof"]["aggregate"]["accuracy"] == 1.0
    assert by_method["heuristic"]["aggregate"]["accuracy"] == 1.0
    assert by_method["lexical"]["aggregate"]["false_supported_rate"] > 0
    assert by_method["citeproof"]["layers"]["regression"]["summary"]["total"] == 2
    assert report["method_catalog"]["heuristic"]["requires"] == []
    assert report["method_catalog"]["raw-llm"]["requires"] == ["OPENAI_API_KEY"]
    assert report["ranking"][0]["method"] == "citeproof"
    assert report["layer_ranking"]["regression"][0]["method"] == "citeproof"
    assert report["layer_ranking"]["regression"][0]["accuracy"] == 1.0


def test_compare_eval_suite_redacts_locked_dataset_failures(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "heldout-secret-failure",
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "unsupported",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "suite.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": "locked-heldout",
                        "path": dataset.name,
                        "layer": "heldout_real",
                        "locked": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = compare_eval_suite(manifest, ["citeproof", "lexical"])

    for method_report in report["methods"]:
        dataset_report = method_report["datasets"][0]
        assert dataset_report["failure_count"] == 1
        assert dataset_report["failure_details_redacted"] is True
        assert dataset_report["failures"] == []
    assert "heldout-secret-failure" not in json.dumps(report)


def test_compare_benchmark_cli_writes_json(tmp_path: Path) -> None:
    manifest = _write_suite(tmp_path)
    output = tmp_path / "comparison.json"

    code = main(
        [
            "compare-benchmark",
            str(manifest),
            "--methods",
            "citeproof,lexical",
            "--json-output",
            str(output),
        ]
    )

    assert code == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert [entry["method"] for entry in data["methods"]] == ["citeproof", "lexical"]


def test_raw_llm_classifier_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_classifier("raw-llm")


def test_heuristic_classifier_is_available() -> None:
    classifier = build_classifier("heuristic")

    result = classifier("A improves B.", "A does not improve B.")

    assert result.label.value == "contradicted"


def _write_suite(tmp_path: Path) -> Path:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "numeric-conflict",
                        "claim": "Method X improves success by 42 percent.",
                        "evidence": "Method X improves success by 12 percent.",
                        "expected_label": "contradicted",
                    }
                ),
                json.dumps(
                    {
                        "id": "supported",
                        "claim": "Method X improves sample efficiency.",
                        "evidence": "Method X improves sample efficiency.",
                        "expected_label": "supported",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "suite.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": "tmp",
                        "path": dataset.name,
                        "layer": "regression",
                        "source_type": "synthetic",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return manifest
