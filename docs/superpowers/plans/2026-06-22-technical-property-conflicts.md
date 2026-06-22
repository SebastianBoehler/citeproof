# Technical Property Conflicts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic technical-property conflict detection so high-overlap technical condition swaps do not get labeled `supported`.

**Architecture:** Create a focused `technical_property_lens` module with controlled value groups and context-overlap checks. Integrate it into the existing `fact_lenses` hard-conflict path and map its findings through the existing `entity_conflict` failure mode.

**Tech Stack:** Python, pytest, ruff, existing CiteProof deterministic lens architecture.

---

## File Structure

- Create `src/citeproof/technical_property_lens.py`: controlled technical-property groups and `inspect_technical_property_conflicts`.
- Create `tests/test_technical_property_lens.py`: direct tests and conservative boundaries.
- Modify `src/citeproof/fact_lenses.py`: append technical property conflicts to hard findings.
- Modify `src/citeproof/adjudicator.py`: map technical property findings to `entity_conflict`.
- Create `tests/test_entailment_technical_properties.py`: end-to-end label and failure-mode tests.
- Modify `examples/edge_cases/claim_support.jsonl`: append six adversarial rows.
- Modify `tests/test_eval_runner.py`: require the six new failure-mode rows.
- Modify `docs/evaluation.md`: update benchmark total and coverage sentence.

## Task 1: Direct Technical Property Lens

**Files:**
- Create: `src/citeproof/technical_property_lens.py`
- Create: `tests/test_technical_property_lens.py`

- [ ] **Step 1: Add failing direct tests**

Create `tests/test_technical_property_lens.py`:

```python
from citeproof.technical_property_lens import inspect_technical_property_conflicts


def test_detects_complexity_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The algorithm runs in linear time.",
        "The algorithm runs in quadratic time.",
    )

    assert any("Complexity conflict" in finding for finding in findings)


def test_detects_inference_fidelity_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The method uses exact inference.",
        "The method uses approximate inference.",
    )

    assert any("Inference fidelity conflict" in finding for finding in findings)


def test_detects_trainability_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The encoder is frozen during training.",
        "The encoder is fine-tuned end-to-end during training.",
    )

    assert any("Trainability conflict" in finding for finding in findings)


def test_detects_reward_density_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The agent is trained with dense rewards.",
        "The agent is trained with sparse rewards.",
    )

    assert any("Reward density conflict" in finding for finding in findings)


def test_detects_evaluation_domain_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The model is evaluated on out-of-domain data.",
        "The model is evaluated on in-domain data.",
    )

    assert any("Evaluation domain conflict" in finding for finding in findings)


def test_detects_data_sensitivity_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The dataset contains private medical records.",
        "The dataset contains public medical records.",
    )

    assert any("Data sensitivity conflict" in finding for finding in findings)


def test_ignores_evidence_with_claim_value_plus_extra_value() -> None:
    findings = inspect_technical_property_conflicts(
        "The algorithm runs in linear time.",
        "The algorithm runs in linear time for sparse inputs and quadratic time otherwise.",
    )

    assert findings == ()


def test_ignores_property_terms_in_different_contexts() -> None:
    findings = inspect_technical_property_conflicts(
        "The linear probe is trained on the encoder.",
        "The decoder has quadratic time complexity.",
    )

    assert findings == ()
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_technical_property_lens.py -q -p no:cacheprovider`

Expected: FAIL because `citeproof.technical_property_lens` does not exist.

- [ ] **Step 3: Implement lens**

Create `src/citeproof/technical_property_lens.py` with:

```python
"""Controlled technical property conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class TechnicalPropertyGroup:
    label: str
    values: tuple[tuple[str, tuple[str, ...]], ...]


GROUPS = (
    TechnicalPropertyGroup(
        "Complexity",
        (
            ("constant", (r"\bconstant\s+time\b", r"\bo\\(1\\)\b")),
            ("logarithmic", (r"\blogarithmic\b", r"\bo\\(log\\s*n\\)\b")),
            ("linear", (r"\blinear\s+(?:time|complexity)\\b", r"\bo\\(n\\)\b")),
            ("quadratic", (r"\bquadratic\s+(?:time|complexity)\\b", r"\bo\\(n\\^?2\\)\b")),
            ("cubic", (r"\bcubic\s+(?:time|complexity)\\b", r"\bo\\(n\\^?3\\)\b")),
            ("exponential", (r"\bexponential\s+(?:time|complexity)\\b", r"\bo\\(2\\^n\\)\b")),
        ),
    ),
    TechnicalPropertyGroup(
        "Inference fidelity",
        (
            ("exact", (r"\bexact\s+inference\b",)),
            ("approximate", (r"\bapproximate\s+inference\b", r"\bapproximation\b")),
        ),
    ),
    TechnicalPropertyGroup(
        "Trainability",
        (
            ("frozen", (r"\bfrozen\b", r"\bkept\s+fixed\b")),
            ("fine-tuned", (r"\bfine[- ]tuned\b", r"\bfine[- ]tuning\b")),
        ),
    ),
    TechnicalPropertyGroup(
        "Reward density",
        (
            ("dense", (r"\bdense\s+rewards?\b",)),
            ("sparse", (r"\bsparse\s+rewards?\b",)),
        ),
    ),
    TechnicalPropertyGroup(
        "Evaluation domain",
        (
            ("in-domain", (r"\bin[- ]domain\b",)),
            ("out-of-domain", (r"\bout[- ]of[- ]domain\b",)),
        ),
    ),
    TechnicalPropertyGroup(
        "Data sensitivity",
        (
            ("private", (r"\bprivate\s+(?:medical\s+)?records?\b", r"\bprivate\s+data\b")),
            ("public", (r"\bpublic\s+(?:medical\s+)?records?\b", r"\bpublic\s+data\b")),
        ),
    ),
)
```

