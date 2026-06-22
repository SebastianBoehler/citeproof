# Draft Eval Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `eval-draft` retrieval-aware by reporting false-supported rows, failure modes, and verifier trace diagnostics, with optional NLI judge support.

**Architecture:** Extend the existing `citeproof.evals.draft` module instead of creating a new benchmark command. Add a small trace-flattening helper inside `draft.py`, pass a judge through the draft eval path, and register verifier arguments on the existing CLI subcommand.

**Tech Stack:** Python stdlib, existing `Label`/`FailureMode` models, existing `verify_draft`/`verify_claim`, pytest, ruff, uv.

---

## File Structure

- Modify `src/citeproof/evals/draft.py`: pass through `judge`, support expected failure modes, and emit trace diagnostics.
- Modify `src/citeproof/cli.py`: add verifier args to `eval-draft` and pass the selected judge.
- Modify `tests/test_draft_eval.py`: add diagnostics and custom-judge tests.
- Modify `docs/evaluation.md`: document draft diagnostics.
- Modify `README.md`: mention `eval-draft --verifier nli`.

## Task 1: Failing Draft Eval Diagnostics Tests

**Files:**
- Modify: `tests/test_draft_eval.py`

- [ ] **Step 1: Add tests for diagnostics and failure-mode assertions**

Append these tests to `tests/test_draft_eval.py`:

```python
from citeproof.models import EvidenceJudgment, Label


def test_draft_eval_reports_trace_diagnostics(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "methodx.md").write_text(
        "Method X performed comparably to PPO, with no statistically significant improvement.",
        encoding="utf-8",
    )
    draft = tmp_path / "draft.md"
    draft.write_text("Method X outperforms PPO [@methodx].", encoding="utf-8")
    expected = tmp_path / "expected.jsonl"
    expected.write_text(
        '{"id":"contradicted","claim_contains":"Method X","expected_label":"contradicted",'
        '"expected_failure_mode":"negation_conflict"}\n',
        encoding="utf-8",
    )

    result = run_draft_eval(draft, sources, expected)
    case = result["cases"][0]

    assert case["pass"]
    assert case["false_supported"] is False
    assert case["failure_mode"] == "negation_conflict"
    assert case["failure_mode_pass"] is True
    assert case["source_gate_status"] == "passed"
    assert case["candidate_count"] >= 1
    assert case["contradiction_candidate_count"] >= 1
    assert case["best_contradiction_rank"] == 1
```

- [ ] **Step 2: Add a custom-judge pass-through test**

Append:

```python
def test_draft_eval_accepts_custom_judge(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "real2024.md").write_text("A improves B.", encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text("A improves B [@real2024].", encoding="utf-8")
    expected = tmp_path / "expected.jsonl"
    expected.write_text(
        '{"id":"custom","claim_contains":"A improves B","expected_label":"unsupported"}\n',
        encoding="utf-8",
    )

    def judge(_claim: str, _evidence: str) -> EvidenceJudgment:
        return EvidenceJudgment(Label.UNSUPPORTED, 0.91, "custom judge")

    result = run_draft_eval(draft, sources, expected, judge=judge)

    assert result["cases"][0]["predicted_label"] == "unsupported"
    assert result["cases"][0]["pass"]
```

- [ ] **Step 3: Run tests to verify failure**

Run: `uv run pytest tests/test_draft_eval.py -q`

Expected: diagnostics keys are missing and `run_draft_eval` does not accept `judge`.

## Task 2: Draft Eval Implementation

**Files:**
- Modify: `src/citeproof/evals/draft.py`
- Test: `tests/test_draft_eval.py`

- [ ] **Step 1: Update imports and function signatures**

In `src/citeproof/evals/draft.py`, add:

```python
from citeproof.entailment import judge_evidence
from citeproof.models import EvidenceJudgment, FailureMode, Label, VerificationResult
```

Change `run_draft_eval` to:

```python
def run_draft_eval(
    draft_path: str | Path,
    source_dir: str | Path,
    expected_path: str | Path,
    bib_path: str | Path | None = None,
    judge=judge_evidence,
) -> dict:
```

Change `_verify_draft_for_eval` to accept and pass `judge`.

- [ ] **Step 2: Add row diagnostics helpers**

Add:

