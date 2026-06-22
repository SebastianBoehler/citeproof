# Eval Suite Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manifest-driven `eval-suite` command that evaluates multiple direct claim-support datasets and fails explicitly when aggregate reliability gates are violated.

**Architecture:** Reuse the existing JSONL `run_eval_cases` path. Add a focused `citeproof.evals.suite` module for manifest loading, relative path resolution, aggregate metrics, and gate checks. Add a thin CLI wrapper plus docs, example manifest, tests, and CI coverage.

**Tech Stack:** Python stdlib JSON/pathlib/dataclasses, existing `citeproof.evals.runner`, existing `EvalSummary`, pytest, ruff, uv.

---

## File Structure

- Create `src/citeproof/evals/suite.py`: manifest runner and gate evaluator.
- Create `tests/test_eval_suite.py`: direct module tests and CLI exit-code tests.
- Modify `src/citeproof/cli.py`: add `eval-suite` subcommand.
- Add `examples/eval_suite.json`: strict primary plus edge suite manifest.
- Modify `README.md`: document the new command.
- Modify `docs/evaluation.md`: explain suite-level gates and held-out use.
- Modify `.github/workflows/tests.yml`: run `eval-suite` in CI.

## Task 1: Suite Module Tests

**Files:**
- Create: `tests/test_eval_suite.py`

- [ ] **Step 1: Write failing module tests**

```python
import json
from pathlib import Path

import pytest

from citeproof.evals.suite import run_eval_suite


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_eval_suite_resolves_manifest_relative_paths(tmp_path: Path) -> None:
    suite_dir = tmp_path / "suite"
    suite_dir.mkdir()
    _write_jsonl(
        suite_dir / "cases.jsonl",
        [
            {
                "id": "supported",
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "supported",
            },
            {
                "id": "contradicted",
                "claim": "A improves B.",
                "evidence": "A does not improve B.",
                "expected_label": "contradicted",
            },
        ],
    )
    manifest = suite_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [{"name": "tiny", "path": "cases.jsonl", "split": "heldout"}],
                "gates": {"max_false_supported_rate": 0.0, "min_accuracy": 1.0},
            }
        ),
        encoding="utf-8",
    )

    report = run_eval_suite(manifest)

    assert report["aggregate"]["total"] == 2
    assert report["datasets"][0]["name"] == "tiny"
    assert report["datasets"][0]["split"] == "heldout"
    assert report["datasets"][0]["summary"]["false_supported_rate"] == 0.0
    assert all(gate["pass"] for gate in report["gates"])


def test_eval_suite_reports_failing_gate(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    _write_jsonl(
        dataset,
        [
            {
                "id": "false-supported",
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "unsupported",
            }
        ],
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [{"name": "bad", "path": "cases.jsonl"}],
                "gates": {"max_false_supported_rate": 0.0},
            }
        ),
        encoding="utf-8",
    )

    report = run_eval_suite(manifest)

    assert report["aggregate"]["false_supported_rate"] == 1.0
    assert report["gates"] == [
        {
            "name": "max_false_supported_rate",
            "actual": 1.0,
            "threshold": 0.0,
            "pass": False,
        }
    ]
    assert report["datasets"][0]["failures"][0]["id"] == "false-supported"


def test_eval_suite_rejects_unknown_gate(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    _write_jsonl(
        dataset,
        [
            {
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "supported",
            }
        ],
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [{"name": "tiny", "path": "cases.jsonl"}],
                "gates": {"unknown_gate": 0.0},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported eval-suite gate"):
        run_eval_suite(manifest)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_eval_suite.py -q`

Expected: import failure for missing `citeproof.evals.suite`.

## Task 2: Suite Module Implementation

**Files:**
- Create: `src/citeproof/evals/suite.py`
- Test: `tests/test_eval_suite.py`

- [ ] **Step 1: Implement suite runner**

Create `src/citeproof/evals/suite.py`:

