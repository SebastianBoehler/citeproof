"""Compare CiteProof against benchmark baselines."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from citeproof.adjudicator import adjudicate_evidence
from citeproof.benchmark_manifest import (
    dataset_report_metadata,
    layer_policy,
    load_benchmark_manifest,
    summarize_layers,
)
from citeproof.evals.metrics import summarize
from citeproof.models import EvidenceJudgment, Label
from citeproof.text import token_overlap_ratio

Classifier = Callable[[str, str], EvidenceJudgment]
LABELS = {label.value for label in Label}


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
        "layer_policy": layer_policy(manifest),
        "ranking": _rank_summaries(
            _ranking_row(str(report["method"]), report["aggregate"]) for report in reports
        ),
        "layer_ranking": _rank_layers(reports),
    }


def build_classifier(
    method: str,
    *,
    nli_model: str | None = None,
    raw_llm_model: str | None = None,
    raw_llm_base_url: str | None = None,
) -> Classifier:
    """Create a benchmark classifier by method name."""

    if method == "citeproof":
        return adjudicate_evidence
    if method == "lexical":
        return lexical_classifier
    if method == "nli":
        from citeproof.nli import build_nli_judge

        return build_nli_judge(nli_model)
    if method == "raw-llm":
        return OpenAIChatClassifier(
            raw_llm_model or os.getenv("CITEPROOF_RAW_LLM_MODEL", "gpt-4.1-mini"),
            base_url=raw_llm_base_url or os.getenv("CITEPROOF_RAW_LLM_BASE_URL"),
        )
    raise ValueError(f"Unknown benchmark comparison method: {method}")


def lexical_classifier(claim: str, evidence: str) -> EvidenceJudgment:
    """Simple token-overlap baseline with no contradiction reasoning."""

    overlap = token_overlap_ratio(claim, evidence)
    if overlap >= 0.68:
        return EvidenceJudgment(Label.SUPPORTED, min(0.95, 0.55 + overlap / 2), "Lexical overlap.")
    if overlap >= 0.38:
        return EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.45 + overlap / 2, "Partial overlap.")
    return EvidenceJudgment(Label.UNSUPPORTED, 0.35, "Low lexical overlap.")


class OpenAIChatClassifier:
    """Raw LLM claim-evidence classifier using an OpenAI-compatible chat endpoint."""

    def __init__(self, model: str, *, base_url: str | None = None, timeout: float = 60.0) -> None:
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("raw-llm comparison requires OPENAI_API_KEY.")

    def __call__(self, claim: str, evidence: str) -> EvidenceJudgment:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify whether the evidence supports the claim. Return only JSON with "
                        "label, confidence, and reason. Labels: supported, partially_supported, "
                        "contradicted, unsupported, uncertain."
                    ),
                },
                {"role": "user", "content": f"Claim: {claim}\n\nEvidence: {evidence}"},
            ],
        }
        data = self._post(payload)
        content = data["choices"][0]["message"]["content"]
        parsed = _parse_json_object(str(content))
        label = _normalize_label(str(parsed.get("label", "uncertain")))
        confidence = float(parsed.get("confidence", 0.5))
        return EvidenceJudgment(label, max(0.0, min(1.0, confidence)), str(parsed.get("reason", "")))

    def _post(self, payload: dict[str, object]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"raw-llm request failed with HTTP {exc.code}: {body}") from exc


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
                "failures": [row for row in rows if not row["pass"]],
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


def _parse_json_object(text: str) -> dict[str, object]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("raw-llm response did not contain a JSON object.")
        return json.loads(match.group(0))


def _normalize_label(raw: str) -> Label:
    label = raw.strip().casefold().replace("-", "_")
    aliases = {"support": "supported", "refuted": "contradicted", "neutral": "unsupported"}
    label = aliases.get(label, label)
    if label not in LABELS:
        return Label.UNCERTAIN
    return Label(label)
