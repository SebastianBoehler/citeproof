"""End-to-end draft evaluation."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from citeproof.entailment import judge_evidence
from citeproof.evals.metrics import summarize
from citeproof.models import EvidenceJudgment, FailureMode, Label, VerificationResult
from citeproof.paper import load_bib_aligned_sources
from citeproof.parser import parse_claims
from citeproof.sources import build_chunks
from citeproof.verifier import verify_claim, verify_draft

Judge = Callable[[str, str], EvidenceJudgment]


def run_draft_eval(
    draft_path: str | Path,
    source_dir: str | Path,
    expected_path: str | Path,
    bib_path: str | Path | None = None,
    judge: Judge = judge_evidence,
) -> dict:
    """Evaluate draft verifier labels against expected JSONL cases."""

    results = _verify_draft_for_eval(draft_path, source_dir, bib_path, judge)
    cases = _load_expected(expected_path)
    expected: list[Label] = []
    predicted: list[Label] = []
    rows = []
    for case in cases:
        result = _find_result(case["claim_contains"], results)
        row = _case_row(case, result)
        expected.append(Label(row["expected_label"]))
        predicted.append(Label(row["predicted_label"]))
        rows.append(row)
    return {"summary": summarize(expected, predicted).to_json(), "cases": rows}


def _verify_draft_for_eval(
    draft_path: str | Path,
    source_dir: str | Path,
    bib_path: str | Path | None,
    judge: Judge,
):
    if bib_path is None:
        return verify_draft(draft_path, source_dir, judge=judge)
    trusted_sources, _loaded_count, _mapped_count = load_bib_aligned_sources(bib_path, source_dir)
    chunks = build_chunks(trusted_sources)
    claims = parse_claims(Path(draft_path).read_text(encoding="utf-8"))
    return [verify_claim(claim, chunks, judge=judge) for claim in claims]


def _case_row(case: dict[str, str], result: VerificationResult) -> dict[str, object]:
    expected_label = Label(case["expected_label"])
    label_pass = expected_label == result.label
    expected_failure_mode = (
        FailureMode(case["expected_failure_mode"]) if "expected_failure_mode" in case else None
    )
    row = {
        "id": case["id"],
        "claim_contains": case["claim_contains"],
        "expected_label": expected_label.value,
        "predicted_label": result.label.value,
        "confidence": result.confidence,
        "false_supported": expected_label != Label.SUPPORTED and result.label == Label.SUPPORTED,
        "failure_mode": result.failure_mode.value if result.failure_mode else None,
        "pass": label_pass,
        "reason": result.reason,
        **_trace_diagnostics(result),
    }
    if expected_failure_mode is not None:
        failure_mode_pass = result.failure_mode == expected_failure_mode
        row["expected_failure_mode"] = expected_failure_mode.value
        row["failure_mode_pass"] = failure_mode_pass
        row["pass"] = label_pass and failure_mode_pass
    return row


def _trace_diagnostics(result: VerificationResult) -> dict[str, object]:
    trace = result.trace
    if trace is None:
        return {
            "source_gate_status": None,
            "candidate_count": 0,
            "support_candidate_count": 0,
            "contradiction_candidate_count": 0,
            "best_support_rank": None,
            "best_contradiction_rank": None,
        }
    atoms = trace.atom_verifications
    return {
        "source_gate_status": trace.source_gate_status,
        "candidate_count": sum(atom.candidate_count for atom in atoms),
        "support_candidate_count": sum(atom.support_candidate_count for atom in atoms),
        "contradiction_candidate_count": sum(atom.contradiction_candidate_count for atom in atoms),
        "best_support_rank": _best_rank(atom.best_support_rank for atom in atoms),
        "best_contradiction_rank": _best_rank(atom.best_contradiction_rank for atom in atoms),
    }


def _best_rank(values) -> int | None:
    return min((value for value in values if value is not None), default=None)


def _load_expected(path: str | Path) -> list[dict[str, str]]:
    cases = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        data.setdefault("id", f"{Path(path).name}:{line_number}")
        cases.append(data)
    return cases


def _find_result(claim_contains: str, results):
    matches = [result for result in results if claim_contains in result.claim]
    if not matches:
        raise ValueError(f"No verified claim contains: {claim_contains}")
    if len(matches) > 1:
        raise ValueError(f"Multiple verified claims contain: {claim_contains}")
    return matches[0]