```python
"""Manifest-driven eval suites."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

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
    manifest = _load_manifest(manifest_file)
    datasets = manifest["datasets"]
    gates = manifest.get("gates", {})
    reports: list[dict[str, object]] = []
    all_expected: list[Label] = []
    all_predicted: list[Label] = []
    for entry in datasets:
        dataset_path = _resolve_dataset_path(manifest_file, entry["path"])
        cases = run_eval_cases(dataset_path, judge=judge)
        expected = [Label(case["expected_label"]) for case in cases]
        predicted = [Label(case["predicted_label"]) for case in cases]
        all_expected.extend(expected)
        all_predicted.extend(predicted)
        summary = summarize(expected, predicted)
        reports.append(
            {
                "name": str(entry["name"]),
                "path": str(dataset_path),
                "split": str(entry.get("split", "unspecified")),
                "summary": summary.to_dict(),
                "failures": [case for case in cases if not case["pass"]],
            }
        )
    aggregate = summarize(all_expected, all_predicted)
    gate_results = _evaluate_gates(aggregate, gates)
    return {
        "manifest": str(manifest_file),
        "datasets": reports,
        "aggregate": aggregate.to_dict(),
        "gates": gate_results,
        "passed": all(result["pass"] for result in gate_results),
    }


def suite_passed(report: dict[str, object]) -> bool:
    """Return whether every gate in an eval-suite report passed."""

    return bool(report.get("passed", False))


def _load_manifest(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    datasets = data.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("Eval-suite manifest must contain a non-empty datasets list.")
    for index, entry in enumerate(datasets, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Dataset entry {index} must be an object.")
        if "name" not in entry or "path" not in entry:
            raise ValueError(f"Dataset entry {index} must contain name and path.")
    gates = data.get("gates", {})
    if not isinstance(gates, dict):
        raise ValueError("Eval-suite gates must be an object when provided.")
    return data


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
```

- [ ] **Step 2: Run suite module tests**

Run: `uv run pytest tests/test_eval_suite.py -q`

Expected: all tests pass.

## Task 3: CLI Integration Tests and Implementation

**Files:**
- Modify: `tests/test_eval_suite.py`
- Modify: `src/citeproof/cli.py`

- [ ] **Step 1: Add CLI exit-code tests**

Append to `tests/test_eval_suite.py`:

```python
from citeproof.cli import main


def test_eval_suite_cli_returns_zero_for_passing_gates(tmp_path: Path, capsys) -> None:
    dataset = tmp_path / "cases.jsonl"
    _write_jsonl(
        dataset,
        [{"claim": "A improves B.", "evidence": "A improves B.", "expected_label": "supported"}],
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [{"name": "tiny", "path": "cases.jsonl"}],
                "gates": {"max_false_supported_rate": 0.0},
            }
        ),
        encoding="utf-8",
    )

    code = main(["eval-suite", str(manifest)])

    captured = capsys.readouterr()
    assert code == 0
    assert '"passed": true' in captured.out


def test_eval_suite_cli_returns_two_for_failing_gates(tmp_path: Path, capsys) -> None:
    dataset = tmp_path / "cases.jsonl"
    _write_jsonl(
        dataset,
        [
            {
                "claim": "A improves B.",
                "evidence": "A improves B.",
                "expected_label": "unsupported",
            }
        ],
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "datasets": [{"name": "bad", "path": "cases.jsonl"}],
                "gates": {"max_false_supported_rate": 0.0},
            }
        ),
        encoding="utf-8",
    )

    code = main(["eval-suite", str(manifest)])

    captured = capsys.readouterr()
    assert code == 2
    assert '"passed": false' in captured.out
```

- [ ] **Step 2: Run CLI tests to verify failure**

Run: `uv run pytest tests/test_eval_suite.py -q`

Expected: CLI tests fail because `eval-suite` is not registered.

- [ ] **Step 3: Add CLI handler**

Modify `src/citeproof/cli.py`:

```python
def _run_eval_suite(args: argparse.Namespace) -> int:
    from citeproof.evals.suite import run_eval_suite, suite_passed

    report = run_eval_suite(args.manifest, judge=_make_judge(args))
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output:
        _write_text(args.json_output, text)
    print(text)
    return 0 if suite_passed(report) else 2
```

