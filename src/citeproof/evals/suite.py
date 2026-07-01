"""Manifest-driven eval suites."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from citeproof.benchmark_manifest import (
    dataset_failures,
    dataset_report_metadata,
    layer_policy,
    load_benchmark_manifest,
    summarize_layers,
)
from citeproof.entailment import judge_evidence
from citeproof.evals.metrics import summarize
from citeproof.evals.runner import Judge, run_eval_cases
from citeproof.models import Label

GateCheck = Callable[[dict[str, object], float], tuple[float, bool]]


def run_eval_suite(
    manifest_path: str | Path,
    judge: Judge = judge_evidence,
) -> dict[str, object]:
    """Run all direct claim-support datasets declared in a suite manifest."""

    manifest_file = Path(manifest_path)
    manifest = load_benchmark_manifest(manifest_file)
    reports: list[dict[str, object]] = []
    layer_results: list[dict[str, object]] = []
    all_expected: list[Label] = []
    all_predicted: list[Label] = []
    for entry in manifest["datasets"]:
        dataset_path = _resolve_dataset_path(manifest_file, entry["path"])
        cases = run_eval_cases(dataset_path, judge=judge)
        expected = [Label(case["expected_label"]) for case in cases]
        predicted = [Label(case["predicted_label"]) for case in cases]
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
        reports.append(
            {
                "name": str(entry["name"]),
                "path": str(dataset_path),
                "split": str(entry.get("split", "unspecified")),
                **dataset_report_metadata(entry),
                "summary": summary.to_dict(),
                **dataset_failures(cases, entry),
            }
        )
    aggregate = summarize(all_expected, all_predicted)
    layers = summarize_layers(layer_results)
    gate_results = _evaluate_gates(aggregate.to_dict(), manifest.get("gates", {}))
    layer_gate_results = _evaluate_layer_gates(layers, manifest.get("layer_gates", {}))
    return {
        "manifest": str(manifest_file),
        "datasets": reports,
        "layers": layers,
        "layer_policy": layer_policy(manifest),
        "aggregate": aggregate.to_dict(),
        "gates": gate_results,
        "layer_gates": layer_gate_results,
        "passed": _all_gates_pass(gate_results, layer_gate_results),
    }


def suite_passed(report: dict[str, object]) -> bool:
    """Return whether every gate in an eval-suite report passed."""

    return bool(report.get("passed", False))


def _resolve_dataset_path(manifest_path: Path, raw_path: object) -> Path:
    dataset_path = Path(str(raw_path))
    if dataset_path.is_absolute():
        return dataset_path
    return manifest_path.parent / dataset_path


def _evaluate_gates(summary: dict[str, object], gates: dict[str, object]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    checks = _gate_checks()
    for name, raw_threshold in gates.items():
        if name not in checks:
            raise ValueError(f"Unsupported eval-suite gate: {name}")
        threshold = float(raw_threshold)
        actual, passed = checks[name](summary, threshold)
        results.append(
            {
                "name": name,
                "actual": actual,
                "threshold": threshold,
                "pass": passed,
            }
        )
    return results


def _evaluate_layer_gates(
    layers: dict[str, object],
    layer_gates: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    results = {}
    for layer, gates in layer_gates.items():
        if layer not in layers:
            raise ValueError(f"layer_gates references unknown benchmark layer: {layer}")
        if not isinstance(gates, dict):
            raise ValueError(f"Layer gates for {layer} must be an object.")
        layer_report = layers[str(layer)]
        if not isinstance(layer_report, dict) or not isinstance(layer_report.get("summary"), dict):
            raise ValueError(f"Benchmark layer {layer} has no summary metrics.")
        results[str(layer)] = _evaluate_gates(layer_report["summary"], gates)
    return results


def _all_gates_pass(
    gates: list[dict[str, object]],
    layer_gates: dict[str, list[dict[str, object]]],
) -> bool:
    return all(result["pass"] for result in gates) and all(
        result["pass"] for results in layer_gates.values() for result in results
    )


def _gate_checks() -> dict[str, GateCheck]:
    return {
        "max_false_supported_rate": lambda summary, threshold: (
            _metric(summary, "false_supported_rate"),
            _metric(summary, "false_supported_rate") <= threshold,
        ),
        "min_accuracy": lambda summary, threshold: (
            _metric(summary, "accuracy"),
            _metric(summary, "accuracy") >= threshold,
        ),
        "max_manual_review_rate": lambda summary, threshold: (
            _metric(summary, "manual_review_rate"),
            _metric(summary, "manual_review_rate") <= threshold,
        ),
        "min_supported_precision": lambda summary, threshold: (
            _metric(summary, "supported_precision"),
            _metric(summary, "supported_precision") >= threshold,
        ),
        "min_contradiction_recall": lambda summary, threshold: (
            _metric(summary, "contradiction_recall"),
            _metric(summary, "contradiction_recall") >= threshold,
        ),
        "min_unsupported_recall": lambda summary, threshold: (
            _metric(summary, "unsupported_recall"),
            _metric(summary, "unsupported_recall") >= threshold,
        ),
    }


def _metric(summary: dict[str, object], name: str) -> float:
    value = summary.get(name)
    if not isinstance(value, int | float):
        raise ValueError(f"Eval summary is missing numeric metric: {name}")
    return float(value)
