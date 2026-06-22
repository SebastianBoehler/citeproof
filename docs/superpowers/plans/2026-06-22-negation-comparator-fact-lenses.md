# Negation Comparator Fact Lenses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent high-overlap evidence that explicitly negates or bounds a claim from being labeled `supported`.

**Architecture:** Add a focused deterministic module for explicit negation, directional-change, numeric-bound conflicts, and numeric-bound tensions. Integrate it into `fact_lenses.py`, map findings to existing failure modes, and expand the adversarial edge benchmark.

**Tech Stack:** Python 3.11+, stdlib regex/dataclasses, existing `citeproof.quantities`, `citeproof.text`, pytest, ruff.

---

## File Structure

- Create `src/citeproof/negation_lens.py`: deterministic explicit-negation, direction, numeric-bound conflict, and numeric-bound tension helpers.
- Create `tests/test_negation_lens.py`: direct unit tests for the new lens without involving the full adjudicator.
- Modify `src/citeproof/fact_lenses.py`: call the new lens with other hard fact findings.
- Modify `src/citeproof/adjudicator.py`: map `Negation conflict` and `Direction conflict` findings to `FailureMode.NEGATION_CONFLICT`.
- Modify `tests/test_fact_lenses.py`: integration tests through `inspect_facts`.
- Modify `tests/test_entailment_quantities.py` or create `tests/test_entailment_negation.py`: verify `judge_evidence` no longer returns `supported` for the known false-supported probes.
- Modify `examples/edge_cases/claim_support.jsonl`: add adversarial direct eval rows.
- Modify `tests/test_eval_runner.py`: assert the new expected failure-mode rows pass.
- Modify `docs/evaluation.md`: update edge benchmark total and coverage wording after fresh evals.

All Python files touched by this plan must stay below 300 LOC.

---

### Task 1: Direct Lens Tests

**Files:**
- Create: `tests/test_negation_lens.py`

- [ ] **Step 1: Write failing tests for explicit negation**

Create `tests/test_negation_lens.py` with:

```python
from citeproof.negation_lens import (
    inspect_negation_and_comparator_conflicts,
    inspect_negation_and_comparator_tensions,
)


def test_detects_use_negation_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The method uses LoRA adapters.",
        "The method does not use LoRA adapters.",
    )

    assert any("Negation conflict" in finding for finding in findings)
    assert any("LoRA adapters" in finding for finding in findings)


def test_detects_training_negation_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The model was trained on ImageNet.",
        "The model was not trained on ImageNet.",
    )

    assert any("Negation conflict" in finding for finding in findings)
    assert any("ImageNet" in finding for finding in findings)


def test_detects_without_negation_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The approach uses offline pretraining.",
        "The approach works without offline pretraining.",
    )

    assert any("Negation conflict" in finding for finding in findings)
    assert any("offline pretraining" in finding for finding in findings)


def test_ignores_unrelated_negated_object() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The method uses LoRA adapters.",
        "The method does not use labels during training.",
    )

    assert findings == ()
```

- [ ] **Step 2: Verify tests fail before implementation**

Run:

```bash
python -m pytest tests/test_negation_lens.py -q -p no:cacheprovider
```

Expected: FAIL with `ModuleNotFoundError: No module named 'citeproof.negation_lens'`.

- [ ] **Step 3: Add failing direction and numeric-bound tests**

Append to `tests/test_negation_lens.py`:

```python
def test_detects_direction_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "Error decreased by 5 percent.",
        "Error increased by 5 percent.",
    )

    assert any("Direction conflict" in finding for finding in findings)


def test_ignores_direction_change_for_different_metric() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "Training time decreased by 5 percent.",
        "Accuracy increased by 5 percent.",
    )

    assert findings == ()


def test_detects_incompatible_numeric_bounds() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains up to 16,000 task-oriented dialogues.",
    )

    assert any("Numeric bound conflict" in finding for finding in findings)


def test_allows_compatible_lower_bound_quantity() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "Schema-Guided Dialogue contains at least 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 20,000 task-oriented dialogues.",
    )

    assert findings == ()


def test_flags_bound_equality_as_partial_tension() -> None:
    hard_findings = inspect_negation_and_comparator_conflicts(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 16,000 task-oriented dialogues.",
    )
    partial_findings = inspect_negation_and_comparator_tensions(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 16,000 task-oriented dialogues.",
    )

    assert hard_findings == ()
    assert any("Numeric bound tension" in finding for finding in partial_findings)
```

