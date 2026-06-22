# Ratio Effect Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect ratio-effect point-estimate and CI conflicts where the null value is `1`, preventing false support in hazard/odds/risk ratio claims.

**Architecture:** Add `src/citeproof/ratio_effect_lens.py` and call it from `statistical_lens.py` alongside p-value and confidence-interval checks. Keep failure-mode mapping numeric by extending `adjudicator._fact_failure_mode`.

**Tech Stack:** Python, pytest, ruff, CiteProof heuristic verifier.

---

### Task 1: Red Ratio-Effect Tests

**Files:**
- Modify: `tests/test_statistical_lens.py`
- Modify: `tests/test_entailment_statistical.py`

- [ ] **Step 1: Add failing lens tests**

```python
def test_detects_ratio_point_estimate_direction_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The treatment hazard ratio is below 1.",
        "The treatment hazard ratio was 1.20.",
    )

    assert any("Ratio effect conflict" in finding for finding in findings)


def test_detects_ratio_ci_null_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The odds ratio excludes the null value.",
        "The odds ratio was 0.82 with 95% CI [0.60, 1.12].",
    )

    assert any("Ratio effect conflict" in finding for finding in findings)
```

- [ ] **Step 2: Add failing adjudicator test**

```python
def test_ratio_effect_conflict_maps_to_numeric_failure() -> None:
    judgment = adjudicate_evidence(
        "The treatment hazard ratio is below 1.",
        "The treatment hazard ratio was 1.20.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT
```

- [ ] **Step 3: Verify red state**

Run:

```bash
uv run pytest tests/test_statistical_lens.py tests/test_entailment_statistical.py -q
```

Expected: new ratio tests fail.

### Task 2: Ratio Effect Lens

**Files:**
- Create: `src/citeproof/ratio_effect_lens.py`
- Modify: `src/citeproof/statistical_lens.py`
- Modify: `src/citeproof/adjudicator.py`

- [ ] **Step 1: Implement `inspect_ratio_effect_conflicts`**

Parse explicit ratio metric point estimates and CIs. Return findings beginning
with `Ratio effect conflict:` for incompatible below/above-one or
include/exclude-null relations.

- [ ] **Step 2: Wire statistical coordinator**

Import and call `inspect_ratio_effect_conflicts(claim, evidence, context_overlaps)`
from `statistical_lens.inspect_statistical_conflicts`.

- [ ] **Step 3: Map failure mode**

Map `ratio effect conflict` to `FailureMode.NUMERIC_CONFLICT` in
`adjudicator._fact_failure_mode`.

- [ ] **Step 4: Run focused tests**

```bash
uv run pytest tests/test_statistical_lens.py tests/test_entailment_statistical.py -q
uv run ruff check src/citeproof/ratio_effect_lens.py src/citeproof/statistical_lens.py
```

Expected: focused tests and lint pass.

### Task 3: Eval, Docs, And CI

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add edge benchmark rows**

Append two `contradicted` rows: one point-estimate direction conflict and one
ratio CI null conflict.

- [ ] **Step 2: Run full gate**

```bash
uv run pytest -q -p no:cacheprovider
uv run citeproof eval-suite examples/eval_suite.json
uv run ruff check --no-cache .
```

Expected: all tests pass, eval-suite passes, `false_supported_rate` remains
`0.0`, and all touched files remain below 300 LOC.

- [ ] **Step 3: Commit and push**

```bash
git add src/citeproof/ratio_effect_lens.py src/citeproof/statistical_lens.py \
  src/citeproof/adjudicator.py tests/test_statistical_lens.py \
  tests/test_entailment_statistical.py examples/edge_cases/claim_support.jsonl \
  docs/evaluation.md
git commit -m "feat: detect ratio effect conflicts"
git push origin main
```
