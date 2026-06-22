# Protocol Slot Conflicts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent high-overlap academic protocol-slot swaps from being labeled `supported`.

**Architecture:** Reuse CiteProof's deterministic fact-lens pipeline. Extend quantity parsing for duration/dose units and extend the existing protocol lens with comparator and dosing-frequency slots, so contradictions are explainable and still outrank support.

**Tech Stack:** Python stdlib regex/dataclasses/Decimal, existing `adjudicator`, `fact_lenses`, pytest, ruff, uv.

---

## File Structure

- Modify `src/citeproof/quantities.py`: add controlled duration and dose units.
- Modify `src/citeproof/protocol_lens.py`: add protocol groups for comparator/control and dosing frequency.
- Modify `src/citeproof/adjudicator.py`: route protocol-frequency conflicts to `entity_conflict`.
- Create `tests/test_protocol_slot_conflicts.py`: focused adjudicator and lens regression tests.
- Modify `tests/test_quantities.py`: parser coverage for duration and dose units.
- Modify `examples/edge_cases/claim_support.jsonl`: benchmark rows for the new false-supported cases.
- Modify `docs/evaluation.md`: benchmark total and coverage text.

### Task 1: Quantity Duration And Dose Units

**Files:**
- Modify: `src/citeproof/quantities.py`
- Modify: `tests/test_quantities.py`

- [ ] **Step 1: Add failing parser tests**

```python
def test_quantity_units_recognizes_duration_units() -> None:
    quantities = quantity_units("The study measured mortality at 30 days and 6 months.")
    assert quantities["day"] == (Decimal("30"),)
    assert quantities["month"] == (Decimal("6"),)


def test_quantity_units_recognizes_dose_units() -> None:
    quantities = quantity_units("Patients received 10 mg and 2 doses.")
    assert quantities["mg"] == (Decimal("10"),)
    assert quantities["dose"] == (Decimal("2"),)
```

- [ ] **Step 2: Run focused tests and observe failure**

Run: `uv run pytest tests/test_quantities.py::test_quantity_units_recognizes_duration_units tests/test_quantities.py::test_quantity_units_recognizes_dose_units -q`

- [ ] **Step 3: Extend `_WORD_UNIT` and normalization**

Add `days?`, `weeks?`, `months?`, `years?`, `hours?`, `minutes?`, `seconds?`, `mg`, `g`, `kg`, `ml`, and `doses?` to `_WORD_UNIT`. Keep `_normalize_unit` using plural stripping, except preserve short units such as `mg`, `kg`, `ml`, and `g`.

- [ ] **Step 4: Verify focused tests pass**

Run: `uv run pytest tests/test_quantities.py -q`

### Task 2: Protocol Slot Lens

**Files:**
- Modify: `src/citeproof/protocol_lens.py`
- Modify: `src/citeproof/adjudicator.py`
- Create: `tests/test_protocol_slot_conflicts.py`

- [ ] **Step 1: Add failing contradiction tests**

```python
from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label


def test_comparator_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The trial compared the intervention with placebo.",
        "The trial compared the intervention with usual care.",
    )
    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_dosing_frequency_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "Patients received the drug daily.",
        "Patients received the drug weekly.",
    )
    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_duration_and_dose_quantity_conflicts_are_numeric() -> None:
    for claim, evidence in (
        ("The study measured mortality at 30 days.", "The study measured mortality at 90 days."),
        ("Patients received 10 mg of the drug.", "Patients received 20 mg of the drug."),
    ):
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_matching_protocol_slots_remain_clean() -> None:
    result = inspect_facts(
        "The trial compared the intervention with placebo.",
        "The trial compared the intervention with placebo.",
    )
    assert result.label is None
```

- [ ] **Step 2: Run focused tests and observe failure**

Run: `uv run pytest tests/test_protocol_slot_conflicts.py -q`

- [ ] **Step 3: Extend protocol groups**

Add `Comparator/control` and `Dosing frequency` to `CONFLICT_GROUPS`, update `VALUE_TERMS_RE`, and normalize overlapping terms so `usual care` and `standard care` count as the same value.

- [ ] **Step 4: Route failure mode**

In `_fact_failure_mode`, map `protocol conflict` findings to `FailureMode.ENTITY_CONFLICT`.

- [ ] **Step 5: Verify focused tests pass**

Run: `uv run pytest tests/test_protocol_slot_conflicts.py tests/test_quantities.py -q`

### Task 3: Benchmark And Docs

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add edge rows**

Add four rows: comparator conflict, dosing-frequency conflict, follow-up duration conflict, and dose amount conflict. Expected labels are `contradicted`; expected failure modes are `entity_conflict` for protocol slots and `numeric_conflict` for quantities.

- [ ] **Step 2: Update docs**

Increase the edge-case total by four and add protocol-slot conflicts to the covered-case list.

- [ ] **Step 3: Run edge eval**

Run: `uv run citeproof eval examples/edge_cases/claim_support.jsonl --details-output reports/edge_cases_heuristic.json`

### Task 4: Verification And Commit

**Files:**
- All touched files above

- [ ] **Step 1: Run focused and full gates**

Run:

```bash
uv run pytest tests/test_quantities.py tests/test_protocol_slot_conflicts.py -q
uv run pytest -q -p no:cacheprovider
uv run citeproof eval-suite examples/eval_suite.json
uv run ruff check --no-cache .
```

- [ ] **Step 2: Check file sizes**

Run: `find src/citeproof tests docs/superpowers -type f | xargs wc -l | sort -nr | head -40`

- [ ] **Step 3: Commit and push**

Run:

```bash
git add src/citeproof/quantities.py src/citeproof/protocol_lens.py src/citeproof/adjudicator.py tests/test_quantities.py tests/test_protocol_slot_conflicts.py examples/edge_cases/claim_support.jsonl docs/evaluation.md
git commit -m "feat: detect protocol slot conflicts"
git push origin main
```

## Self-Review

- Spec coverage: duration/dose quantity conflicts and comparator/frequency protocol conflicts are covered.
- Scope: no broad biomedical parser, no new model dependency, no configurable fallback.
- Safety invariant: the new checks require controlled slot terms and existing context overlap.
