"""Benchmark dataset helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MUTATION_FIELDS = (
    "claim",
    "evidence",
    "expected_label",
    "expected_failure_mode",
)


def mutate_benchmark_file(
    seed_path: str | Path,
    output_path: str | Path,
) -> list[dict[str, Any]]:
    """Expand per-case mutation specs into an adversarial JSONL dataset."""

    rows = mutate_benchmark_rows(_read_jsonl(seed_path))
    _write_jsonl(output_path, rows)
    return rows


def mutate_benchmark_rows(seed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return mutation rows declared by supported real-paper seed cases."""

    output: list[dict[str, Any]] = []
    for row in seed_rows:
        parent_id = str(row.get("id") or f"case-{len(output) + 1}")
        for mutation in _mutation_specs(row):
            output.append(_mutation_row(row, parent_id, mutation))
    return output


def _mutation_specs(row: dict[str, Any]) -> list[dict[str, Any]]:
    mutations = row.get("mutations", [])
    if not isinstance(mutations, list):
        raise ValueError(f"Case {row.get('id', '<unknown>')} mutations must be a list.")
    return [mutation for mutation in mutations if isinstance(mutation, dict)]


def _mutation_row(
    parent: dict[str, Any],
    parent_id: str,
    mutation: dict[str, Any],
) -> dict[str, Any]:
    kind = str(mutation.get("kind") or "mutation")
    row = {
        "id": str(mutation.get("id") or f"{parent_id}::{kind}"),
        "parent_id": parent_id,
        "mutation_kind": kind,
        "claim": str(mutation.get("claim", parent["claim"])),
        "evidence": str(mutation.get("evidence", parent["evidence"])),
        "expected_label": str(mutation["expected_label"]),
    }
    for field in MUTATION_FIELDS:
        if field in mutation and field not in row:
            row[field] = mutation[field]
    return row


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    output.write_text(text, encoding="utf-8")
