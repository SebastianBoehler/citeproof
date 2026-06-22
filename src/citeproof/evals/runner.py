"""JSONL eval runner."""

from __future__ import annotations

import json
from pathlib import Path

from citeproof.entailment import judge_evidence
from citeproof.evals.metrics import EvalSummary, summarize
from citeproof.models import Label


def run_eval_file(dataset_path: str | Path) -> EvalSummary:
    """Run direct evidence-vs-claim eval examples from JSONL."""

    expected: list[Label] = []
    predicted: list[Label] = []
    path = Path(dataset_path)
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        claim = str(data["claim"])
        evidence = str(data["evidence"])
        expected_label = Label(str(data["expected_label"]))
        judgment = judge_evidence(claim, evidence)
        expected.append(expected_label)
        predicted.append(judgment.label)
        if data.get("id") is None:
            data["id"] = f"{path.name}:{line_number}"
    return summarize(expected, predicted)
