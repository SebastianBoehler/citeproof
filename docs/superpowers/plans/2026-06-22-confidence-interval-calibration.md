# Confidence Interval Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect confidence-interval numeric range conflicts so CI/significance claims cannot be falsely supported by incompatible numeric intervals.

**Architecture:** Refactor p-value helpers from `statistical_lens.py` into `pvalue_lens.py`, add `confidence_interval_lens.py`, and keep `statistical_lens.py` as the coordinator that merges statistical conflict findings.

**Tech Stack:** Python, pytest, ruff, CiteProof heuristic verifier.

---

### Task 1: Modularize P-Value Helpers

**Files:**
- Create: `src/citeproof/pvalue_lens.py`
- Modify: `src/citeproof/statistical_lens.py`
- Test: `tests/test_statistical_lens.py`

- [ ] **Step 1: Move p-value code**

Move `PValueClaim`, p-value regexes, `_p_value_conflicts`, and helper functions
from `statistical_lens.py` into `pvalue_lens.py`, exposing:

```python
def inspect_p_value_conflicts(claim: str, evidence: str, context_overlaps: bool) -> tuple[str, ...]:
    ...
```

- [ ] **Step 2: Wire coordinator**

Import and call `inspect_p_value_conflicts` from `statistical_lens.py` before
the existing statistical group checks.

- [ ] **Step 3: Verify no behavior change**

Run:

```bash
uv run pytest tests/test_statistical_lens.py tests/test_entailment_statistical.py -q
```

Expected: all current p-value and statistical tests pass.

### Task 2: Numeric Confidence Interval Lens

**Files:**
- Create: `src/citeproof/confidence_interval_lens.py`
- Modify: `src/citeproof/statistical_lens.py`
- Test: `tests/test_statistical_lens.py`
- Test: `tests/test_entailment_statistical.py`

- [ ] **Step 1: Add failing tests**

```python
def test_detects_numeric_ci_includes_zero_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The confidence interval excludes zero.",
        "The 95% confidence interval was [-0.10, 0.30].",
    )

    assert any("Confidence interval numeric conflict" in finding for finding in findings)


def test_significance_conflicts_with_ci_including_zero() -> None:
    findings = inspect_statistical_conflicts(
        "The treatment effect is statistically significant.",
        "The 95% confidence interval was [-0.10, 0.30].",
    )

    assert any("Confidence interval numeric conflict" in finding for finding in findings)
```

- [ ] **Step 2: Implement CI parser**

Create a focused module that parses bracketed or parenthesized two-number
intervals only when the text near the interval contains `confidence interval`
or `CI`.

- [ ] **Step 3: Wire coordinator**

Import and call `inspect_confidence_interval_conflicts` in
`statistical_lens.py`.

- [ ] **Step 4: Verify focused tests**

Run:

```bash
uv run pytest tests/test_statistical_lens.py tests/test_entailment_statistical.py -q
```

Expected: all tests pass.

### Task 3: Eval, Docs, And CI

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add edge benchmark rows**

Append two `contradicted` rows for numeric CI conflicts: explicit excludes-zero
versus CI including zero, and significant wording versus CI including zero.

- [ ] **Step 2: Run full gate**

```bash
uv run pytest -q -p no:cacheprovider
uv run citeproof eval-suite examples/eval_suite.json
uv run ruff check --no-cache .
```

Expected: tests pass, eval-suite passes, `false_supported_rate` remains `0.0`,
and all touched source/test files remain below 300 LOC.

- [ ] **Step 3: Commit and push**

```bash
git add src/citeproof/pvalue_lens.py src/citeproof/confidence_interval_lens.py \
  src/citeproof/statistical_lens.py tests/test_statistical_lens.py \
  tests/test_entailment_statistical.py examples/edge_cases/claim_support.jsonl \
  docs/evaluation.md
git commit -m "feat: detect numeric confidence interval conflicts"
git push origin main
```
