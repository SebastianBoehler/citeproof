# Clinical Effect Slots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block high-overlap false support for clinical/effect slots and trainable-scope claims.

**Architecture:** Add one deterministic clinical lens for structured biomedical slots and extend the existing technical-property lens for trainable scope. Wire both through the existing hard-conflict pipeline before lexical support.

**Tech Stack:** Python stdlib regex/dataclasses/Decimal, existing fact-lens pipeline, pytest, ruff, uv.

---

## File Structure

- Create `src/citeproof/clinical_lens.py`: exact effect values, adjustment status, population, endpoint windows, trial design.
- Modify `src/citeproof/fact_lenses.py`: call the clinical hard-conflict lens.
- Modify `src/citeproof/adjudicator.py`: route new clinical findings to stable failure modes.
- Modify `src/citeproof/technical_property_lens.py`: add trainable-scope conflict values.
- Create `tests/test_clinical_effect_slots.py`: focused regression tests.
- Modify `examples/edge_cases/claim_support.jsonl`: add six cases.
- Modify `docs/evaluation.md`: update totals and coverage text.

### Task 1: Failing Regression Tests

- [ ] **Step 1: Add tests**

```python
from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label


def test_exact_hazard_ratio_conflict_is_numeric() -> None:
    judgment = adjudicate_evidence(
        "Treatment reduced mortality with a hazard ratio of 0.72.",
        "Treatment reduced mortality with a hazard ratio of 0.95.",
    )
    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_adjusted_unadjusted_estimate_conflict() -> None:
    judgment = adjudicate_evidence(
        "The study reports an adjusted odds ratio for mortality.",
        "The study reports an unadjusted odds ratio for mortality.",
    )
    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_population_and_endpoint_window_conflicts() -> None:
    cases = (
        ("The cohort included adults with sepsis.", "The cohort included children with sepsis.", FailureMode.ENTITY_CONFLICT),
        ("The trial reduced 30-day mortality.", "The trial reduced 90-day mortality.", FailureMode.NUMERIC_CONFLICT),
    )
    for claim, evidence, mode in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == mode


def test_trial_design_and_trainable_scope_conflicts() -> None:
    cases = (
        ("The study was a randomized phase II trial of DrugX.", "The study was a single-arm phase II trial of DrugX."),
        ("LoRA updates all model weights during fine-tuning.", "LoRA keeps pretrained model weights frozen and updates low-rank adapter weights during fine-tuning."),
    )
    for claim, evidence in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED


def test_matching_clinical_slots_remain_clean() -> None:
    result = inspect_facts(
        "The study reports an adjusted odds ratio for mortality.",
        "The study reports an adjusted odds ratio for mortality.",
    )
    assert result.label is None
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest tests/test_clinical_effect_slots.py -q`

### Task 2: Clinical Lens

- [ ] **Step 1: Implement `clinical_lens.py`**

Create small dataclasses for ratio values and endpoint windows. Implement
`inspect_clinical_conflicts(claim, evidence) -> tuple[str, ...]` with context
overlap checks for exact ratio value, adjustment status, population group,
endpoint window, and trial design conflicts.

- [ ] **Step 2: Integrate routing**

Import the clinical lens in `fact_lenses.py`. Map `exact effect value conflict`
and `endpoint window conflict` to `NUMERIC_CONFLICT`; map `adjustment status`,
`population group`, and `trial design` to `ENTITY_CONFLICT`.

### Task 3: Trainable Scope

- [ ] **Step 1: Extend technical properties**

Add a `Trainable scope` group with values for all model weights, adapter
weights, and frozen base/pretrained/model weights. Ensure frozen-base evidence
does not also count as all-weights evidence.

- [ ] **Step 2: Run focused tests**

Run: `uv run pytest tests/test_clinical_effect_slots.py -q`

### Task 4: Benchmark And Verification

- [ ] **Step 1: Add edge rows and docs**

Add six edge rows matching the focused probes. Increase the edge-case total by
six and list clinical effect slots plus trainable-scope conflicts in
`docs/evaluation.md`.

- [ ] **Step 2: Run gates**

```bash
uv run pytest tests/test_clinical_effect_slots.py -q
uv run pytest -q -p no:cacheprovider
uv run citeproof eval examples/edge_cases/claim_support.jsonl --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-suite examples/eval_suite.json
uv run ruff check --no-cache .
```

- [ ] **Step 3: Size, commit, push**

```bash
wc -l src/citeproof/clinical_lens.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py src/citeproof/technical_property_lens.py tests/test_clinical_effect_slots.py docs/superpowers/plans/2026-06-22-clinical-effect-slots.md
git add src/citeproof/clinical_lens.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py src/citeproof/technical_property_lens.py tests/test_clinical_effect_slots.py examples/edge_cases/claim_support.jsonl docs/evaluation.md
git commit -m "feat: detect clinical effect slot conflicts"
git push origin main
```

## Self-Review

- Spec coverage: all six current false-supported probes are represented.
- Scope: no model dependency, no broad fallback threshold change.
- Safety invariant: every new contradiction requires a controlled slot mismatch
  plus non-slot context overlap.
