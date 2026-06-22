# Statistical Reporting Conflicts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic statistical-reporting conflict detection so high-overlap statistical claim swaps do not get labeled `supported`.

**Architecture:** Create a focused `statistical_lens` with controlled groups and conservative context-overlap checks. Integrate it into `fact_lenses` hard findings and map findings to the existing `entity_conflict` failure mode.

**Tech Stack:** Python, pytest, ruff, existing CiteProof deterministic lens architecture.

---

## File Structure

- Create `src/citeproof/statistical_lens.py`: controlled statistical-reporting groups and `inspect_statistical_conflicts`.
- Create `tests/test_statistical_lens.py`: direct tests and conservative boundaries.
- Modify `src/citeproof/fact_lenses.py`: append statistical conflicts to hard findings.
- Modify `src/citeproof/adjudicator.py`: map statistical findings to `entity_conflict`.
- Create `tests/test_entailment_statistical.py`: end-to-end label and failure-mode tests.
- Modify `examples/edge_cases/claim_support.jsonl`: append seven adversarial rows.
- Modify `tests/test_eval_runner.py`: require the seven new failure-mode rows.
- Modify `docs/evaluation.md`: update benchmark total and coverage sentence.

## Task 1: Direct Statistical Lens

**Files:**
- Create: `src/citeproof/statistical_lens.py`
- Create: `tests/test_statistical_lens.py`

- [ ] **Step 1: Add failing direct tests**

Create `tests/test_statistical_lens.py`:

```python
from citeproof.statistical_lens import inspect_statistical_conflicts


def test_detects_confidence_interval_relation_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The confidence interval excludes zero.",
        "The 95% confidence interval includes zero.",
    )

    assert any("Confidence interval conflict" in finding for finding in findings)


def test_detects_f1_averaging_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The system improves macro-F1.",
        "The system improves micro-F1.",
    )

    assert any("F1 averaging conflict" in finding for finding in findings)


def test_detects_summary_statistic_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The paper reports median latency.",
        "The paper reports mean latency.",
    )

    assert any("Summary statistic conflict" in finding for finding in findings)


def test_detects_uncertainty_statistic_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The error bars show standard deviation.",
        "The error bars show standard error.",
    )

    assert any("Uncertainty statistic conflict" in finding for finding in findings)


def test_detects_pairedness_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The test uses a paired bootstrap.",
        "The test uses an unpaired bootstrap.",
    )

    assert any("Pairedness conflict" in finding for finding in findings)


def test_detects_tail_count_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The analysis uses a one-tailed test.",
        "The analysis uses a two-tailed test.",
    )

    assert any("Tail count conflict" in finding for finding in findings)


def test_detects_test_family_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The method uses a parametric test.",
        "The method uses a nonparametric test.",
    )

    assert any("Test family conflict" in finding for finding in findings)


def test_ignores_evidence_with_claim_value_plus_extra_value() -> None:
    findings = inspect_statistical_conflicts(
        "The paper reports median latency.",
        "The paper reports median latency and mean latency.",
    )

    assert findings == ()


def test_ignores_statistical_terms_in_different_contexts() -> None:
    findings = inspect_statistical_conflicts(
        "The macro scheduler improves throughput.",
        "The system improves micro-F1.",
    )

    assert findings == ()
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_statistical_lens.py -q -p no:cacheprovider`

Expected: FAIL because `citeproof.statistical_lens` does not exist.

- [ ] **Step 3: Implement lens**

Create `src/citeproof/statistical_lens.py` with controlled groups for:

```python
("Confidence interval", ("includes zero", "excludes zero"))
("F1 averaging", ("macro-F1", "micro-F1"))
("Summary statistic", ("mean", "median"))
("Uncertainty statistic", ("standard deviation", "standard error"))
("Pairedness", ("paired", "unpaired"))
("Tail count", ("one-tailed", "two-tailed"))
("Test family", ("parametric", "nonparametric"))
```

Use the same conservative disjoint-value and context-overlap pattern as the
existing property lenses.

- [ ] **Step 4: Verify direct tests**

Run:

```bash
python -m pytest tests/test_statistical_lens.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/statistical_lens.py tests/test_statistical_lens.py
git diff --check
wc -l src/citeproof/statistical_lens.py tests/test_statistical_lens.py
```

