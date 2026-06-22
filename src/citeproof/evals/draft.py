"""End-to-end draft evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from citeproof.evals.metrics import summarize
from citeproof.models import Label
from citeproof.paper import load_bib_aligned_sources
from citeproof.parser import parse_claims
from citeproof.sources import build_chunks
from citeproof.verifier import verify_claim, verify_draft


def run_draft_eval(
    draft_path: str | Path,
    source_dir: str | Path,
    expected_path: str | Path,
    bib_path: str | Path | None = None,
) -> dict:
    """Evaluate draft verifier labels against expected JSONL cases."""

    results = _verify_draft_for_eval(draft_path, source_dir, bib_path)
    cases = _load_expected(expected_path)
    expected: list[Label] = []
    predicted: list[Label] = []
    rows = []
    for case in cases:
        result = _find_result(case["claim_contains"], results)
        expected_label = Label(case["expected_label"])
        expected.append(expected_label)
        predicted.append(result.label)
        rows.append(
            {
                "id": case["id"],
                "claim_contains": case["claim_contains"],
                "expected_label": expected_label.value,
                "predicted_label": result.label.value,
                "pass": expected_label == result.label,
                "reason": result.reason,
            }
        )
    return {"summary": summarize(expected, predicted).to_json(), "cases": rows}


def _verify_draft_for_eval(
    draft_path: str | Path,
    source_dir: str | Path,
    bib_path: str | Path | None,
):
    if bib_path is None:
        return verify_draft(draft_path, source_dir)
    trusted_sources, _loaded_count, _mapped_count = load_bib_aligned_sources(bib_path, source_dir)
    chunks = build_chunks(trusted_sources)
    claims = parse_claims(Path(draft_path).read_text(encoding="utf-8"))
    return [verify_claim(claim, chunks) for claim in claims]


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