- [ ] **Step 4: Verify expanded tests still fail**

Run:

```bash
python -m pytest tests/test_negation_lens.py -q -p no:cacheprovider
```

Expected: FAIL because `citeproof.negation_lens` does not exist.

---

### Task 2: Implement The New Lens

**Files:**
- Create: `src/citeproof/negation_lens.py`
- Test: `tests/test_negation_lens.py`

- [ ] **Step 1: Create module skeleton**

Create `src/citeproof/negation_lens.py`:

```python
"""Deterministic negation and comparator conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from citeproof.quantities import QuantityMention, quantity_mentions
from citeproof.text import tokenize

LOWER_BOUND = "lower"
UPPER_BOUND = "upper"
EXACT_BOUND = "exact"

NEGATED_USE_RE = re.compile(
    r"\b(?:does\s+not|did\s+not|not)\s+use\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
CLAIM_USE_RE = re.compile(
    r"\b(?:uses?|used|using)\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
NEGATED_TRAIN_RE = re.compile(
    r"\b(?:was\s+not|were\s+not|not)\s+"
    r"(?P<predicate>trained|pretrained|fine[- ]tuned)\s+on\s+"
    r"(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
CLAIM_TRAIN_RE = re.compile(
    r"\b(?P<predicate>trained|pretrained|fine[- ]tuned)\s+on\s+"
    r"(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
WITHOUT_RE = re.compile(
    r"\bwithout\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
POSITIVE_DIRECTION_RE = re.compile(r"\b(increase[sd]?|higher|more)\b", re.IGNORECASE)
NEGATIVE_DIRECTION_RE = re.compile(r"\b(decrease[sd]?|lower|less|reduced)\b", re.IGNORECASE)
LOWER_BOUND_RE = re.compile(
    r"\b(over|more\s+than|greater\s+than|at\s+least|no\s+less\s+than)\b",
    re.IGNORECASE,
)
UPPER_BOUND_RE = re.compile(
    r"\b(up\s+to|at\s+most|no\s+more\s+than|under|less\s+than)\b",
    re.IGNORECASE,
)
EXACT_BOUND_RE = re.compile(r"\b(exactly)\b", re.IGNORECASE)
OBJECT_STOP_RE = re.compile(r"\b(?:but|although|while|whereas|and|with|during|from|than)\b", re.IGNORECASE)


@dataclass(frozen=True)
class BoundQuantity:
    mention: QuantityMention
    bound: str
```

- [ ] **Step 2: Add public API and negation helpers**

Append:

