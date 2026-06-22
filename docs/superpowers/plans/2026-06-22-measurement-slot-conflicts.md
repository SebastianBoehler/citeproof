# Measurement Slot Conflicts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block high-overlap false support for CS/ML metric values, compact quantities, and versioned benchmark names.

**Architecture:** Extend shared quantity parsing for compact B-scale quantities, add one deterministic measurement lens for metric scalar and versioned benchmark conflicts, and wire it into the hard-conflict pipeline.

**Tech Stack:** Python stdlib regex/dataclasses/Decimal, existing fact-lens pipeline, pytest, ruff, uv.

---

## File Structure

- Modify `src/citeproof/quantities.py`: add B scale plus parameters/tokens/context units.
- Create `src/citeproof/measurement_lens.py`: metric scalar and benchmark-version conflicts.
- Modify `src/citeproof/fact_lenses.py`: call the new lens.
- Modify `src/citeproof/adjudicator.py`: route measurement findings to stable modes.
- Modify `tests/test_quantities.py`: compact billion/unit parser tests.
- Create `tests/test_measurement_slot_conflicts.py`: focused regression tests.
- Modify `examples/edge_cases/claim_support.jsonl`: add five rows.
- Modify `docs/evaluation.md`: update totals and coverage text.

### Task 1: Quantity Parser Expansion

- [ ] **Step 1: Add parser tests**

```python
def test_quantity_units_normalizes_billion_suffix() -> None:
    quantities = quantity_units("The model has 7B parameters and a 32k token context.")
    assert quantities["parameter"] == (Decimal("7000000000"),)
    assert quantities["token"] == (Decimal("32000"),)
```

- [ ] **Step 2: Extend parser**

Add compact `b/B` to `_COMPACT_SCALE`, and add `parameters?`, `tokens?`, and
`contexts?` to `_WORD_UNIT`.

### Task 2: Measurement Lens

- [ ] **Step 1: Add focused tests**

```python
def test_metric_scalar_conflicts_are_numeric() -> None:
    cases = (
        ("The model achieved an accuracy of 0.92 on the test set.", "The model achieved an accuracy of 0.84 on the test set."),
        ("The model achieved an AUROC of 0.91 on the test set.", "The model achieved an AUROC of 0.82 on the test set."),
        ("The system achieved a BLEU score of 31.2 on WMT14.", "The system achieved a BLEU score of 27.4 on WMT14."),
    )
    for claim, evidence in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_quantity_and_benchmark_version_conflicts() -> None:
    cases = (
        ("The model has 7B parameters.", "The model has 13B parameters.", FailureMode.NUMERIC_CONFLICT),
        ("The context window is 32k tokens.", "The context window is 128k tokens.", FailureMode.NUMERIC_CONFLICT),
        ("The evaluation uses MMLU-Pro.", "The evaluation uses MMLU.", FailureMode.ENTITY_CONFLICT),
    )
    for claim, evidence, mode in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == mode
```

- [ ] **Step 2: Implement `measurement_lens.py`**

Create metric-value extraction for controlled metric names: accuracy, F1,
AUROC, AUPRC, BLEU, chrF, ROUGE, perplexity, loss. Create benchmark anchor
extraction for all-caps names with optional hyphen suffix. Require context
overlap before returning conflicts.

- [ ] **Step 3: Integrate and route**

Call `inspect_measurement_conflicts` from `fact_lenses.py`. Route `Metric value
conflict` to `NUMERIC_CONFLICT` and `Benchmark version conflict` to
`ENTITY_CONFLICT`.

### Task 3: Benchmark And Verification

- [ ] **Step 1: Add edge rows and docs**

Add five edge rows for metric scalar, BLEU score, parameter count, token count,
and benchmark version conflicts. Increase the edge total by five and list
measurement-slot conflicts in `docs/evaluation.md`.

- [ ] **Step 2: Run gates**

```bash
uv run pytest tests/test_quantities.py tests/test_measurement_slot_conflicts.py -q
uv run pytest -q -p no:cacheprovider
uv run citeproof eval examples/edge_cases/claim_support.jsonl --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-suite examples/eval_suite.json
uv run ruff check --no-cache .
```

- [ ] **Step 3: Size, commit, push**

```bash
wc -l src/citeproof/measurement_lens.py src/citeproof/quantities.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_measurement_slot_conflicts.py docs/superpowers/plans/2026-06-22-measurement-slot-conflicts.md
git add src/citeproof/measurement_lens.py src/citeproof/quantities.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_quantities.py tests/test_measurement_slot_conflicts.py examples/edge_cases/claim_support.jsonl docs/evaluation.md
git commit -m "feat: detect measurement slot conflicts"
git push origin main
```

## Self-Review

- Spec coverage: all current measurement false-supported probes are represented.
- Scope: no model dependency and no global fallback threshold change.
- Safety invariant: conflicts require controlled metric/unit/benchmark slots plus context overlap.
