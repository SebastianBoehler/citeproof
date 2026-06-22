# Numeric Quantity Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize compact and spelled academic quantities so numeric contradictions cannot pass as supported.

**Architecture:** Add a small shared `quantities.py` parser and integrate it into fact lenses and entailment. Keep the parser deterministic and conservative; do not add dependencies or model calls.

**Tech Stack:** Python stdlib regex/dataclasses, existing pytest, existing eval runner.

---

## File Structure

- Create `src/citeproof/quantities.py`: shared quantity mention parser.
- Create `tests/test_quantities.py`: direct parser tests.
- Modify `src/citeproof/fact_lenses.py`: use shared quantity parser for numeric/unit conflicts.
- Modify `src/citeproof/entailment.py`: use shared quantity parser for single-number conflict and remove duplicate number regex/function.
- Modify `tests/test_fact_lenses.py`: add compact/spelled numeric conflict tests.
- Modify `tests/test_entailment.py`: add one compact-number contradiction test if file stays under 300; otherwise create `tests/test_entailment_quantities.py`.
- Modify `examples/edge_cases/claim_support.jsonl`, `tests/test_eval_runner.py`, and `docs/evaluation.md`: add compact-number edge case and update count.

## Task 1: Shared Quantity Parser

**Files:**
- Create: `src/citeproof/quantities.py`
- Create: `tests/test_quantities.py`

- [ ] **Step 1: Add parser tests**

Create `tests/test_quantities.py`:

```python
from citeproof.quantities import quantity_units


def test_quantity_units_normalizes_compact_suffixes() -> None:
    quantities = quantity_units("Schema-Guided Dialogue contains over 16k dialogues.")

    assert quantities == {"dialogue": ("16000",)}


def test_quantity_units_normalizes_scale_words() -> None:
    quantities = quantity_units("WildChat contains 1 million conversations.")

    assert quantities == {"conversation": ("1000000",)}


def test_quantity_units_normalizes_spelled_small_numbers() -> None:
    quantities = quantity_units("The model was trained on four GPUs.")

    assert quantities == {"gpu": ("4",)}


def test_quantity_units_normalizes_two_word_numbers() -> None:
    quantities = quantity_units("The evaluation used forty two examples.")

    assert quantities == {"example": ("42",)}
```

- [ ] **Step 2: Verify parser tests fail**

Run:

```bash
python -m pytest tests/test_quantities.py -q -p no:cacheprovider
```

Expected: fails because `citeproof.quantities` does not exist.

- [ ] **Step 3: Implement parser**

Implement:

- frozen dataclass `QuantityMention(number: str, unit: str, text: str)`;
- `quantity_units(text: str) -> dict[str, tuple[str, ...]]`;
- `numbers_to_units(text: str) -> dict[str, set[str]]`;
- digit/suffix/scale-word and spelled-number extraction;
- unit normalization matching current fact-lens units.

- [ ] **Step 4: Verify Task 1**

Run:

```bash
python -m pytest tests/test_quantities.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/quantities.py tests/test_quantities.py
git diff --check
wc -l src/citeproof/quantities.py tests/test_quantities.py
```

Expected: parser tests pass, lint passes, files stay below 300 lines.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/citeproof/quantities.py tests/test_quantities.py
git commit -m "feat: parse normalized quantities"
```

## Task 2: Fact Lens And Entailment Integration

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Modify: `src/citeproof/entailment.py`
- Modify: `tests/test_fact_lenses.py`
- Create or modify: `tests/test_entailment_quantities.py` if `tests/test_entailment.py` would exceed 300 lines.

- [ ] **Step 1: Add failing behavior tests**

Add fact-lens tests:

```python
def test_detects_compact_number_conflict() -> None:
    result = inspect_facts(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 15,000 task-oriented dialogues.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Numeric conflict" in finding for finding in result.findings)


def test_compact_and_scale_word_numbers_match() -> None:
    result = inspect_facts(
        "WildChat contains 1M conversations.",
        "WildChat contains 1 million conversations.",
    )

    assert result.label is None


def test_spelled_gpu_numbers_match() -> None:
    result = inspect_facts(
        "The model was trained on 4 GPUs.",
        "The model was trained on four GPUs.",
    )

    assert result.label is None


def test_detects_spelled_number_conflict() -> None:
    result = inspect_facts(
        "The model was trained on 4 GPUs.",
        "The model was trained on three GPUs.",
    )

    assert result.label == Label.CONTRADICTED
```

Add an entailment test in `tests/test_entailment_quantities.py`:

```python
from citeproof.entailment import judge_evidence
from citeproof.models import Label


def test_compact_number_conflict_is_not_supported() -> None:
    judgment = judge_evidence(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 15,000 task-oriented dialogues.",
    )

    assert judgment.label == Label.CONTRADICTED
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_fact_lenses.py tests/test_entailment_quantities.py -q -p no:cacheprovider
```

Expected: compact-number conflict tests fail before integration.

- [ ] **Step 3: Integrate shared parser**

Modify `fact_lenses.py`:

- import `QuantityMention`, `numbers_to_units`, and `quantity_units`;
- replace local `_NumberMention`, `NUMBER_UNIT_RE`, `_number_units`, `_numbers_to_units`, `_normalize_unit`, and `_normalize_number`;
- preserve finding text by using `QuantityMention.text`.

Modify `entailment.py`:

- import `quantity_mentions`;
- replace `_number_mentions()` with shared parser output;
- remove local number regexes and helper if no longer used.

- [ ] **Step 4: Verify Task 2**

Run:

```bash
python -m pytest tests/test_quantities.py tests/test_fact_lenses.py tests/test_entailment_quantities.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/quantities.py src/citeproof/fact_lenses.py src/citeproof/entailment.py tests/test_quantities.py tests/test_fact_lenses.py tests/test_entailment_quantities.py
git diff --check
wc -l src/citeproof/quantities.py src/citeproof/fact_lenses.py src/citeproof/entailment.py tests/test_fact_lenses.py tests/test_entailment_quantities.py
```

Expected: tests pass, lint passes, `entailment.py` stays below 300 lines.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/citeproof/fact_lenses.py src/citeproof/entailment.py tests/test_fact_lenses.py tests/test_entailment_quantities.py
git commit -m "fix: detect compact quantity conflicts"
```

## Task 3: Eval Coverage And Final Verification

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add edge case**

Append:

```json
{"id":"compact-number-conflict","claim":"Schema-Guided Dialogue contains over 16k task-oriented dialogues.","evidence":"Schema-Guided Dialogue contains 15,000 task-oriented dialogues.","expected_label":"contradicted","expected_failure_mode":"numeric_conflict"}
```

- [ ] **Step 2: Update eval assertion**

Add `compact-number-conflict` to the expected failure-mode IDs in `tests/test_eval_runner.py`.

- [ ] **Step 3: Update docs**

Change the edge-case total from 24 to 25 in `docs/evaluation.md` and add compact quantity conflicts to the coverage sentence.

- [ ] **Step 4: Full verification**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_quantity_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output /tmp/citeproof_quantity_hallucination.json
git diff --check
```

Expected: all tests and evals pass, edge eval total 25, false-supported rate 0.0.

- [ ] **Step 5: Commit Task 3**

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add compact quantity edge case"
```
