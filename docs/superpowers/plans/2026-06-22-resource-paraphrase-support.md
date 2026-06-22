# Resource Paraphrase Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add conservative deterministic support for training-time and sample-efficiency paraphrases.

**Architecture:** Extend the existing semantic-support branch in `src/citeproof/entailment.py`. Keep retrieval, source loading, fact lenses, adjudication, and optional NLI unchanged so the final verifier remains conservative.

**Tech Stack:** Python stdlib regex, existing `pytest`, existing JSONL eval runner.

---

## File Structure

- Modify `src/citeproof/entailment.py`: add narrow helper predicates for affirmative resource reduction and negated resource reduction, called from `_has_semantic_support()`.
- Modify `tests/test_entailment.py`: add direct tests for the two supported paraphrases and one negated non-support case.
- Modify `examples/edge_cases/claim_support.jsonl`: add two supported edge rows.
- Modify `tests/test_eval_runner.py`: add the two edge row IDs to the expected ID set.
- Modify `docs/evaluation.md`: update the edge-case count from 22 to 24 and mention resource-efficiency paraphrases.

## Task 1: Entailment Lens

**Files:**
- Modify: `src/citeproof/entailment.py`
- Modify: `tests/test_entailment.py`

- [ ] **Step 1: Write failing tests**

Add these tests to `tests/test_entailment.py`:

```python
def test_training_time_fewer_hours_paraphrase_support() -> None:
    judgment = judge_evidence(
        "Method X reduces training time.",
        "Method X required fewer training hours than the baseline.",
    )

    assert judgment.label == Label.SUPPORTED


def test_sample_efficiency_fewer_interactions_paraphrase_support() -> None:
    judgment = judge_evidence(
        "Method X improves sample efficiency.",
        "Method X reaches the target success rate with fewer environment interactions.",
    )

    assert judgment.label == Label.SUPPORTED


def test_negated_resource_reduction_is_not_supported() -> None:
    judgment = judge_evidence(
        "Method X improves sample efficiency.",
        "Method X does not require fewer environment interactions than the baseline.",
    )

    assert judgment.label != Label.SUPPORTED
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_entailment.py::test_training_time_fewer_hours_paraphrase_support tests/test_entailment.py::test_sample_efficiency_fewer_interactions_paraphrase_support tests/test_entailment.py::test_negated_resource_reduction_is_not_supported -q -p no:cacheprovider
```

Expected: the first two fail as `partially_supported`; the negated case must already be non-supported or fail until the guard exists.

- [ ] **Step 3: Implement narrow predicates**

In `src/citeproof/entailment.py`, add regex helpers for:

- reduction claims: `reduce`, `reduces`, `reduced`, `lower`, `lowers`, `decrease`, `decreases`;
- affirmative evidence: `fewer`, `less`, `reduced`, `half as many` near time/sample units;
- negated evidence: `does not`, `did not`, `failed to`, `no reduction`, or `without` near the same resource terms.

Call these helpers from `_has_semantic_support()` before the existing BERTScore/language branches.

- [ ] **Step 4: Verify Task 1**

Run:

```bash
python -m pytest tests/test_entailment.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/entailment.py tests/test_entailment.py
git diff --check
wc -l src/citeproof/entailment.py tests/test_entailment.py
```

Expected: all tests pass, lint passes, no whitespace errors, both files stay below 300 lines.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/citeproof/entailment.py tests/test_entailment.py
git commit -m "feat: support resource paraphrase entailment"
```

## Task 2: Evaluation Coverage

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add edge rows**

Append these JSONL rows:

```json
{"id":"training-time-fewer-hours-support","claim":"Method X reduces training time.","evidence":"Method X required fewer training hours than the baseline.","expected_label":"supported"}
{"id":"sample-efficiency-fewer-interactions-support","claim":"Method X improves sample efficiency.","evidence":"Method X reaches the target success rate with fewer environment interactions.","expected_label":"supported"}
```

- [ ] **Step 2: Update eval ID assertion**

Add both IDs to the expected ID set in `tests/test_eval_runner.py`.

- [ ] **Step 3: Update docs**

In `docs/evaluation.md`, change the edge benchmark total from 22 to 24 and add `resource-efficiency paraphrases` to the coverage sentence.

- [ ] **Step 4: Verify Task 2**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_resource_edge_cases.json
git diff --check
wc -l src/citeproof/entailment.py tests/test_entailment.py tests/test_eval_runner.py docs/evaluation.md
```

Expected: tests and lint pass; edge eval reports total 24, accuracy 1.0, false-supported rate 0.0; changed files stay below 300 lines.

- [ ] **Step 5: Commit Task 2**

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add resource paraphrase edge cases"
```

## Final Verification

Run before merge:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_resource_edge_cases_final.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output /tmp/citeproof_resource_hallucination_final.json
git diff --check
```

Expected: no false-supported cases and no file over 300 lines except existing plan/spec files where explicitly allowed.
