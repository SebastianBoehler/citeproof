# Academic Count Quantities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recognize common academic study-count units so patient/participant/study count mismatches become numeric conflicts instead of false support.

**Architecture:** Extend the existing deterministic quantity parser in `quantities.py`. The existing fact-lens numeric-conflict path will then catch mismatches without a new verifier layer.

**Tech Stack:** Python, pytest, ruff, CiteProof heuristic verifier.

---

### Task 1: Red Academic Count Tests

**Files:**
- Modify: `tests/test_quantities.py`
- Create: `tests/test_academic_count_quantities.py`

- [ ] **Step 1: Add parser tests**

```python
def test_quantity_units_recognizes_academic_count_units() -> None:
    quantities = quantity_units(
        "The study enrolled 100 patients, 12 sites, and 4 treatment arms."
    )

    assert quantities == {
        "patient": (Decimal("100"),),
        "site": (Decimal("12"),),
        "arm": (Decimal("4"),),
    }
```

- [ ] **Step 2: Add fact and adjudicator tests**

```python
def test_patient_count_conflict_is_numeric_conflict() -> None:
    result = inspect_facts(
        "The study enrolled 100 patients.",
        "The study enrolled 120 patients.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Numeric conflict" in finding for finding in result.findings)


def test_patient_count_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The study enrolled 100 patients.",
        "The study enrolled 120 patients.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT
```

- [ ] **Step 3: Verify red state**

Run:

```bash
uv run pytest tests/test_quantities.py tests/test_academic_count_quantities.py -q
```

Expected: new tests fail before the parser recognizes the units.

### Task 2: Quantity Parser Extension

**Files:**
- Modify: `src/citeproof/quantities.py`
- Test: `tests/test_quantities.py`
- Test: `tests/test_academic_count_quantities.py`

- [ ] **Step 1: Extend `_WORD_UNIT`**

Add the academic count units from the design to `_WORD_UNIT`. Keep plural
handling through the existing `_normalize_unit` path.

- [ ] **Step 2: Handle `centres` spelling**

Normalize `centres` to `centre` and `centers` to `center` through the existing
`rstrip("s")` behavior; no cross-spelling equivalence is required in this slice.

- [ ] **Step 3: Run focused tests**

```bash
uv run pytest tests/test_quantities.py tests/test_academic_count_quantities.py -q
uv run ruff check src/citeproof/quantities.py tests/test_quantities.py tests/test_academic_count_quantities.py
```

Expected: focused tests and lint pass.

### Task 3: Eval, Docs, And CI

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add edge benchmark rows**

Append two `contradicted` rows for patient and participant count mismatches,
both with `expected_failure_mode` set to `numeric_conflict`.

- [ ] **Step 2: Run full gate**

```bash
uv run pytest -q -p no:cacheprovider
uv run citeproof eval-suite examples/eval_suite.json
uv run ruff check --no-cache .
```

Expected: all tests pass, eval-suite passes, `false_supported_rate` remains
`0.0`, and touched files remain below 300 LOC.

- [ ] **Step 3: Commit and push**

```bash
git add src/citeproof/quantities.py tests/test_quantities.py \
  tests/test_academic_count_quantities.py examples/edge_cases/claim_support.jsonl \
  docs/evaluation.md
git commit -m "feat: detect academic count conflicts"
git push origin main
```
