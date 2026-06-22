"""JSONL eval runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from citeproof.entailment import judge_evidence
from citeproof.evals.metrics import EvalSummary, summarize
from citeproof.models import EvidenceJudgment, Label

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
        judgment = judge(claim, evidence)
        if data.get("id") is None:
            data["id"] = f"{path.name}:{line_number}"
        rows.append(
            {
                "id": data["id"],
                "expected_label": expected_label.value,
                "predicted_label": judgment.label.value,
                "confidence": round(judgment.confidence, 3),
                "pass": expected_label == judgment.label,
                "reason": judgment.reason,
            }
        )
    return rows
