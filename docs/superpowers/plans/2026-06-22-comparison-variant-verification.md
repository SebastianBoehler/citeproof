# Comparison Variant Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Catch common reversed benchmark-comparison wording variants without increasing false contradictions across contexts or dimensions.

**Architecture:** Extend the existing comparison lens relation metadata and regex, then add one edge benchmark row plus documentation updates. Keep all behavior deterministic and dependency-free.

**Tech Stack:** Python 3.11+, regex helpers, pytest, existing JSONL eval harness.

---

## Task 1: Comparison Variant Lens

**Files:**
- Modify: `src/citeproof/comparison_lens.py`
- Test: `tests/test_fact_lenses.py`
- Test: `tests/test_entailment.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_fact_lenses.py`:

```python
def test_detects_reversed_beats_comparison() -> None:
    result = inspect_facts(
        "LoRA beats Prefix Tuning on GLUE.",
        "Prefix Tuning beats LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Comparison direction conflict" in finding for finding in result.findings)


def test_detects_reversed_exceeds_comparison() -> None:
    result = inspect_facts(
        "LoRA exceeds Prefix Tuning on GLUE.",
        "Prefix Tuning exceeds LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED


def test_detects_reversed_outperformed_comparison() -> None:
    result = inspect_facts(
        "LoRA outperformed Prefix Tuning on GLUE.",
        "Prefix Tuning outperformed LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED


def test_detects_reversed_achieves_higher_accuracy_comparison() -> None:
    result = inspect_facts(
        "LoRA achieves higher accuracy than Prefix Tuning on GLUE.",
        "Prefix Tuning achieves higher accuracy than LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED


def test_detects_reversed_lower_error_comparison() -> None:
    result = inspect_facts(
        "LoRA has lower error than Prefix Tuning on GLUE.",
        "Prefix Tuning has lower error than LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED


def test_lower_error_context_mismatch_is_partial_support() -> None:
    result = inspect_facts(
        "LoRA has lower error than Prefix Tuning on GLUE.",
        "Prefix Tuning has lower error than LoRA on SQuAD.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Comparison context mismatch" in finding for finding in result.findings)
```

Append to `tests/test_entailment.py`:

```python
def test_reversed_beats_comparison_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA beats Prefix Tuning on GLUE.",
        "Prefix Tuning beats LoRA on GLUE.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_lower_error_context_mismatch_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA has lower error than Prefix Tuning on GLUE.",
        "Prefix Tuning has lower error than LoRA on SQuAD.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
```

- [ ] **Step 2: Run red tests**

Run:

```bash
uv run pytest tests/test_fact_lenses.py::test_detects_reversed_beats_comparison \
  tests/test_fact_lenses.py::test_detects_reversed_exceeds_comparison \
  tests/test_fact_lenses.py::test_detects_reversed_outperformed_comparison \
  tests/test_fact_lenses.py::test_detects_reversed_achieves_higher_accuracy_comparison \
  tests/test_fact_lenses.py::test_detects_reversed_lower_error_comparison \
  tests/test_fact_lenses.py::test_lower_error_context_mismatch_is_partial_support \
  tests/test_entailment.py::test_reversed_beats_comparison_is_not_supported \
  tests/test_entailment.py::test_lower_error_context_mismatch_is_not_supported -v
```

Expected: variant tests fail because current comparison lens does not parse the
new phrases.

- [ ] **Step 3: Implement relation metadata**

In `src/citeproof/comparison_lens.py`, replace the flat relation map with a
small relation metadata dataclass:

```python
@dataclass(frozen=True)
class _RelationSpec:
    family: str
    dimension: str
```

Update `COMPARISON_RE` to include:

- `beats`
- `exceeds`
- `outperformed`
- `achieves higher accuracy than`
- `has lower error than`

Use relation values such as:

```python
COMPARISON_RELATIONS = {
    "beats": _RelationSpec("higher_is_better", "generic"),
    "outperforms": _RelationSpec("higher_is_better", "generic"),
    "outperformed": _RelationSpec("higher_is_better", "generic"),
    "exceeds": _RelationSpec("higher_is_better", "generic"),
    "is better than": _RelationSpec("higher_is_better", "generic"),
    "is superior to": _RelationSpec("higher_is_better", "generic"),
    "has higher accuracy than": _RelationSpec("higher_is_better", "accuracy"),
    "achieves higher accuracy than": _RelationSpec("higher_is_better", "accuracy"),
    "has lower error than": _RelationSpec("lower_is_better", "error"),
}
```

Store a normalized relation key on `_Comparison` such as
`relation: _RelationSpec`. Dimension/family equality should be required before
direction conflict. Dimension mismatch should remain partial support.

- [ ] **Step 4: Run green tests**

Run:

```bash
uv run pytest tests/test_fact_lenses.py tests/test_entailment.py -v
uv run pytest -q
uv run ruff check .
wc -l src/citeproof/comparison_lens.py tests/test_fact_lenses.py tests/test_entailment.py
git diff --check
```

Expected: tests pass, ruff passes, files remain under 300 LOC.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add src/citeproof/comparison_lens.py tests/test_fact_lenses.py tests/test_entailment.py
git commit -m "feat: detect comparison wording variants"
```

## Task 2: Edge Eval And Docs

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `README.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add edge row and eval assertion**

Append:

```json
{"id":"comparison-beats-swap","claim":"LoRA beats Prefix Tuning on GLUE.","evidence":"Prefix Tuning beats LoRA on GLUE.","expected_label":"contradicted","expected_failure_mode":"comparison_direction_conflict"}
```

Update `tests/test_eval_runner.py::test_edge_cases_with_expected_failure_modes_pass`
to include `comparison-beats-swap`.

- [ ] **Step 2: Update docs**

- `README.md`: mention comparison wording variants in the deterministic
  fact-lens bullet only if it still reads cleanly.
- `docs/evaluation.md`: update edge benchmark total from `21` to `22` and add
  comparison wording variants to the coverage sentence.

- [ ] **Step 3: Run full verification**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output reports/hallucination_bib_gated_details.json
git diff --check
```

Expected: edge eval total `22`, accuracy `1.0`, false-supported rate `0.0`.

- [ ] **Step 4: Commit Task 2**

Run:

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py README.md docs/evaluation.md
git commit -m "test: add comparison wording adversary"
```

## Final Verification And Merge

- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run ruff check .`.
- [ ] Merge branch into `main`.
- [ ] Push `main`.
- [ ] Watch GitHub Actions for the merge commit.
