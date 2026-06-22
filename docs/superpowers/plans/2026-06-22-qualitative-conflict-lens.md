# Qualitative Conflict Lens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block false `supported` labels for qualitative scope, strength, and descriptor conflicts.

**Architecture:** Add `qualitative_lens.py` as a small deterministic module with hard conflict and partial-tension functions. Integrate it into `fact_lenses.py`, add adversarial direct eval cases, then run the full local and CI gate.

**Tech Stack:** Python 3.11+, stdlib regex, existing `citeproof.text.tokenize`, pytest, ruff.

---

## File Structure

- Create `src/citeproof/qualitative_lens.py`: curated qualitative conflict and tension checks.
- Create `tests/test_qualitative_lens.py`: direct tests for the new module.
- Modify `src/citeproof/fact_lenses.py`: call qualitative conflicts and tensions.
- Modify `src/citeproof/adjudicator.py`: map qualitative finding strings to existing failure modes.
- Modify `tests/test_fact_lenses.py`: integration tests through `inspect_facts`.
- Create `tests/test_entailment_qualitative.py`: `judge_evidence` regressions for false-supported probes.
- Modify `examples/edge_cases/claim_support.jsonl`, `tests/test_eval_runner.py`, and `docs/evaluation.md`.

All touched Python files must stay below 300 LOC.

---

### Task 1: Direct Qualitative Lens

**Files:**
- Create: `src/citeproof/qualitative_lens.py`
- Create: `tests/test_qualitative_lens.py`

- [ ] **Step 1: Add failing direct tests**

Create `tests/test_qualitative_lens.py`:

```python
from citeproof.qualitative_lens import inspect_qualitative_conflicts, inspect_qualitative_tensions


def test_detects_exclusivity_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "Method X is the only method evaluated on sparse-reward tasks.",
        "Method X is one of three methods evaluated on sparse-reward tasks.",
    )

    assert any("Exclusivity conflict" in finding for finding in findings)


def test_detects_significance_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "Method X significantly improves accuracy.",
        "Method X improves accuracy, but the improvement is not statistically significant.",
    )

    assert any("Significance conflict" in finding for finding in findings)


def test_detects_sota_negation_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "Method X achieves state-of-the-art accuracy on GLUE.",
        "Method X does not achieve state-of-the-art accuracy on GLUE.",
    )

    assert any("State-of-the-art conflict" in finding for finding in findings)


def test_detects_requirement_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "Method X requires no labeled data.",
        "Method X requires labeled data for training.",
    )

    assert any("Requirement conflict" in finding for finding in findings)


def test_detects_descriptor_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "The policy uses a transformer architecture.",
        "The policy uses a convolutional architecture.",
    )

    assert any("Descriptor conflict" in finding for finding in findings)


def test_detects_offline_online_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "The method uses offline reinforcement learning.",
        "The method uses online reinforcement learning.",
    )

    assert any("Descriptor conflict" in finding for finding in findings)


def test_detects_universal_scope_tension() -> None:
    findings = inspect_qualitative_tensions(
        "Method X improves performance on all evaluated tasks.",
        "Method X improves performance on most evaluated tasks.",
    )

    assert any("Scope tension" in finding for finding in findings)


def test_ignores_descriptor_terms_in_different_contexts() -> None:
    findings = inspect_qualitative_conflicts(
        "The transformer policy improves accuracy.",
        "The convolutional baseline is included for comparison.",
    )

    assert findings == ()
```

- [ ] **Step 2: Verify red run**

Run:

```bash
python -m pytest tests/test_qualitative_lens.py -q -p no:cacheprovider
```

Expected: FAIL with `ModuleNotFoundError: No module named 'citeproof.qualitative_lens'`.

- [ ] **Step 3: Implement `qualitative_lens.py`**

Create `src/citeproof/qualitative_lens.py`:

