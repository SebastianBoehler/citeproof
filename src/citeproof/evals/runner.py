"""JSONL eval runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.evals.metrics import EvalSummary, summarize
from citeproof.models import EvidenceJudgment, FailureMode, Label

Judge = Callable[[str, str], EvidenceJudgment]


def run_eval_file(dataset_path: str | Path, judge: Judge = judge_evidence) -> EvalSummary:
    """Run direct evidence-vs-claim eval examples from JSONL."""

    cases = run_eval_cases(dataset_path, judge)
    expected = [Label(case["expected_label"]) for case in cases]
    predicted = [Label(case["predicted_label"]) for case in cases]
    return summarize(expected, predicted)


def run_eval_cases(dataset_path: str | Path, judge: Judge = judge_evidence) -> list[dict]:
    """Run direct evidence-vs-claim eval examples and return per-case rows."""

    rows = []
    path = Path(dataset_path)
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        claim = str(data["claim"])
        evidence = str(data["evidence"])
        expected_label = Label(str(data["expected_label"]))
        expected_failure_mode = (
            FailureMode(str(data["expected_failure_mode"]))
            if "expected_failure_mode" in data
            else None
        )
        judgment = adjudicate_evidence(claim, evidence, judge=judge)
        if data.get("id") is None:
            data["id"] = f"{path.name}:{line_number}"
        label_pass = expected_label == judgment.label
        row = {
            "id": data["id"],
            "expected_label": expected_label.value,
            "predicted_label": judgment.label.value,
            "confidence": round(judgment.confidence, 3),
            "failure_mode": judgment.failure_mode.value if judgment.failure_mode else None,
            "false_supported": expected_label != Label.SUPPORTED and judgment.label == Label.SUPPORTED,
            "pass": label_pass,
            "reason": judgment.reason,
        }
        if expected_failure_mode is not None:
            failure_mode_pass = judgment.failure_mode == expected_failure_mode
            row["expected_failure_mode"] = expected_failure_mode.value
            row["failure_mode_pass"] = failure_mode_pass
            row["pass"] = label_pass and failure_mode_pass
        rows.append(row)
    return rows
