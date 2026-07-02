import json
from pathlib import Path

from citeproof.cli import main
from citeproof.evals.external import convert_external_benchmark


def test_convert_scifact_jsonl_export(tmp_path: Path) -> None:
    source = tmp_path / "scifact.jsonl"
    output = tmp_path / "claim_support.jsonl"
    source.write_text(
        json.dumps(
            {
                "claim_id": 17,
                "claim": "Drug A reduces mortality.",
                "evidence": "Drug A did not reduce mortality in the trial.",
                "evidence_label": "CONTRADICT",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = convert_external_benchmark(source, output, source_format="scifact")

    assert rows[0]["id"] == "17"
    assert rows[0]["expected_label"] == "contradicted"
    assert rows[0]["external_format"] == "scifact"
    assert output.read_text(encoding="utf-8").endswith("\n")


def test_convert_scitance_json_list_export(tmp_path: Path) -> None:
    source = tmp_path / "scitance.json"
    output = tmp_path / "claim_support.jsonl"
    source.write_text(
        json.dumps(
            [
                {
                    "uid": "s1",
                    "citation_text": "The model improves accuracy.",
                    "sentences": ["The model improves accuracy over the baseline."],
                    "label": "entailment",
                }
            ]
        ),
        encoding="utf-8",
    )

    rows = convert_external_benchmark(source, output, source_format="scitance")

    assert rows == [
        {
            "id": "s1",
            "claim": "The model improves accuracy.",
            "evidence": "The model improves accuracy over the baseline.",
            "expected_label": "supported",
            "external_format": "scitance",
        }
    ]


def test_convert_factscore_cli(tmp_path: Path) -> None:
    source = tmp_path / "factscore.json"
    output = tmp_path / "claim_support.jsonl"
    source.write_text(
        json.dumps(
            {
                "annotations": [
                    {
                        "atom_id": "a1",
                        "atom": "The system uses retrieval.",
                        "passage": "The system answers without retrieval.",
                        "is_supported": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    code = main(
        [
            "convert-external-benchmark",
            str(source),
            "--format",
            "factscore",
            "--output",
            str(output),
        ]
    )

    assert code == 0
    assert '"external_format": "factscore"' in output.read_text(encoding="utf-8")