```python
"""Deterministic qualitative scope and descriptor checks."""

from __future__ import annotations

import re

from citeproof.text import tokenize

ONLY_RE = re.compile(r"\bonly\b", re.IGNORECASE)
MULTI_RE = re.compile(r"\b(one\s+of|among|several|multiple|both)\b", re.IGNORECASE)
UNIVERSAL_RE = re.compile(r"\b(all|every|universally)\b", re.IGNORECASE)
NARROW_RE = re.compile(r"\b(most|many|some|subset|not\s+all|majority)\b", re.IGNORECASE)
SIGNIFICANT_CLAIM_RE = re.compile(r"\b(significant|significantly)\b", re.IGNORECASE)
SIGNIFICANCE_NEGATION_RE = re.compile(
    r"\b(not\s+statistically\s+significant|not\s+significant|"
    r"no\s+statistically\s+significant)\b",
    re.IGNORECASE,
)
SOTA_CLAIM_RE = re.compile(r"\b(?:achieves?|reaches?)\s+state-of-the-art\b", re.IGNORECASE)
SOTA_NEGATION_RE = re.compile(
    r"\b(?:does\s+not|did\s+not|not)\s+(?:achieve|reach)\s+state-of-the-art\b",
    re.IGNORECASE,
)
REQUIRES_NO_RE = re.compile(
    r"\brequires?\s+no\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,60})",
    re.IGNORECASE,
)
REQUIRES_RE = re.compile(
    r"\brequires?\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,60})",
    re.IGNORECASE,
)
OBJECT_STOP_RE = re.compile(r"\b(?:for|during|with|and|but|while|whereas)\b", re.IGNORECASE)
TRIGGER_WORDS_RE = re.compile(
    r"\b(only|one|of|three|among|several|multiple|both|all|every|most|many|some|"
    r"subset|majority|significant|significantly|not|statistically|state|art|"
    r"requires?|no|transformer|convolutional|offline|online|supervised|unsupervised|"
    r"simulated|synthetic|real|world)\b",
    re.IGNORECASE,
)

DESCRIPTOR_PAIRS = (
    ("transformer", "convolutional"),
    ("offline", "online"),
    ("supervised", "unsupervised"),
    ("simulated", "real-world"),
    ("synthetic", "real-world"),
)


def inspect_qualitative_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    findings: list[str] = []
    findings += _exclusivity_conflicts(claim, evidence)
    findings += _significance_conflicts(claim, evidence)
    findings += _sota_conflicts(claim, evidence)
    findings += _requirement_conflicts(claim, evidence)
    findings += _descriptor_conflicts(claim, evidence)
    return tuple(findings)


def inspect_qualitative_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    if UNIVERSAL_RE.search(claim) and NARROW_RE.search(evidence) and _context_overlaps(claim, evidence):
        return ("Scope tension: evidence is narrower than the universal claim.",)
    return ()
```

Append helpers:

```python
def _exclusivity_conflicts(claim: str, evidence: str) -> list[str]:
    if ONLY_RE.search(claim) and MULTI_RE.search(evidence) and _context_overlaps(claim, evidence):
        return ["Exclusivity conflict: evidence describes the claim as one of multiple cases."]
    return []


def _significance_conflicts(claim: str, evidence: str) -> list[str]:
    if SIGNIFICANT_CLAIM_RE.search(claim) and SIGNIFICANCE_NEGATION_RE.search(evidence):
        if _context_overlaps(claim, evidence):
            return ["Significance conflict: evidence says the result is not statistically significant."]
    return []


def _sota_conflicts(claim: str, evidence: str) -> list[str]:
    if SOTA_CLAIM_RE.search(claim) and SOTA_NEGATION_RE.search(evidence):
        if _context_overlaps(claim, evidence):
            return ["State-of-the-art conflict: evidence negates the state-of-the-art claim."]
    return []


def _requirement_conflicts(claim: str, evidence: str) -> list[str]:
    claim_negative = [_clean_object(match.group("object")) for match in REQUIRES_NO_RE.finditer(claim)]
    evidence_positive = [_clean_object(match.group("object")) for match in REQUIRES_RE.finditer(evidence)]
    for negative in claim_negative:
        for positive in evidence_positive:
            if _objects_overlap(negative, positive):
                return [f"Requirement conflict: claim says no {negative} but evidence requires it."]
    return []


def _descriptor_conflicts(claim: str, evidence: str) -> list[str]:
    for left, right in DESCRIPTOR_PAIRS:
        if _has_descriptor(claim, left) and _has_descriptor(evidence, right):
            if _context_overlaps(claim, evidence):
                return [f"Descriptor conflict: claim says {left} while evidence says {right}."]
        if _has_descriptor(claim, right) and _has_descriptor(evidence, left):
            if _context_overlaps(claim, evidence):
                return [f"Descriptor conflict: claim says {right} while evidence says {left}."]
    return []


def _has_descriptor(text: str, descriptor: str) -> bool:
    pattern = descriptor.replace("-", r"[-\s]+")
    return bool(re.search(rf"\b{pattern}\b", text, re.IGNORECASE))


def _clean_object(text: str) -> str:
    return OBJECT_STOP_RE.split(text, maxsplit=1)[0].strip(" .,:;()[]{}")


def _objects_overlap(left: str, right: str) -> bool:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return False
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens)) >= 0.67


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = set(tokenize(TRIGGER_WORDS_RE.sub(" ", claim)))
    evidence_tokens = set(tokenize(TRIGGER_WORDS_RE.sub(" ", evidence)))
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.5
```

