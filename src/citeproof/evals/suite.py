"""Manifest-driven eval suites."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from citeproof.benchmark_manifest import (
    dataset_report_metadata,
    layer_policy,
    load_benchmark_manifest,
    summarize_layers,
)
from citeproof.entailment import judge_evidence
from citeproof.evals.metrics import EvalSummary, summarize
from citeproof.evals.runner import Judge, run_eval_cases
from citeproof.models import Label

GateCheck = Callable[[EvalSummary, float], tuple[float, bool]]


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
                "failures": [case for case in cases if not case["pass"]],
            }
        )
    aggregate = summarize(all_expected, all_predicted)
    gate_results = _evaluate_gates(aggregate, manifest.get("gates", {}))
    return {
        "manifest": str(manifest_file),
        "datasets": reports,
        "layers": summarize_layers(layer_results),
        "layer_policy": layer_policy(manifest),
        "aggregate": aggregate.to_dict(),
        "gates": gate_results,
        "passed": all(result["pass"] for result in gate_results),
    }


def suite_passed(report: dict[str, object]) -> bool:
    """Return whether every gate in an eval-suite report passed."""

    return bool(report.get("passed", False))


def _resolve_dataset_path(manifest_path: Path, raw_path: object) -> Path:
    dataset_path = Path(str(raw_path))
    if dataset_path.is_absolute():
        return dataset_path
    return manifest_path.parent / dataset_path


def _evaluate_gates(summary: EvalSummary, gates: dict[str, object]) -> list[dict[str, object]]:
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


def _gate_checks() -> dict[str, GateCheck]:
    return {
        "max_false_supported_rate": lambda summary, threshold: (
            summary.false_supported_rate,
            summary.false_supported_rate <= threshold,
        ),
        "min_accuracy": lambda summary, threshold: (summary.accuracy, summary.accuracy >= threshold),
        "max_manual_review_rate": lambda summary, threshold: (
            summary.manual_review_rate,
            summary.manual_review_rate <= threshold,
        ),
        "min_supported_precision": lambda summary, threshold: (
            summary.supported_precision,
            summary.supported_precision >= threshold,
        ),
        "min_contradiction_recall": lambda summary, threshold: (
            summary.contradiction_recall,
            summary.contradiction_recall >= threshold,
        ),
        "min_unsupported_recall": lambda summary, threshold: (
            summary.unsupported_recall,
            summary.unsupported_recall >= threshold,
        ),
    }