```python
def _case_row(case: dict[str, str], result: VerificationResult) -> dict[str, object]:
    expected_label = Label(case["expected_label"])
    label_pass = expected_label == result.label
    expected_failure_mode = (
        FailureMode(case["expected_failure_mode"])
        if "expected_failure_mode" in case
        else None
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
```

- [ ] **Step 3: Use `_case_row` in `run_draft_eval`**

Replace the inline row construction with:

```python
row = _case_row(case, result)
expected.append(Label(row["expected_label"]))
predicted.append(Label(row["predicted_label"]))
rows.append(row)
```

- [ ] **Step 4: Run draft eval tests**

Run: `uv run pytest tests/test_draft_eval.py -q`

Expected: all tests pass.

## Task 3: CLI Verifier Argument Support

**Files:**
- Modify: `src/citeproof/cli.py`
- Modify: `tests/test_draft_eval.py`

- [ ] **Step 1: Add parser-level CLI test**

Append to `tests/test_draft_eval.py`:

```python
def test_eval_draft_cli_accepts_verifier_args(tmp_path: Path, monkeypatch, capsys) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text("", encoding="utf-8")
    expected = tmp_path / "expected.jsonl"
    expected.write_text("", encoding="utf-8")

    import citeproof.cli as cli

    def fake_run_draft_eval(draft_path, source_dir, expected_path, bib_path=None, judge=None):
        assert draft_path == str(draft)
        assert source_dir == str(sources)
        assert expected_path == str(expected)
        assert bib_path is None
        assert judge is not None
        return {"summary": "{}", "cases": []}

    monkeypatch.setattr(cli, "run_draft_eval", fake_run_draft_eval)
    code = cli.main(
        [
            "eval-draft",
            str(draft),
            "--sources",
            str(sources),
            "--expected",
            str(expected),
            "--verifier",
            "heuristic",
        ]
    )

    assert code == 0
    assert "{}" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_draft_eval.py::test_eval_draft_cli_accepts_verifier_args -q`

Expected: parser rejects `--verifier`.

- [ ] **Step 3: Wire CLI**

Change `_run_eval_draft` in `src/citeproof/cli.py`:

```python
result = run_draft_eval(args.draft, args.sources, args.expected, args.bib, judge=_make_judge(args))
```

Add `_add_verifier_args(eval_draft)` before `eval_draft.set_defaults(...)`.

- [ ] **Step 4: Run draft tests**

Run: `uv run pytest tests/test_draft_eval.py -q`

Expected: all tests pass.

## Task 4: Docs

**Files:**
- Modify: `docs/evaluation.md`
- Modify: `README.md`

- [ ] **Step 1: Update docs**

In `docs/evaluation.md`, add to Reading Scores:

```markdown
- Draft `eval-draft` details additionally include retrieval trace diagnostics:
  `source_gate_status`, `candidate_count`, `support_candidate_count`,
  `contradiction_candidate_count`, `best_support_rank`, and
  `best_contradiction_rank`.
```

In README, after the NLI `verify-paper` example, add:

```markdown
The same verifier flag is available for draft evaluation:

```bash
CITEPROOF_DEVICE=cpu \
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --verifier nli
```
```

- [ ] **Step 2: Run docs grep**

Run: `rg -n "eval-draft.*verifier|source_gate_status|best_contradiction_rank" README.md docs/evaluation.md`

Expected: new documentation lines are found.

## Task 5: Full Verification and Commit

**Files:**
- All modified files.

- [ ] **Step 1: Run full test suite**

Run:

```bash
uv run pytest -q -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 2: Run benchmark commands**

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

Expected: all commands exit successfully; false-supported rate remains `0.0`.

- [ ] **Step 3: Run lint**

Run: `uv run ruff check --no-cache .`

Expected: no lint failures.

- [ ] **Step 4: Commit**

Run:

```bash
git add src/citeproof/evals/draft.py src/citeproof/cli.py tests/test_draft_eval.py \
  docs/evaluation.md README.md reports/hallucination_bib_gated_details.json
git commit -m "feat: add draft eval diagnostics"
```

- [ ] **Step 5: Push and check CI**

Run:

```bash
git push origin main
gh run list --branch main --limit 1
gh run watch <latest-run-id> --exit-status
```

Expected: pushed commit is on `origin/main`; CI passes.