Add parser registration after `eval`:

```python
    eval_suite = subparsers.add_parser("eval-suite", help="Run a manifest of claim-support eval datasets.")
    eval_suite.add_argument("manifest")
    eval_suite.add_argument("--json-output")
    _add_verifier_args(eval_suite)
    eval_suite.set_defaults(func=_run_eval_suite)
```

- [ ] **Step 4: Run CLI tests**

Run: `uv run pytest tests/test_eval_suite.py -q`

Expected: all tests pass.

## Task 4: Example Manifest, Docs, and CI

**Files:**
- Add: `examples/eval_suite.json`
- Modify: `README.md`
- Modify: `docs/evaluation.md`
- Modify: `.github/workflows/tests.yml`

- [ ] **Step 1: Add example suite manifest**

Create `examples/eval_suite.json`:

```json
{
  "datasets": [
    {
      "name": "primary",
      "path": "claim_support.jsonl",
      "split": "curated"
    },
    {
      "name": "edge",
      "path": "edge_cases/claim_support.jsonl",
      "split": "adversarial"
    }
  ],
  "gates": {
    "max_false_supported_rate": 0.0,
    "min_accuracy": 1.0,
    "max_manual_review_rate": 0.35,
    "min_supported_precision": 1.0,
    "min_contradiction_recall": 1.0,
    "min_unsupported_recall": 1.0
  }
}
```

- [ ] **Step 2: Document README quick-start command**

Add this command after the edge eval command:

```bash
uv run citeproof eval-suite examples/eval_suite.json
```

Add one sentence in the benchmark paragraph:

```markdown
Use `eval-suite` for CI and private held-out benchmarks because it reports
aggregate metrics and fails when reliability gates are violated.
```

- [ ] **Step 3: Document eval-suite in `docs/evaluation.md`**

Add a `Suite Gates` section:

```markdown
## Suite Gates

Use `eval-suite` when comparing multiple benchmark files or running private
held-out cases:

```bash
uv run citeproof eval-suite examples/eval_suite.json
```

The suite manifest resolves dataset paths relative to the manifest file. The
committed suite gates aggregate direct claim-support metrics across the primary
and edge datasets and currently require `false_supported_rate = 0.0`.
Private real-paper suites should use the same JSONL row format and a separate
manifest that is not committed when source text cannot be redistributed.
```
```

- [ ] **Step 4: Add CI command**

Add to `.github/workflows/tests.yml` after `Run sample eval`:

```yaml
      - name: Run eval suite
        run: uv run citeproof eval-suite examples/eval_suite.json
```

- [ ] **Step 5: Run eval suite**

Run: `uv run citeproof eval-suite examples/eval_suite.json`

Expected: exit code `0`, aggregate total `116`, `false_supported_rate` `0.0`, and `"passed": true`.

## Task 5: Full Verification and Commit

**Files:**
- All modified files.

- [ ] **Step 1: Run full tests**

Run:

```bash
uv run pytest -q -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 2: Run benchmark gates**

Run:

```bash
uv run citeproof eval-suite examples/eval_suite.json
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output reports/hallucination_bib_gated_details.json
```

Expected: all commands exit `0`; direct suite aggregate total is `116`; false-supported rate is `0.0`.

- [ ] **Step 3: Run lint**

Run:

```bash
uv run ruff check --no-cache .
```

Expected: no lint failures.

- [ ] **Step 4: Commit implementation**

Run:

```bash
git add src/citeproof/evals/suite.py src/citeproof/cli.py tests/test_eval_suite.py \
  examples/eval_suite.json README.md docs/evaluation.md .github/workflows/tests.yml
git commit -m "feat: add eval suite gates"
```

- [ ] **Step 5: Push and verify CI**

Run:

```bash
git push origin main
gh run list --branch main --limit 1
gh run watch <latest-run-id> --exit-status
```

Expected: pushed commit is on `origin/main`; latest CI passes.
