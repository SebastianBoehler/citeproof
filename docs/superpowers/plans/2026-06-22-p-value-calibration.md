# P-Value Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic p-value conflict detection so incompatible p-value relations and significance wording cannot be labeled `supported`.

**Architecture:** Extend `src/citeproof/statistical_lens.py` with p-value parsing and comparison. Map p-value findings to `numeric_conflict` in `adjudicator`, then add unit and eval coverage.

**Tech Stack:** Python, pytest, ruff, CiteProof heuristic verifier.

---

### Task 1: P-Value Lens Tests

**Files:**
- Modify: `tests/test_statistical_lens.py`

- [ ] **Step 1: Add failing tests**

```python
def test_detects_explicit_p_value_threshold_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The model improvement has p < 0.05.",
        "The model improvement has p = 0.08.",
    )

    assert any("P-value conflict" in finding for finding in findings)


def test_detects_significance_wording_p_value_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The model improvement is statistically significant.",
        "The model improvement has p = 0.08.",
    )

    assert any("P-value conflict" in finding for finding in findings)


def test_ignores_matching_significant_p_value() -> None:
    findings = inspect_statistical_conflicts(
        "The model improvement is statistically significant.",
        "The model improvement has p = 0.01.",
    )

    assert not any("P-value conflict" in finding for finding in findings)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_statistical_lens.py -q
```

Expected: new p-value tests fail before implementation.

### Task 2: P-Value Parser And Adjudication

**Files:**
- Modify: `src/citeproof/statistical_lens.py`
- Modify: `src/citeproof/adjudicator.py`
- Test: `tests/test_entailment_statistical.py`

- [ ] **Step 1: Implement p-value parsing**

Add a small internal `PValueClaim` dataclass with `threshold`, `relation`, and
`text`, parse explicit p-value forms, and add conventional significance-wording
claims when explicit p-values are absent.

- [ ] **Step 2: Compare relations**

Return `P-value conflict: ...` when claim-side and evidence-side p-value
relations are incompatible. Keep context-overlap gating consistent with other
statistical groups.

- [ ] **Step 3: Map failure mode**

In `adjudicator._fact_failure_mode`, map `p-value conflict` to
`FailureMode.NUMERIC_CONFLICT`.

- [ ] **Step 4: Add adjudicator tests**

```python
def test_p_value_conflict_maps_to_numeric_failure() -> None:
    judgment = adjudicate_evidence(
        "The model improvement has p < 0.05.",
        "The model improvement has p = 0.08.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT
```

### Task 3: Eval And Gate

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add edge benchmark rows**

Append two `contradicted` rows: one explicit `p < 0.05` versus `p = 0.08`, and
one significant wording versus `p = 0.08`.

- [ ] **Step 2: Run full gate**

```bash
uv run pytest -q -p no:cacheprovider
uv run citeproof eval-suite examples/eval_suite.json
uv run ruff check --no-cache .
```

Expected: all tests pass, eval-suite passes, false-supported rate remains `0.0`.

- [ ] **Step 3: Commit and push**

```bash
git add src/citeproof/statistical_lens.py src/citeproof/adjudicator.py \
  tests/test_statistical_lens.py tests/test_entailment_statistical.py \
  examples/edge_cases/claim_support.jsonl docs/evaluation.md
git commit -m "feat: detect p-value conflicts"
git push origin main
```
