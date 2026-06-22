# Claim Strength Overstatement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent evidence for weaker claims from being labeled as full support for stronger academic claims.

**Architecture:** Add a focused `strength_lens` with hard conflicts for direct magnitude/no-overhead contradictions and partial-support tensions for causal, best, and full-recovery overstatements. Integrate conflicts into hard findings and tensions into partial-support findings.

**Tech Stack:** Python, pytest, ruff, existing CiteProof deterministic lens architecture.

---

## File Structure

- Create `src/citeproof/strength_lens.py`: `inspect_strength_conflicts` and `inspect_strength_tensions`.
- Create `tests/test_strength_lens.py`: direct tests and conservative boundaries.
- Modify `src/citeproof/fact_lenses.py`: append strength conflicts and tensions.
- Create `tests/test_entailment_strength.py`: end-to-end label and failure-mode tests.
- Modify `examples/edge_cases/claim_support.jsonl`: append seven adversarial rows.
- Modify `tests/test_eval_runner.py`: require the new expected failure-mode rows where present.
- Modify `docs/evaluation.md`: update benchmark total and coverage sentence.

## Task 1: Direct Strength Lens

**Files:**
- Create: `src/citeproof/strength_lens.py`
- Create: `tests/test_strength_lens.py`

- [ ] **Step 1: Add failing direct tests**

Create `tests/test_strength_lens.py`:

```python
from citeproof.strength_lens import inspect_strength_conflicts, inspect_strength_tensions


def test_detects_large_small_conflict() -> None:
    findings = inspect_strength_conflicts(
        "The method yields a large improvement.",
        "The method yields a small improvement.",
    )

    assert any("Magnitude conflict" in finding for finding in findings)


def test_detects_substantial_modest_conflict() -> None:
    findings = inspect_strength_conflicts(
        "The method yields substantial gains.",
        "The method yields modest gains.",
    )

    assert any("Magnitude conflict" in finding for finding in findings)


def test_detects_no_overhead_conflict() -> None:
    findings = inspect_strength_conflicts(
        "The method adds no computational overhead.",
        "The method adds small computational overhead.",
    )

    assert any("Overhead conflict" in finding for finding in findings)


def test_detects_causal_association_tension() -> None:
    findings = inspect_strength_tensions(
        "The intervention causes improved accuracy.",
        "The intervention is associated with improved accuracy.",
    )

    assert any("Causal overstatement" in finding for finding in findings)


def test_detects_best_competitive_tension() -> None:
    findings = inspect_strength_tensions(
        "The method achieves the best accuracy.",
        "The method achieves competitive accuracy.",
    )

    assert any("Ranking overstatement" in finding for finding in findings)


def test_detects_full_partial_tension() -> None:
    findings = inspect_strength_tensions(
        "The method fully recovers the signal.",
        "The method partially recovers the signal.",
    )

    assert any("Completeness overstatement" in finding for finding in findings)


def test_ignores_strength_terms_in_different_contexts() -> None:
    assert inspect_strength_conflicts(
        "The large model improves accuracy.",
        "The small baseline improves latency.",
    ) == ()
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_strength_lens.py -q -p no:cacheprovider`

Expected: FAIL because `citeproof.strength_lens` does not exist.

- [ ] **Step 3: Implement lens**

Create `src/citeproof/strength_lens.py` with conservative regex groups, shared context stripping, and:

```python
def inspect_strength_conflicts(claim: str, evidence: str) -> tuple[str, ...]: ...
def inspect_strength_tensions(claim: str, evidence: str) -> tuple[str, ...]: ...
```

Hard conflicts:

- claim `large|substantial` and evidence `small|modest`
- claim `no ... overhead` and evidence `small|some|nonzero ... overhead`

Tensions:

- claim `causes|caused|proves|demonstrates` and evidence `associated|correlated|suggests|may`
- claim `best|top-performing|highest` and evidence `competitive|comparable`
- claim `fully|completely` with `recovers|reconstructs|restores` and evidence `partially|partial`

- [ ] **Step 4: Verify direct tests**

Run:

```bash
python -m pytest tests/test_strength_lens.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/strength_lens.py tests/test_strength_lens.py
git diff --check
wc -l src/citeproof/strength_lens.py tests/test_strength_lens.py
```