```python
def inspect_negation_and_comparator_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return deterministic negation, direction, and bound conflicts."""

    findings = (
        _explicit_negation_conflicts(claim, evidence)
        + _direction_conflicts(claim, evidence)
        + _numeric_bound_conflicts(claim, evidence)
    )
    return tuple(findings)


def inspect_negation_and_comparator_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return weaker bound tensions that should block a supported label."""

    return tuple(_numeric_bound_tensions(claim, evidence))


def _explicit_negation_conflicts(claim: str, evidence: str) -> list[str]:
    claim_objects = _claim_objects(claim)
    evidence_negations = _evidence_negated_objects(evidence)
    findings: list[str] = []
    for predicate, claim_object in claim_objects:
        for negated_object in evidence_negations:
            if _objects_overlap(claim_object, negated_object):
                findings.append(
                    f"Negation conflict: evidence negates {predicate} of {claim_object}"
                )
                break
    return findings


def _claim_objects(text: str) -> list[tuple[str, str]]:
    objects: list[tuple[str, str]] = []
    for match in CLAIM_USE_RE.finditer(text):
        objects.append(("use", _clean_object(match.group("object"))))
    for match in CLAIM_TRAIN_RE.finditer(text):
        predicate = match.group("predicate").replace("-", " ").lower()
        objects.append((predicate, _clean_object(match.group("object"))))
    return [(predicate, obj) for predicate, obj in objects if obj]


def _evidence_negated_objects(text: str) -> list[str]:
    objects: list[str] = []
    for pattern in (NEGATED_USE_RE, NEGATED_TRAIN_RE, WITHOUT_RE):
        for match in pattern.finditer(text):
            obj = _clean_object(match.group("object"))
            if obj:
                objects.append(obj)
    return objects


def _clean_object(text: str) -> str:
    clipped = OBJECT_STOP_RE.split(text, maxsplit=1)[0]
    return clipped.strip(" .,:;()[]{}")


def _objects_overlap(left: str, right: str) -> bool:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return False
    overlap = left_tokens & right_tokens
    return bool(overlap) and len(overlap) / min(len(left_tokens), len(right_tokens)) >= 0.67
```

- [ ] **Step 3: Add direction helpers**

Append:

```python
def _direction_conflicts(claim: str, evidence: str) -> list[str]:
    claim_direction = _direction(claim)
    evidence_direction = _direction(evidence)
    if not claim_direction or not evidence_direction or claim_direction == evidence_direction:
        return []
    if not _direction_context_overlaps(claim, evidence):
        return []
    return [
        "Direction conflict: claim says "
        f"{claim_direction} while evidence says {evidence_direction}"
    ]


def _direction(text: str) -> str | None:
    positive = bool(POSITIVE_DIRECTION_RE.search(text))
    negative = bool(NEGATIVE_DIRECTION_RE.search(text))
    if positive == negative:
        return None
    return "increased" if positive else "decreased"


def _direction_context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = set(tokenize(_strip_direction_words(claim)))
    evidence_tokens = set(tokenize(_strip_direction_words(evidence)))
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.5


def _strip_direction_words(text: str) -> str:
    text = POSITIVE_DIRECTION_RE.sub(" ", text)
    return NEGATIVE_DIRECTION_RE.sub(" ", text)
```

- [ ] **Step 4: Add numeric-bound helpers**

Append:

```python
def _numeric_bound_conflicts(claim: str, evidence: str) -> list[str]:
    claim_bounds = _bound_quantities(claim)
    evidence_bounds = _bound_quantities(evidence)
    findings: list[str] = []
    for claim_bound in claim_bounds:
        for evidence_bound in evidence_bounds:
            if claim_bound.mention.unit != evidence_bound.mention.unit:
                continue
            if _bounds_conflict(claim_bound, evidence_bound):
                findings.append(
                    "Numeric bound conflict for "
                    f"{claim_bound.mention.unit}: claim {claim_bound.mention.text} "
                    f"vs evidence {evidence_bound.mention.text}"
                )
    return findings


def _numeric_bound_tensions(claim: str, evidence: str) -> list[str]:
    claim_bounds = _bound_quantities(claim)
    evidence_bounds = _bound_quantities(evidence)
    findings: list[str] = []
    for claim_bound in claim_bounds:
        for evidence_bound in evidence_bounds:
            if claim_bound.mention.unit != evidence_bound.mention.unit:
                continue
            if _bounds_tense(claim_bound, evidence_bound):
                findings.append(
                    "Numeric bound tension for "
                    f"{claim_bound.mention.unit}: claim {claim_bound.mention.text} "
                    f"vs evidence {evidence_bound.mention.text}"
                )
    return findings


def _bound_quantities(text: str) -> list[BoundQuantity]:
    bounds: list[BoundQuantity] = []
    cursor = 0
    for mention in quantity_mentions(text):
        start = text.find(mention.text, cursor)
        if start == -1:
            start = text.find(mention.text)
        cursor = max(start + len(mention.text), cursor)
        context = text[max(0, start - 32) : start]
        bounds.append(BoundQuantity(mention, _bound_category(context)))
    return bounds


def _bound_category(prefix: str) -> str:
    if LOWER_BOUND_RE.search(prefix):
        return LOWER_BOUND
    if UPPER_BOUND_RE.search(prefix):
        return UPPER_BOUND
    if EXACT_BOUND_RE.search(prefix):
        return EXACT_BOUND
    return EXACT_BOUND


def _bounds_conflict(claim: BoundQuantity, evidence: BoundQuantity) -> bool:
    if claim.bound == LOWER_BOUND and evidence.bound == UPPER_BOUND:
        return evidence.mention.number <= claim.mention.number
    if claim.bound == UPPER_BOUND and evidence.bound == LOWER_BOUND:
        return evidence.mention.number >= claim.mention.number
    if claim.bound == LOWER_BOUND and evidence.bound == EXACT_BOUND:
        return evidence.mention.number < claim.mention.number
    if claim.bound == UPPER_BOUND and evidence.bound == EXACT_BOUND:
        return evidence.mention.number > claim.mention.number
    return False


def _bounds_tense(claim: BoundQuantity, evidence: BoundQuantity) -> bool:
    return bool(
        claim.bound == LOWER_BOUND
        and evidence.bound == EXACT_BOUND
        and evidence.mention.number == claim.mention.number
    )
```

