# Attribute Conflict Lens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block high-overlap false `supported` labels when a claim swaps a controlled academic attribute relative to the cited evidence.

**Architecture:** Add a focused `attribute_lens` module that returns deterministic hard-conflict findings. Integrate it into `fact_lenses.inspect_facts`, map its findings in `adjudicator`, and expand the edge-case benchmark from 40 to 46 cases.

**Tech Stack:** Python, pytest, ruff, existing CiteProof deterministic lens architecture.

---

## File Structure

- Create `src/citeproof/attribute_lens.py`: controlled vocabularies, mention extraction, context overlap, and `inspect_attribute_conflicts`.
- Create `tests/test_attribute_lens.py`: direct lens unit tests and false-positive boundaries.
- Modify `src/citeproof/fact_lenses.py`: append attribute conflicts to hard findings.
- Modify `src/citeproof/adjudicator.py`: map attribute conflicts to failure modes.
- Create `tests/test_entailment_attributes.py`: end-to-end `judge_evidence` and `adjudicate_evidence` tests.
- Modify `examples/edge_cases/claim_support.jsonl`: add six adversarial rows.
- Modify `tests/test_eval_runner.py`: assert expected failure-mode rows are present and pass.
- Modify `docs/evaluation.md`: update benchmark total and coverage sentence.

## Task 1: Direct Attribute Lens

**Files:**
- Create: `src/citeproof/attribute_lens.py`
- Create: `tests/test_attribute_lens.py`

- [ ] **Step 1: Write failing direct tests**

```python
from citeproof.attribute_lens import inspect_attribute_conflicts


def test_detects_modality_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The dataset contains 10,000 images.",
        "The dataset contains 10,000 text samples.",
    )

    assert any("Modality conflict" in finding for finding in findings)


def test_detects_task_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The method improves summarization performance.",
        "The method improves translation performance.",
    )

    assert any("Task conflict" in finding for finding in findings)


def test_detects_split_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The model was evaluated on the test set.",
        "The model was evaluated on the validation set.",
    )

    assert any("Split conflict" in finding for finding in findings)


def test_detects_language_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The benchmark evaluates German documents.",
        "The benchmark evaluates English documents.",
    )

    assert any("Language conflict" in finding for finding in findings)


def test_detects_optimizer_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The model uses Adam optimization.",
        "The model uses SGD optimization.",
    )

    assert any("Optimizer conflict" in finding for finding in findings)


def test_detects_availability_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The dataset is publicly available.",
        "The dataset is not publicly available.",
    )

    assert any("Availability conflict" in finding for finding in findings)


def test_ignores_different_contexts() -> None:
    findings = inspect_attribute_conflicts(
        "The image dataset is publicly available.",
        "The text baseline is private.",
    )

    assert findings == ()
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_attribute_lens.py -q -p no:cacheprovider`

Expected: FAIL because `citeproof.attribute_lens` does not exist.

- [ ] **Step 3: Implement the lens**

Create `src/citeproof/attribute_lens.py` with:

```python
"""Controlled academic attribute conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class AttributeGroup:
    name: str
    label: str
    values: tuple[tuple[str, tuple[str, ...]], ...]
    failure_hint: str


GROUPS = (
    AttributeGroup(
        "modality",
        "Modality",
        (
            ("images", (r"\bimages?\b", r"\bvisual\b")),
            ("text", (r"\btexts?\b", r"\btextual\b")),
            ("audio", (r"\baudio\b", r"\bspeech\b")),
            ("video", (r"\bvideos?\b")),
            ("tabular", (r"\btabular\b", r"\btables?\b")),
        ),
        "entity",
    ),
    AttributeGroup(
        "task",
        "Task",
        (
            ("summarization", (r"\bsummari[sz]ation\b", r"\bsummari[sz]e\b")),
            ("translation", (r"\btranslation\b", r"\btranslate\b")),
            ("classification", (r"\bclassification\b", r"\bclassify\b")),
            ("segmentation", (r"\bsegmentation\b", r"\bsegment\b")),
            ("retrieval", (r"\bretrieval\b", r"\bretrieve\b")),
        ),
        "entity",
    ),
    AttributeGroup(
        "split",
        "Split",
        (
            ("train", (r"\btrain(?:ing)?\s+set\b", r"\btrain(?:ing)?\s+split\b")),
            ("validation", (r"\bvalidation\s+set\b", r"\bvalidation\s+split\b", r"\bdev\s+set\b")),
            ("test", (r"\btest\s+set\b", r"\btest\s+split\b")),
        ),
        "entity",
    ),
    AttributeGroup(
        "language",
        "Language",
        (
            ("English", (r"\bEnglish\b",)),
            ("German", (r"\bGerman\b",)),
            ("French", (r"\bFrench\b",)),
            ("Spanish", (r"\bSpanish\b",)),
            ("Chinese", (r"\bChinese\b",)),
        ),
        "entity",
    ),
    AttributeGroup(
        "optimizer",
        "Optimizer",
        (
            ("AdamW", (r"\bAdamW\b",)),
            ("Adam", (r"\bAdam\b",)),
            ("SGD", (r"\bSGD\b", r"\bstochastic gradient descent\b")),
            ("RMSProp", (r"\bRMSProp\b",)),
        ),
        "entity",
    ),
    AttributeGroup(
        "availability",
        "Availability",
        (
            ("public", (r"\bpublicly available\b", r"\bopen source\b")),
            ("private", (r"\bnot publicly available\b", r"\bprivate\b", r"\bproprietary\b")),
        ),
        "negation",
    ),
)

TRIGGER_WORDS_RE = re.compile(
    r"\b("
    r"adamw?|audio|available|chinese|classification|classify|dev|documents?|english|"
    r"french|german|images?|not|open|optimization|private|proprietary|publicly|"
    r"retrieval|rmsprop|segmentation|sgd|source|spanish|summari[sz]ation|"
    r"tabular|test|text|texts?|train(?:ing)?|translation|validation|videos?"
    r")\b",
    re.IGNORECASE,
)


def inspect_attribute_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    findings: list[str] = []
    for group in GROUPS:
        claim_values = _mentioned_values(group, claim)
        evidence_values = _mentioned_values(group, evidence)
        for claim_value in claim_values:
            for evidence_value in evidence_values:
                if claim_value == evidence_value:
                    continue
                if _context_overlaps(claim, evidence):
                    findings.append(
                        f"{group.label} conflict: claim says {claim_value} "
                        f"while evidence says {evidence_value}."
                    )
    return tuple(dict.fromkeys(findings))
```

