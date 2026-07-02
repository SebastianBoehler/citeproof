"""Adapters for external claim-evidence benchmark exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citeproof.models import Label

SUPPORTED_FORMATS = ("scifact", "scitance", "factscore")

_SUPPORT = {"support", "supports", "supported", "true", "yes", "entails", "entailment"}
_CONTRADICT = {
    "contradict",
    "contradicts",
    "contradicted",
    "refute",
    "refutes",
    "refuted",
    "false",
    "no",
    "contradiction",
}
_PARTIAL = {"partial", "partially_supported", "partially supported", "mixed"}
_UNSUPPORTED = {"nei", "not_enough_info", "not enough info", "unsupported", "unknown", "neutral"}


def convert_external_benchmark(
    input_path: str | Path,
    output_path: str | Path,
    *,
    source_format: str,
) -> list[dict[str, str]]:
    """Convert supported external benchmark records to CiteProof JSONL rows."""

    rows = [_convert_record(record, source_format) for record in _read_records(input_path)]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return rows


def _convert_record(record: dict[str, Any], source_format: str) -> dict[str, str]:
    if source_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported external benchmark format: {source_format}")
    if source_format == "factscore":
        return _factscore_row(record)
    return _claim_evidence_row(record, source_format)


def _claim_evidence_row(record: dict[str, Any], source_format: str) -> dict[str, str]:
    claim = _first_text(record, "claim", "citation", "citation_text", "statement", "text")
    evidence = _evidence_text(record)
    label = _label(record)
    return {
        "id": str(record.get("id") or record.get("claim_id") or record.get("uid") or f"{source_format}-case"),
        "claim": claim,
        "evidence": evidence,
        "expected_label": label.value,
        "external_format": source_format,
    }


def _factscore_row(record: dict[str, Any]) -> dict[str, str]:
    claim = _first_text(record, "atom", "claim", "statement")
    evidence = _evidence_text(record)
    label = _label(record)
    return {
        "id": str(record.get("id") or record.get("atom_id") or "factscore-case"),
        "claim": claim,
        "evidence": evidence,
        "expected_label": label.value,
        "external_format": "factscore",
    }


def _read_records(path: str | Path) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8")
    if path_str := str(path):
        if path_str.endswith(".jsonl"):
            return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, list):
        return [_ensure_record(item) for item in data]
    if isinstance(data, dict):
        for key in ("data", "claims", "annotations", "examples"):
            if isinstance(data.get(key), list):
                return [_ensure_record(item) for item in data[key]]
    raise ValueError("External benchmark input must be JSONL, a JSON list, or an object with data records.")


def _ensure_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("External benchmark records must be objects.")
    return value


def _first_text(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError(f"External benchmark record has no text field among: {', '.join(keys)}")


def _evidence_text(record: dict[str, Any]) -> str:
    for key in ("evidence", "abstract", "sentence", "passage", "source", "snippet"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("evidence_sentences", "sentences", "passages"):
        value = record.get(key)
        if isinstance(value, list):
            pieces = [str(item).strip() for item in value if str(item).strip()]
            if pieces:
                return " ".join(pieces)
    raise ValueError("External benchmark record has no evidence text.")


def _label(record: dict[str, Any]) -> Label:
    if isinstance(record.get("is_supported"), bool):
        return Label.SUPPORTED if record["is_supported"] else Label.UNSUPPORTED
    raw = str(
        record.get("expected_label")
        or record.get("label")
        or record.get("evidence_label")
        or record.get("verdict")
        or ""
    )
    key = raw.strip().casefold().replace("-", "_")
    if key in _SUPPORT:
        return Label.SUPPORTED
    if key in _CONTRADICT:
        return Label.CONTRADICTED
    if key in _PARTIAL:
        return Label.PARTIALLY_SUPPORTED
    if key in _UNSUPPORTED:
        return Label.UNSUPPORTED
    raise ValueError(f"Unsupported external benchmark label: {raw}")