- [ ] **Step 5: Run direct tests**

Run:

```bash
python -m pytest tests/test_negation_lens.py -q -p no:cacheprovider
```

Expected: PASS, all tests in `tests/test_negation_lens.py` pass.

- [ ] **Step 6: Run lint and size check**

Run:

```bash
ruff check --no-cache src/citeproof/negation_lens.py tests/test_negation_lens.py
wc -l src/citeproof/negation_lens.py tests/test_negation_lens.py
```

Expected: ruff passes; both files are below 300 LOC.

- [ ] **Step 7: Commit direct lens**

Run:

```bash
git add src/citeproof/negation_lens.py tests/test_negation_lens.py
git commit -m "feat: add negation comparator lens"
```

---

### Task 3: Integrate With Fact Lenses And Failure Modes

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Modify: `src/citeproof/adjudicator.py`
- Modify: `tests/test_fact_lenses.py`
- Create: `tests/test_entailment_negation.py`

- [ ] **Step 1: Add fact-lens integration tests**

Append to `tests/test_fact_lenses.py`:

```python
def test_detects_use_negation_fact_conflict() -> None:
    result = inspect_facts(
        "The method uses LoRA adapters.",
        "The method does not use LoRA adapters.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Negation conflict" in finding for finding in result.findings)


def test_detects_direction_fact_conflict() -> None:
    result = inspect_facts(
        "Error decreased by 5 percent.",
        "Error increased by 5 percent.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Direction conflict" in finding for finding in result.findings)


def test_detects_numeric_bound_fact_conflict() -> None:
    result = inspect_facts(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains up to 16,000 task-oriented dialogues.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Numeric bound conflict" in finding for finding in result.findings)
```

- [ ] **Step 2: Add entailment regression tests**

Create `tests/test_entailment_negation.py`:

```python
from citeproof.entailment import judge_evidence
from citeproof.models import Label


def test_judge_evidence_does_not_support_use_negation() -> None:
    judgment = judge_evidence(
        "The method uses LoRA adapters.",
        "The method does not use LoRA adapters.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_does_not_support_training_negation() -> None:
    judgment = judge_evidence(
        "The model was trained on ImageNet.",
        "The model was not trained on ImageNet.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_does_not_support_direction_swap() -> None:
    judgment = judge_evidence(
        "Error decreased by 5 percent.",
        "Error increased by 5 percent.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_does_not_support_bound_conflict() -> None:
    judgment = judge_evidence(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains up to 16,000 task-oriented dialogues.",
    )

    assert judgment.label == Label.CONTRADICTED
```

- [ ] **Step 3: Verify integration tests fail**

Run:

```bash
python -m pytest tests/test_fact_lenses.py tests/test_entailment_negation.py -q -p no:cacheprovider
```