Use the same disjoint-value and context-overlap pattern as `attribute_lens`.

- [ ] **Step 4: Verify direct tests**

Run:

```bash
python -m pytest tests/test_technical_property_lens.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/technical_property_lens.py tests/test_technical_property_lens.py
git diff --check
wc -l src/citeproof/technical_property_lens.py tests/test_technical_property_lens.py
```

Expected: all tests pass; both files remain under 300 LOC.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/technical_property_lens.py tests/test_technical_property_lens.py
git commit -m "feat: add technical property lens"
```

## Task 2: Integration and End-to-End Tests

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Modify: `src/citeproof/adjudicator.py`
- Create: `tests/test_entailment_technical_properties.py`

- [ ] **Step 1: Add failing end-to-end tests**

Create `tests/test_entailment_technical_properties.py`:

```python
import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The algorithm runs in linear time.", "The algorithm runs in quadratic time."),
        ("The method uses exact inference.", "The method uses approximate inference."),
        ("The encoder is frozen during training.", "The encoder is fine-tuned end-to-end during training."),
        ("The agent is trained with dense rewards.", "The agent is trained with sparse rewards."),
        ("The model is evaluated on out-of-domain data.", "The model is evaluated on in-domain data."),
        ("The dataset contains private medical records.", "The dataset contains public medical records."),
    ],
)
def test_technical_property_conflicts_are_not_supported(claim: str, evidence: str) -> None:
    judgment = judge_evidence(claim, evidence)

    assert judgment.label == Label.CONTRADICTED


def test_technical_property_conflict_maps_to_entity_failure() -> None:
    judgment = adjudicate_evidence(
        "The algorithm runs in linear time.",
        "The algorithm runs in quadratic time.",
    )

    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_entailment_technical_properties.py -q -p no:cacheprovider`

Expected: FAIL because integration is missing.

- [ ] **Step 3: Integrate hard findings**

Import `inspect_technical_property_conflicts` in `src/citeproof/fact_lenses.py` and append its results to `hard_findings` after attribute conflicts.

- [ ] **Step 4: Map failure modes**

In `src/citeproof/adjudicator.py`, add a `TECHNICAL_PROPERTY_CONFLICTS` tuple with the lower-case conflict labels and map them to `FailureMode.ENTITY_CONFLICT` in `_fact_failure_mode`.

- [ ] **Step 5: Verify focused tests**

Run:

```bash
python -m pytest tests/test_technical_property_lens.py tests/test_entailment_technical_properties.py tests/test_fact_lenses.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_entailment_technical_properties.py
git diff --check
wc -l src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_entailment_technical_properties.py
```

Expected: all tests pass; files remain under 300 LOC.

- [ ] **Step 6: Commit**

```bash
git add src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_entailment_technical_properties.py
git commit -m "fix: block technical property false support"
```

## Task 3: Benchmark and CI

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Append benchmark rows**

Append:

```jsonl
{"id":"complexity-property-conflict","claim":"The algorithm runs in linear time.","evidence":"The algorithm runs in quadratic time.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"inference-property-conflict","claim":"The method uses exact inference.","evidence":"The method uses approximate inference.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"trainability-property-conflict","claim":"The encoder is frozen during training.","evidence":"The encoder is fine-tuned end-to-end during training.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"reward-density-property-conflict","claim":"The agent is trained with dense rewards.","evidence":"The agent is trained with sparse rewards.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"domain-property-conflict","claim":"The model is evaluated on out-of-domain data.","evidence":"The model is evaluated on in-domain data.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"sensitivity-property-conflict","claim":"The dataset contains private medical records.","evidence":"The dataset contains public medical records.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
```

- [ ] **Step 2: Update eval runner and docs**

Add the six IDs to `test_edge_cases_with_expected_failure_modes_pass`. Change the edge-case total in `docs/evaluation.md` from `50` to `56` and mention technical property conflicts in the coverage sentence.

- [ ] **Step 3: Run full gate**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_technical_property_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output /tmp/citeproof_technical_property_hallucination.json
git diff --check
```

Expected: full tests pass; edge eval reports total `56`, accuracy `1.0`, and `false_supported_rate` `0.0`.

- [ ] **Step 4: Commit, push, verify CI**

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add technical property edge cases"
git push origin main
gh run list --repo SebastianBoehler/citeproof --branch main --limit 10 --json databaseId,headSha,status,conclusion,url
```

Expected: pushed SHA gets a successful `tests` workflow run.
