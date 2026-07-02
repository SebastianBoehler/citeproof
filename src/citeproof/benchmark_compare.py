"""Compare CiteProof against benchmark baselines."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from citeproof.benchmark_manifest import (
    dataset_failures,
    dataset_report_metadata,
    layer_policy,
    load_benchmark_manifest,
    summarize_layers,
)
from citeproof.benchmark_methods import Classifier, build_classifier, method_catalog
from citeproof.evals.metrics import summarize
from citeproof.models import Label


def compare_eval_suite(
    manifest_path: str | Path,
    methods: list[str],
    *,
    nli_model: str | None = None,
    raw_llm_model: str | None = None,
    raw_llm_base_url: str | None = None,
) -> dict[str, object]:
    """Run a manifest against multiple claim-evidence classifiers."""

    manifest_file = Path(manifest_path)
    manifest = load_benchmark_manifest(manifest_file)
    reports = []
    for method in methods:
        classifier = build_classifier(
            method,
            nli_model=nli_model,
            raw_llm_model=raw_llm_model,
            raw_llm_base_url=raw_llm_base_url,
        )
        reports.append(_run_method(manifest_file, manifest, method, classifier))
    return {
        "manifest": str(manifest_file),
        "methods": reports,
        "method_catalog": method_catalog(),
        "layer_policy": layer_policy(manifest),
        "ranking": _rank_summaries(
            _ranking_row(str(report["method"]), report["aggregate"]) for report in reports
        ),
        "layer_ranking": _rank_layers(reports),
    }

def _run_method(
    manifest_file: Path,
    manifest: dict[str, object],
    method: str,
    classifier: Classifier,
) -> dict[str, object]:
    dataset_reports = []
    layer_results: list[dict[str, object]] = []
    all_expected: list[Label] = []
    all_predicted: list[Label] = []
    for entry in manifest["datasets"]:
        dataset_path = _resolve_dataset_path(manifest_file, entry["path"])
        rows = _run_dataset(dataset_path, classifier)
        expected = [Label(row["expected_label"]) for row in rows]
        predicted = [Label(row["predicted_label"]) for row in rows]
        all_expected.extend(expected)
        all_predicted.extend(predicted)
        layer_results.append(
            {
                "name": str(entry["name"]),
                "layer": str(entry["layer"]),
                "expected": expected,
                "predicted": predicted,
            }
        )
        summary = summarize(expected, predicted)
        dataset_reports.append(
            {
                "name": str(entry["name"]),
                "path": str(dataset_path),
                "split": str(entry.get("split", "unspecified")),
                **dataset_report_metadata(entry),
                "summary": summary.to_dict(),
                **dataset_failures(rows, entry),
            }
        )
    return {
        "method": method,
        "datasets": dataset_reports,
        "layers": summarize_layers(layer_results),
        "aggregate": summarize(all_expected, all_predicted).to_dict(),
    }


def _run_dataset(path: Path, classifier: Classifier) -> list[dict[str, object]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        expected = Label(str(data["expected_label"]))
        judgment = classifier(str(data["claim"]), str(data["evidence"]))
        rows.append(
            {
                "id": str(data.get("id") or f"{path.name}:{line_number}"),
                "expected_label": expected.value,
                "predicted_label": judgment.label.value,
                "confidence": round(judgment.confidence, 3),
                "pass": expected == judgment.label,
                "reason": judgment.reason,
            }
        )
    return rows


def _rank_layers(reports: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    layers = sorted(
        {
            layer
            for report in reports
            for layer in _layers_for_report(report).keys()
        }
    )
    return {
        layer: _rank_summaries(
            _ranking_row(str(report["method"]), _layers_for_report(report)[layer]["summary"])
            for report in reports
            if layer in _layers_for_report(report)
        )
        for layer in layers
    }


def _layers_for_report(report: dict[str, object]) -> dict[str, dict[str, object]]:
    layers = report.get("layers", {})
    return layers if isinstance(layers, dict) else {}


def _ranking_row(method: str, summary: object) -> dict[str, object]:
    if not isinstance(summary, dict):
        raise ValueError(f"Benchmark method {method} has no summary metrics.")
    return {
        "method": method,
        "accuracy": summary["accuracy"],
        "false_supported_rate": summary["false_supported_rate"],
        "manual_review_rate": summary["manual_review_rate"],
    }


def _rank_summaries(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (-float(row["accuracy"]), float(row["false_supported_rate"])),
    )


def _resolve_dataset_path(manifest_path: Path, raw_path: object) -> Path:
    dataset_path = Path(str(raw_path))
    return dataset_path if dataset_path.is_absolute() else manifest_path.parent / dataset_path