- [ ] **Step 4: Run direct tests and checks**

Run:

```bash
python -m pytest tests/test_qualitative_lens.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/qualitative_lens.py tests/test_qualitative_lens.py
git diff --check
wc -l src/citeproof/qualitative_lens.py tests/test_qualitative_lens.py
```

Expected: tests and ruff pass; both files under 300 LOC.

- [ ] **Step 5: Commit direct lens**

Run:

```bash
git add src/citeproof/qualitative_lens.py tests/test_qualitative_lens.py
git commit -m "feat: add qualitative conflict lens"
```

---

### Task 2: Integrate Lens And Add Regression Tests

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Modify: `src/citeproof/adjudicator.py`
- Modify: `tests/test_fact_lenses.py`
- Create: `tests/test_entailment_qualitative.py`

- [ ] **Step 1: Add fact-lens tests**

Append to `tests/test_fact_lenses.py`:

```python
def test_detects_qualitative_exclusivity_conflict() -> None:
    result = inspect_facts(
        "Method X is the only method evaluated on sparse-reward tasks.",
        "Method X is one of three methods evaluated on sparse-reward tasks.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Exclusivity conflict" in finding for finding in result.findings)


def test_detects_qualitative_scope_tension() -> None:
    result = inspect_facts(
        "Method X improves performance on all evaluated tasks.",
        "Method X improves performance on most evaluated tasks.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Scope tension" in finding for finding in result.findings)
```

- [ ] **Step 2: Add entailment regression tests**

Create `tests/test_entailment_qualitative.py`:

```python
from citeproof.entailment import judge_evidence
from citeproof.models import Label


def test_judge_evidence_does_not_support_only_vs_one_of() -> None:
    judgment = judge_evidence(
        "Method X is the only method evaluated on sparse-reward tasks.",
        "Method X is one of three methods evaluated on sparse-reward tasks.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_does_not_support_all_vs_most() -> None:
    judgment = judge_evidence(
        "Method X improves performance on all evaluated tasks.",
        "Method X improves performance on most evaluated tasks.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED


def test_judge_evidence_does_not_support_sota_negation() -> None:
    judgment = judge_evidence(
        "Method X achieves state-of-the-art accuracy on GLUE.",
        "Method X does not achieve state-of-the-art accuracy on GLUE.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_does_not_support_requirement_conflict() -> None:
    judgment = judge_evidence(
        "Method X requires no labeled data.",
        "Method X requires labeled data for training.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_does_not_support_architecture_swap() -> None:
    judgment = judge_evidence(
        "The policy uses a transformer architecture.",
        "The policy uses a convolutional architecture.",
    )

    assert judgment.label == Label.CONTRADICTED
```

- [ ] **Step 3: Run red integration tests**

Run:

```bash
python -m pytest tests/test_fact_lenses.py tests/test_entailment_qualitative.py -q -p no:cacheprovider
```

Expected: FAIL until `fact_lenses.py` calls the qualitative lens.

- [ ] **Step 4: Wire into `fact_lenses.py`**

Import:

```python
from citeproof.qualitative_lens import inspect_qualitative_conflicts, inspect_qualitative_tensions
```

Add to hard findings:

```python
        + list(inspect_qualitative_conflicts(claim, evidence))
```

After bound tensions and before comparison partial support, add:

```python
    qualitative_tensions = inspect_qualitative_tensions(claim, evidence)
    if qualitative_tensions:
        return FactInspection(Label.PARTIALLY_SUPPORTED, qualitative_tensions)
```

- [ ] **Step 5: Map qualitative failure modes**

In `src/citeproof/adjudicator.py::_fact_failure_mode`, add:

```python
    if "exclusivity conflict" in text or "scope tension" in text:
        return FailureMode.SCOPE_OVERSTATEMENT
    if (
        "significance conflict" in text
        or "state-of-the-art conflict" in text
        or "requirement conflict" in text
        or "descriptor conflict" in text
    ):
        return FailureMode.NEGATION_CONFLICT
```

- [ ] **Step 6: Run focused integration checks**

Run:

```bash
python -m pytest tests/test_qualitative_lens.py tests/test_fact_lenses.py tests/test_entailment_qualitative.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/qualitative_lens.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_qualitative_lens.py tests/test_fact_lenses.py tests/test_entailment_qualitative.py
git diff --check
wc -l src/citeproof/qualitative_lens.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_qualitative_lens.py tests/test_fact_lenses.py tests/test_entailment_qualitative.py
```

Expected: tests and ruff pass; files under 300 LOC.

- [ ] **Step 7: Commit integration**

Run:

```bash
git add src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_fact_lenses.py tests/test_entailment_qualitative.py
git commit -m "fix: block qualitative false support"
```

---

### Task 3: Expand Benchmark And Verify

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add benchmark rows**

Append:

```jsonl
{"id":"only-one-of-conflict","claim":"Method X is the only method evaluated on sparse-reward tasks.","evidence":"Method X is one of three methods evaluated on sparse-reward tasks.","expected_label":"contradicted","expected_failure_mode":"scope_overstatement"}
{"id":"all-most-scope-tension","claim":"Method X improves performance on all evaluated tasks.","evidence":"Method X improves performance on most evaluated tasks.","expected_label":"partially_supported"}
{"id":"sota-negation-conflict","claim":"Method X achieves state-of-the-art accuracy on GLUE.","evidence":"Method X does not achieve state-of-the-art accuracy on GLUE.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"requires-no-labels-conflict","claim":"Method X requires no labeled data.","evidence":"Method X requires labeled data for training.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"architecture-swap-conflict","claim":"The policy uses a transformer architecture.","evidence":"The policy uses a convolutional architecture.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"offline-online-conflict","claim":"The method uses offline reinforcement learning.","evidence":"The method uses online reinforcement learning.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"significance-negation-conflict","claim":"Method X significantly improves accuracy.","evidence":"Method X improves accuracy, but the improvement is not statistically significant.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
```

- [ ] **Step 2: Update eval runner expected IDs**

Add the expected-failure-mode IDs to `test_edge_cases_with_expected_failure_modes_pass`.

- [ ] **Step 3: Update docs**

Change edge total from `33` to `40` and add qualitative scope, significance,
requirement, and descriptor conflicts to the coverage sentence.

- [ ] **Step 4: Run full gate and commit**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl \
  --details-output /tmp/citeproof_qualitative_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output /tmp/citeproof_qualitative_hallucination.json
```

Expected:

- tests pass;
- ruff passes;
- primary eval total `4`, accuracy `1.0`, false-supported `0.0`;
- edge eval total `40`, accuracy `1.0`, false-supported `0.0`;
- hallucination eval total `5`, accuracy `1.0`, false-supported `0.0`.

Commit:

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add qualitative conflict edge cases"
```

---

### Task 4: Push And CI

- [ ] **Step 1: Push**

```bash
git push origin main
```

- [ ] **Step 2: Watch CI**

```bash
HEAD_SHA=$(git rev-parse HEAD)
gh run list --repo SebastianBoehler/citeproof --commit "$HEAD_SHA" \
  --limit 5 --json databaseId,headSha,status,conclusion,name,workflowName,createdAt,url
gh run watch <run-id> --repo SebastianBoehler/citeproof --exit-status
```

Expected: `tests` workflow succeeds on every configured Python version.