Expected: FAIL because `fact_lenses.py` has not called the new lens and
`adjudicator.py` does not map the new findings yet.

- [ ] **Step 4: Wire the new lens into `fact_lenses.py`**

Add import:

```python
from citeproof.negation_lens import (
    inspect_negation_and_comparator_conflicts,
    inspect_negation_and_comparator_tensions,
)
```

Update `hard_findings`:

```python
    hard_findings = (
        _number_conflicts(claim, evidence)
        + _unit_conflicts(claim, evidence)
        + _year_conflicts(claim, evidence)
        + list(inspect_negation_and_comparator_conflicts(claim, evidence))
    )
```

After the hard-finding block and before entity conflicts, add a partial-support
check:

```python
    tension_findings = inspect_negation_and_comparator_tensions(claim, evidence)
    if tension_findings:
        return FactInspection(Label.PARTIALLY_SUPPORTED, tension_findings)
```

- [ ] **Step 5: Map failure modes in `adjudicator.py`**

In `_fact_failure_mode`, add this branch after unit/year/numeric checks and
before entity fallback:

```python
    if "negation conflict" in text or "direction conflict" in text:
        return FailureMode.NEGATION_CONFLICT
```

Numeric bound findings include `numeric bound conflict`, which contains no
`numeric conflict` phrase. Add this branch with the numeric conflict branch:

```python
    if "numeric conflict" in text or "numeric bound conflict" in text:
        return FailureMode.NUMERIC_CONFLICT
```

- [ ] **Step 6: Run focused integration tests**

Run:

```bash
python -m pytest tests/test_negation_lens.py tests/test_fact_lenses.py tests/test_entailment_negation.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 7: Run lint and size check**

Run:

```bash
ruff check --no-cache src/citeproof/negation_lens.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_negation_lens.py tests/test_fact_lenses.py tests/test_entailment_negation.py
wc -l src/citeproof/negation_lens.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_negation_lens.py tests/test_fact_lenses.py tests/test_entailment_negation.py
```

Expected: ruff passes; every listed Python file is below 300 LOC.

- [ ] **Step 8: Commit integration**

Run:

```bash
git add src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_fact_lenses.py tests/test_entailment_negation.py
git commit -m "fix: block explicit negation support"
```

---

### Task 4: Expand Edge Benchmark And Docs

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Append adversarial benchmark rows**

Append these JSONL rows to `examples/edge_cases/claim_support.jsonl`:

```jsonl
{"id":"use-negation-conflict","claim":"The method uses LoRA adapters.","evidence":"The method does not use LoRA adapters.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"training-negation-conflict","claim":"The model was trained on ImageNet.","evidence":"The model was not trained on ImageNet.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"without-pretraining-conflict","claim":"The approach uses offline pretraining.","evidence":"The approach works without offline pretraining.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"direction-swap-conflict","claim":"Error decreased by 5 percent.","evidence":"Error increased by 5 percent.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"quantity-bound-conflict","claim":"Schema-Guided Dialogue contains over 16k task-oriented dialogues.","evidence":"Schema-Guided Dialogue contains up to 16,000 task-oriented dialogues.","expected_label":"contradicted","expected_failure_mode":"numeric_conflict"}
{"id":"quantity-bound-compatible","claim":"Schema-Guided Dialogue contains at least 16k task-oriented dialogues.","evidence":"Schema-Guided Dialogue contains 20,000 task-oriented dialogues.","expected_label":"supported"}
{"id":"quantity-bound-equality-tension","claim":"Schema-Guided Dialogue contains over 16k task-oriented dialogues.","evidence":"Schema-Guided Dialogue contains 16,000 task-oriented dialogues.","expected_label":"partially_supported"}
{"id":"unrelated-negation-not-conflict","claim":"The method uses LoRA adapters.","evidence":"The method does not use labels during training.","expected_label":"unsupported"}
```

- [ ] **Step 2: Update expected failure-mode coverage test**

In `tests/test_eval_runner.py::test_edge_cases_with_expected_failure_modes_pass`,
add these IDs to the expected set:

```python
        "use-negation-conflict",
        "training-negation-conflict",
        "without-pretraining-conflict",
        "direction-swap-conflict",
        "quantity-bound-conflict",
