"""HALLMARK bibliography-hallucination adapter."""

from __future__ import annotations

import json
from pathlib import Path

from citeproof.bibliography import BibEntry
from citeproof.metadata import MetadataProvider, verify_entry_metadata


def predict_hallmark_jsonl(
    input_path: str | Path,
    providers: list[MetadataProvider] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Predict HALLMARK labels from external metadata verification."""

    rows = _load_jsonl(input_path)
    predictions = []
    for row in rows[:limit]:
        entry = _entry_from_hallmark(row)
        check = verify_entry_metadata(entry, providers=providers)
        predictions.append(
            {
                "bibtex_key": entry.key,
                "label": _hallmark_label(check.status),
                "confidence": _hallmark_confidence(check.status, check.confidence),
                "reason": check.reason,
                "source": check.provider,
                "api_calls": check.api_calls,
            }
        )
    return predictions


def predictions_to_jsonl(predictions: list[dict]) -> str:
    """Serialize HALLMARK predictions."""

    return "\n".join(json.dumps(row, sort_keys=True) for row in predictions) + "\n"


def _entry_from_hallmark(row: dict) -> BibEntry:
    fields = {str(key).lower(): str(value) for key, value in row.get("fields", {}).items()}
    return BibEntry(
        key=str(row["bibtex_key"]),
        entry_type=str(row.get("bibtex_type") or "misc").removeprefix("@").lower(),
        fields=fields,
    )


def _hallmark_label(status: str) -> str:
    if status == "verified":
        return "VALID"
    if status in {"mismatch", "not_found"}:
        return "HALLUCINATED"
    return "UNCERTAIN"


def _hallmark_confidence(status: str, confidence: float) -> float:
    if status == "verified":
        return confidence
    if status == "mismatch":
        return max(confidence, 0.65)
    if status == "not_found":
        return 0.65
    return 0.5


def _load_jsonl(path: str | Path) -> list[dict]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
