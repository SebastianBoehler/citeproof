import json
from pathlib import Path

from citeproof.bibliography import BibEntry
from citeproof.evals.hallmark import predict_hallmark_jsonl
from citeproof.metadata import MetadataRecord


class FakeProvider:
    name = "fake"

    def search(self, entry: BibEntry) -> list[MetadataRecord]:
        if entry.key == "real2024":
            return [MetadataRecord("fake", entry.fields["title"], entry.fields["year"])]
        return []


def test_hallmark_adapter_outputs_expected_schema(tmp_path: Path) -> None:
    dataset = tmp_path / "hallmark.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "bibtex_key": "real2024",
                        "bibtex_type": "article",
                        "fields": {"title": "Real Paper", "year": "2024"},
                    }
                ),
                json.dumps(
                    {
                        "bibtex_key": "fake2025",
                        "bibtex_type": "article",
                        "fields": {"title": "Fake Paper", "year": "2025"},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    predictions = predict_hallmark_jsonl(dataset, providers=[FakeProvider()])

    assert predictions[0]["label"] == "VALID"
    assert predictions[1]["label"] == "HALLUCINATED"
    assert {"bibtex_key", "label", "confidence", "reason"} <= predictions[0].keys()