```

- [ ] **Step 3: Update evaluation docs**

In `docs/evaluation.md`, update the edge benchmark total from `25` to `33`.

Update the coverage sentence to include:

```markdown
explicit negation conflicts, directional change conflicts, numeric bound conflicts,
```

- [ ] **Step 4: Run eval-focused tests**

Run:

```bash
python -m pytest tests/test_eval_runner.py tests/test_negation_lens.py tests/test_entailment_negation.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Run direct edge eval**

Run:

```bash
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl \
  --details-output /tmp/citeproof_negation_edge.json
```

Expected:

- `total` is `33`;
- `accuracy` is `1.0`;
- `false_supported_rate` is `0.0`.

- [ ] **Step 6: Inspect new benchmark detail rows**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path

rows = json.loads(Path("/tmp/citeproof_negation_edge.json").read_text())
ids = {
    "use-negation-conflict",
    "training-negation-conflict",
    "without-pretraining-conflict",
    "direction-swap-conflict",
    "quantity-bound-conflict",
    "quantity-bound-compatible",
    "quantity-bound-equality-tension",
    "unrelated-negation-not-conflict",
}
for row in rows:
    if row["id"] in ids:
        print(json.dumps(row, indent=2, sort_keys=True))
PY
```

Expected: contradiction rows pass their expected failure mode; compatible and
unrelated rows do not have `false_supported: true`.

- [ ] **Step 7: Commit benchmark expansion**

Run:

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add negation comparator edge cases"
```

---

### Task 5: Full Verification, Push, And CI

**Files:**
- No source edits in this task unless verification reveals a defect.

- [ ] **Step 1: Run full local tests**

Run:

```bash
python -m pytest -q -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 2: Run full lint**

Run:

```bash
ruff check --no-cache .
```

Expected: all checks pass.

- [ ] **Step 3: Run primary direct eval**

Run:

```bash
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
```

Expected:

- `total` is `4`;
- `accuracy` is `1.0`;
- `false_supported_rate` is `0.0`.

- [ ] **Step 4: Run edge direct eval**

Run:

```bash
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl \
  --details-output /tmp/citeproof_negation_edge_final.json
```

Expected:

- `total` is `33`;
- `accuracy` is `1.0`;
- `false_supported_rate` is `0.0`.

- [ ] **Step 5: Run hallucination draft eval**

Run:

```bash
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output /tmp/citeproof_negation_hallucination_final.json
```

Expected:

- `total` is `5`;
- `accuracy` is `1.0`;
- `false_supported_rate` is `0.0`.

- [ ] **Step 6: Check diff cleanliness**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intentional uncommitted changes if a
verification fix was needed. Commit any verification fix with a focused message
before pushing.

- [ ] **Step 7: Push main**

Run:

```bash
git push origin main
```

Expected: push succeeds.

- [ ] **Step 8: Watch CI**

Find and watch the run for the pushed HEAD:

```bash
HEAD_SHA=$(git rev-parse HEAD)
gh run list --repo SebastianBoehler/citeproof --commit "$HEAD_SHA" \
  --limit 5 --json databaseId,headSha,status,conclusion,name,workflowName,createdAt,url
gh run watch <run-id> --repo SebastianBoehler/citeproof --exit-status
```

Expected: the `tests` workflow succeeds on all configured Python versions.

---

## Self-Review Checklist

- The plan implements every spec section: explicit negation, direction conflict,
  numeric bounds, integration, failure-mode mapping, benchmark expansion, docs,
  and full verification.
- It keeps implementation boundaries focused by adding `negation_lens.py`
  instead of growing `fact_lenses.py` with unrelated parsing details.
- It uses TDD for the new module and integration behavior.
- It preserves `false_supported_rate = 0.0` as the primary metric.
- It includes non-conflict rows so the new lens does not only learn to
  contradict.