Also add `_mentioned_values`, `_context_overlaps`, and `_context_tokens`.

- [ ] **Step 4: Run direct tests**

Run: `python -m pytest tests/test_attribute_lens.py -q -p no:cacheprovider`

Expected: all tests pass.

- [ ] **Step 5: Commit direct lens**

```bash
git add src/citeproof/attribute_lens.py tests/test_attribute_lens.py
git commit -m "feat: add attribute conflict lens"
```

## Task 2: Verifier Integration

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Modify: `src/citeproof/adjudicator.py`
- Create: `tests/test_entailment_attributes.py`

- [ ] **Step 1: Add failing end-to-end tests**

```python
import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The dataset contains 10,000 images.", "The dataset contains 10,000 text samples."),
        ("The method improves summarization performance.", "The method improves translation performance."),
        ("The model was evaluated on the test set.", "The model was evaluated on the validation set."),
        ("The benchmark evaluates German documents.", "The benchmark evaluates English documents."),
        ("The model uses Adam optimization.", "The model uses SGD optimization."),
        ("The dataset is publicly available.", "The dataset is not publicly available."),
    ],
)
def test_attribute_conflicts_are_not_supported(claim: str, evidence: str) -> None:
    judgment = judge_evidence(claim, evidence)

    assert judgment.label == Label.CONTRADICTED


def test_availability_conflict_maps_to_negation_failure() -> None:
    judgment = adjudicate_evidence(
        "The dataset is publicly available.",
        "The dataset is not publicly available.",
    )

    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT


def test_task_conflict_maps_to_entity_failure() -> None:
    judgment = adjudicate_evidence(
        "The method improves summarization performance.",
        "The method improves translation performance.",
    )

    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_entailment_attributes.py -q -p no:cacheprovider`

Expected: FAIL because integration is missing.

- [ ] **Step 3: Integrate hard findings**

In `src/citeproof/fact_lenses.py`, import `inspect_attribute_conflicts` and append it to `hard_findings` after qualitative conflicts.

- [ ] **Step 4: Map failure modes**

In `src/citeproof/adjudicator.py`, map `"availability conflict"` to `NEGATION_CONFLICT` and the remaining attribute conflict strings to `ENTITY_CONFLICT`.

- [ ] **Step 5: Run focused tests**

Run:

```bash
python -m pytest tests/test_attribute_lens.py tests/test_entailment_attributes.py tests/test_fact_lenses.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/attribute_lens.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_attribute_lens.py tests/test_entailment_attributes.py
```

Expected: all tests pass and ruff reports no issues.

- [ ] **Step 6: Commit integration**

```bash
git add src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_entailment_attributes.py
git commit -m "fix: block attribute false support"
```

## Task 3: Benchmark and Documentation

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add benchmark rows**

Append six rows with `expected_label: "contradicted"`:

```jsonl
{"id":"modality-attribute-conflict","claim":"The dataset contains 10,000 images.","evidence":"The dataset contains 10,000 text samples.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"task-attribute-conflict","claim":"The method improves summarization performance.","evidence":"The method improves translation performance.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"split-attribute-conflict","claim":"The model was evaluated on the test set.","evidence":"The model was evaluated on the validation set.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"language-attribute-conflict","claim":"The benchmark evaluates German documents.","evidence":"The benchmark evaluates English documents.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"optimizer-attribute-conflict","claim":"The model uses Adam optimization.","evidence":"The model uses SGD optimization.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"availability-attribute-conflict","claim":"The dataset is publicly available.","evidence":"The dataset is not publicly available.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
```

- [ ] **Step 2: Update failure-mode regression**

Add all six IDs to the required set in `tests/test_eval_runner.py::test_edge_cases_with_expected_failure_modes_pass`.

- [ ] **Step 3: Update evaluation docs**

Set the edge-case total to `46` and add controlled attribute conflicts to the coverage sentence.

- [ ] **Step 4: Run full gate**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_attribute_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output /tmp/citeproof_attribute_hallucination.json
git diff --check
wc -l src/citeproof/attribute_lens.py tests/test_attribute_lens.py tests/test_entailment_attributes.py
```

Expected: tests and ruff pass, edge eval reports total `46`, accuracy `1.0`, and `false_supported_rate` `0.0`.

- [ ] **Step 5: Commit benchmark**

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add attribute edge cases"
```

## Task 4: Push and CI

**Files:**
- No file edits.

- [ ] **Step 1: Push main**

Run: `git push origin main`

Expected: push succeeds.

- [ ] **Step 2: Verify GitHub Actions**

Run:

```bash
gh run list --repo SebastianBoehler/citeproof --branch main --limit 10 --json databaseId,headSha,status,conclusion,url
```

Expected: latest pushed SHA gets a completed `success` run for the `tests` workflow.
