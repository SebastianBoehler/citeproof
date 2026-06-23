"""Benchmark manifest loading and layer summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citeproof.evals.metrics import summarize
from citeproof.models import Label

DEFAULT_LAYER = "regression"
DEFAULT_SOURCE_TYPE = "synthetic"


def load_benchmark_manifest(path: str | Path) -> dict[str, object]:
    """Load a benchmark manifest with normalized dataset metadata."""

    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = data.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("Benchmark manifest must contain a non-empty datasets list.")
    normalized = [_normalize_dataset(index, entry) for index, entry in enumerate(datasets, start=1)]
    gates = data.get("gates", {})
    if not isinstance(gates, dict):
        raise ValueError("Benchmark manifest gates must be an object when provided.")
    layer_gates = data.get("layer_gates", {})
    if not isinstance(layer_gates, dict):
        raise ValueError("Benchmark manifest layer_gates must be an object when provided.")
    for layer, gates_for_layer in layer_gates.items():
        if not isinstance(gates_for_layer, dict):
            raise ValueError(f"Benchmark manifest layer_gates.{layer} must be an object.")
    layers = data.get("benchmark_layers", {})
    if not isinstance(layers, dict):
        raise ValueError("Benchmark manifest benchmark_layers must be an object when provided.")
    return {
        **data,
        "datasets": normalized,
        "gates": gates,
        "layer_gates": layer_gates,
        "benchmark_layers": layers,
    }


def dataset_report_metadata(entry: dict[str, object]) -> dict[str, object]:
    """Return stable dataset metadata fields for reports."""

    return {
        "layer": str(entry["layer"]),
        "source_type": str(entry["source_type"]),
        "locked": bool(entry["locked"]),
    }


def layer_policy(manifest: dict[str, object]) -> dict[str, object]:
    """Return declared layer policy metadata."""

    return dict(manifest.get("benchmark_layers", {}))


def summarize_layers(dataset_results: list[dict[str, object]]) -> dict[str, object]:
    """Aggregate dataset metrics by benchmark layer."""

    grouped: dict[str, dict[str, Any]] = {}
    for result in dataset_results:
        layer = str(result["layer"])
        group = grouped.setdefault(layer, {"datasets": [], "expected": [], "predicted": []})
        group["datasets"].append(str(result["name"]))
        group["expected"].extend(Label(str(label)) for label in _label_values(result, "expected"))
        group["predicted"].extend(Label(str(label)) for label in _label_values(result, "predicted"))
    return {
        layer: {
            "datasets": data["datasets"],
            "summary": summarize(data["expected"], data["predicted"]).to_dict(),
        }
        for layer, data in grouped.items()
    }


def _normalize_dataset(index: int, entry: object) -> dict[str, object]:
    if not isinstance(entry, dict):
        raise ValueError(f"Dataset entry {index} must be an object.")
    if "name" not in entry or "path" not in entry:
        raise ValueError(f"Dataset entry {index} must contain name and path.")
    return {
        **entry,
        "layer": str(entry.get("layer", DEFAULT_LAYER)),
        "source_type": str(entry.get("source_type", DEFAULT_SOURCE_TYPE)),
        "locked": bool(entry.get("locked", False)),
    }


def _label_values(result: dict[str, object], key: str) -> list[object]:
    rows = result.get(key, [])
    if not isinstance(rows, list):
        return []
    return rows