Expected: all tests pass; both files remain under 300 LOC.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/statistical_lens.py tests/test_statistical_lens.py
git commit -m "feat: add statistical reporting lens"
```

## Task 2: Integration and End-to-End Tests

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Modify: `src/citeproof/adjudicator.py`
- Create: `tests/test_entailment_statistical.py`

- [ ] **Step 1: Add failing end-to-end tests**

Create `tests/test_entailment_statistical.py`:

```python
import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The confidence interval excludes zero.", "The 95% confidence interval includes zero."),
        ("The system improves macro-F1.", "The system improves micro-F1."),
        ("The paper reports median latency.", "The paper reports mean latency."),
        ("The error bars show standard deviation.", "The error bars show standard error."),
        ("The test uses a paired bootstrap.", "The test uses an unpaired bootstrap."),
        ("The analysis uses a one-tailed test.", "The analysis uses a two-tailed test."),
        ("The method uses a parametric test.", "The method uses a nonparametric test."),
    ],
)
def test_statistical_conflicts_are_not_supported(claim: str, evidence: str) -> None:
    judgment = judge_evidence(claim, evidence)

    assert judgment.label == Label.CONTRADICTED


def test_statistical_conflict_maps_to_entity_failure() -> None:
    judgment = adjudicate_evidence(
        "The paper reports median latency.",
        "The paper reports mean latency.",
    )

    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_entailment_statistical.py -q -p no:cacheprovider`

Expected: FAIL because integration is missing.

- [ ] **Step 3: Integrate hard findings**

Import `inspect_statistical_conflicts` in `src/citeproof/fact_lenses.py` and append its findings to `hard_findings` after technical property conflicts.

- [ ] **Step 4: Map failure modes**

In `src/citeproof/adjudicator.py`, add a `STATISTICAL_CONFLICTS` tuple with the lower-case conflict labels and map them to `FailureMode.ENTITY_CONFLICT` in `_fact_failure_mode`.

- [ ] **Step 5: Verify focused tests**

Run:

```bash
python -m pytest tests/test_statistical_lens.py tests/test_entailment_statistical.py tests/test_fact_lenses.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_entailment_statistical.py
git diff --check
wc -l src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_entailment_statistical.py
```

Expected: all tests pass; files remain under 300 LOC.

- [ ] **Step 6: Commit**

```bash
git add src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_entailment_statistical.py
git commit -m "fix: block statistical reporting false support"
```

## Task 3: Benchmark and CI

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Append benchmark rows**

Append:

```jsonl
{"id":"ci-zero-statistical-conflict","claim":"The confidence interval excludes zero.","evidence":"The 95% confidence interval includes zero.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"f1-averaging-statistical-conflict","claim":"The system improves macro-F1.","evidence":"The system improves micro-F1.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"summary-statistical-conflict","claim":"The paper reports median latency.","evidence":"The paper reports mean latency.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"uncertainty-statistical-conflict","claim":"The error bars show standard deviation.","evidence":"The error bars show standard error.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"pairedness-statistical-conflict","claim":"The test uses a paired bootstrap.","evidence":"The test uses an unpaired bootstrap.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"tail-count-statistical-conflict","claim":"The analysis uses a one-tailed test.","evidence":"The analysis uses a two-tailed test.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"test-family-statistical-conflict","claim":"The method uses a parametric test.","evidence":"The method uses a nonparametric test.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
```

- [ ] **Step 2: Update eval runner and docs**

Add the seven IDs to `test_edge_cases_with_expected_failure_modes_pass`. Change the edge-case total in `docs/evaluation.md` from `56` to `63` and mention statistical reporting conflicts in the coverage sentence.

- [ ] **Step 3: Run full gate**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_statistical_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output /tmp/citeproof_statistical_hallucination.json
git diff --check
```

Expected: full tests pass; edge eval reports total `63`, accuracy `1.0`, and `false_supported_rate` `0.0`.

- [ ] **Step 4: Commit, push, verify CI**

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add statistical reporting edge cases"
git push origin main
gh run list --repo SebastianBoehler/citeproof --branch main --limit 10 --json databaseId,headSha,status,conclusion,url
```

Expected: pushed SHA gets a successful `tests` workflow run.