Expected: all tests pass; both files remain under 300 LOC.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/strength_lens.py tests/test_strength_lens.py
git commit -m "feat: add claim strength lens"
```

## Task 2: Integration and End-to-End Tests

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Create: `tests/test_entailment_strength.py`

- [ ] **Step 1: Add failing end-to-end tests**

Create `tests/test_entailment_strength.py`:

```python
import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The method yields a large improvement.", "The method yields a small improvement."),
        ("The method yields substantial gains.", "The method yields modest gains."),
        ("The method adds no computational overhead.", "The method adds small computational overhead."),
    ],
)
def test_strength_conflicts_are_contradicted(claim: str, evidence: str) -> None:
    assert judge_evidence(claim, evidence).label == Label.CONTRADICTED


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The intervention causes improved accuracy.", "The intervention is associated with improved accuracy."),
        ("The variable causes higher mortality.", "The variable is correlated with higher mortality."),
        ("The method achieves the best accuracy.", "The method achieves competitive accuracy."),
        ("The method fully recovers the signal.", "The method partially recovers the signal."),
    ],
)
def test_strength_tensions_are_partial(claim: str, evidence: str) -> None:
    assert judge_evidence(claim, evidence).label == Label.PARTIALLY_SUPPORTED


def test_strength_tension_maps_to_scope_overstatement() -> None:
    judgment = adjudicate_evidence(
        "The intervention causes improved accuracy.",
        "The intervention is associated with improved accuracy.",
    )

    assert judgment.failure_mode == FailureMode.SCOPE_OVERSTATEMENT
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_entailment_strength.py -q -p no:cacheprovider`

Expected: FAIL because `fact_lenses` does not call `strength_lens`.

- [ ] **Step 3: Integrate**

In `src/citeproof/fact_lenses.py`, import `inspect_strength_conflicts` and `inspect_strength_tensions`. Append conflicts to `hard_findings` and append tensions to `tension_findings`.

- [ ] **Step 4: Verify focused tests**

Run:

```bash
python -m pytest tests/test_strength_lens.py tests/test_entailment_strength.py tests/test_fact_lenses.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/fact_lenses.py tests/test_entailment_strength.py
git diff --check
wc -l src/citeproof/fact_lenses.py tests/test_entailment_strength.py
```

Expected: all tests pass; files remain under 300 LOC.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/fact_lenses.py tests/test_entailment_strength.py
git commit -m "fix: block claim strength false support"
```

## Task 3: Benchmark and CI

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Append benchmark rows**

Append:

```jsonl
{"id":"large-small-strength-conflict","claim":"The method yields a large improvement.","evidence":"The method yields a small improvement.","expected_label":"contradicted"}
{"id":"substantial-modest-strength-conflict","claim":"The method yields substantial gains.","evidence":"The method yields modest gains.","expected_label":"contradicted"}
{"id":"no-overhead-strength-conflict","claim":"The method adds no computational overhead.","evidence":"The method adds small computational overhead.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"causal-association-strength-tension","claim":"The intervention causes improved accuracy.","evidence":"The intervention is associated with improved accuracy.","expected_label":"partially_supported"}
{"id":"causal-correlation-strength-tension","claim":"The variable causes higher mortality.","evidence":"The variable is correlated with higher mortality.","expected_label":"partially_supported"}
{"id":"best-competitive-strength-tension","claim":"The method achieves the best accuracy.","evidence":"The method achieves competitive accuracy.","expected_label":"partially_supported"}
{"id":"full-partial-strength-tension","claim":"The method fully recovers the signal.","evidence":"The method partially recovers the signal.","expected_label":"partially_supported"}
```

- [ ] **Step 2: Update docs**

Change the edge-case total in `docs/evaluation.md` from `63` to `70` and mention claim-strength overstatements in the coverage sentence.

- [ ] **Step 3: Run full gate**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_strength_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output /tmp/citeproof_strength_hallucination.json
git diff --check
```

Expected: full tests pass; edge eval reports total `70`, accuracy `1.0`, and `false_supported_rate` `0.0`.

- [ ] **Step 4: Commit, push, verify CI**

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add claim strength edge cases"
git push origin main
gh run list --repo SebastianBoehler/citeproof --branch main --limit 10 --json databaseId,headSha,status,conclusion,url
```

Expected: pushed SHA gets a successful `tests` workflow run.
