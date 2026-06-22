# Method Design Attribute Conflicts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend CiteProof's controlled attribute lens so method-design swaps do not get labeled `supported`.

**Architecture:** Reuse `inspect_attribute_conflicts` by adding four controlled value groups. Update adjudicator mapping for the new conflict names, then add end-to-end and benchmark coverage.

**Tech Stack:** Python, pytest, ruff, existing CiteProof deterministic lens architecture.

---

## File Structure

- Modify `src/citeproof/attribute_lens.py`: add supervision, study design, summarization style, and agent-setting groups plus trigger words.
- Modify `tests/test_attribute_lens.py`: direct tests for new groups and one mixed-context boundary.
- Modify `src/citeproof/adjudicator.py`: map new conflict labels to `entity_conflict`.
- Create `tests/test_entailment_method_attributes.py`: end-to-end label and failure-mode tests.
- Modify `examples/edge_cases/claim_support.jsonl`: append four adversarial rows.
- Modify `tests/test_eval_runner.py`: require the four new expected failure-mode rows.
- Modify `docs/evaluation.md`: update benchmark total and coverage sentence.

## Task 1: Extend Attribute Lens

**Files:**
- Modify: `src/citeproof/attribute_lens.py`
- Modify: `tests/test_attribute_lens.py`

- [ ] **Step 1: Add failing direct tests**

Append to `tests/test_attribute_lens.py`:

```python
def test_detects_supervision_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The method uses supervised training.",
        "The method uses unsupervised training without labels.",
    )

    assert any("Supervision conflict" in finding for finding in findings)


def test_detects_study_design_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The study is randomized.",
        "The study is observational and not randomized.",
    )

    assert any("Study design conflict" in finding for finding in findings)


def test_detects_summarization_style_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The system performs abstractive summarization.",
        "The system performs extractive summarization.",
    )

    assert any("Summarization style conflict" in finding for finding in findings)


def test_detects_agent_setting_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The policy is trained in a multi-agent environment.",
        "The policy is trained in a single-agent environment.",
    )

    assert any("Agent setting conflict" in finding for finding in findings)


def test_ignores_method_attribute_terms_in_different_contexts() -> None:
    findings = inspect_attribute_conflicts(
        "The supervised baseline is reported in Table 1.",
        "The method uses unsupervised training.",
    )

    assert findings == ()
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_attribute_lens.py -q -p no:cacheprovider`

Expected: FAIL because the new groups are not implemented.

- [ ] **Step 3: Add controlled groups**

In `src/citeproof/attribute_lens.py`, add these `AttributeGroup` entries to `GROUPS`:

```python
AttributeGroup(
    "Supervision",
    (
        ("supervised", (r"\bsupervised\b", r"\blabeled\s+(?:data|examples|labels)\b")),
        ("unsupervised", (r"\bunsupervised\b", r"\bwithout\s+labels\b")),
    ),
),
AttributeGroup(
    "Study design",
    (
        ("randomized", (r"\brandomi[sz]ed\b", r"\brandomi[sz]ed\s+controlled\b")),
        ("observational", (r"\bobservational\b", r"\bnot\s+randomi[sz]ed\b")),
    ),
),
AttributeGroup(
    "Summarization style",
    (
        ("abstractive", (r"\babstractive\b",)),
        ("extractive", (r"\bextractive\b",)),
    ),
),
AttributeGroup(
    "Agent setting",
    (
        ("single-agent", (r"\bsingle[- ]agent\b",)),
        ("multi-agent", (r"\bmulti[- ]agent\b",)),
    ),
),
```

Extend `TRIGGER_WORDS_RE` with: `supervised`, `unsupervised`, `labeled`, `labels`, `randomized`, `randomised`, `observational`, `abstractive`, `extractive`, `single-agent`, `multi-agent`.

- [ ] **Step 4: Verify direct tests**

Run:

```bash
python -m pytest tests/test_attribute_lens.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/attribute_lens.py tests/test_attribute_lens.py
git diff --check
wc -l src/citeproof/attribute_lens.py tests/test_attribute_lens.py
```

Expected: all direct tests pass; both files remain under 300 LOC.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/attribute_lens.py tests/test_attribute_lens.py
git commit -m "feat: extend attribute conflict lens"
```

## Task 2: End-to-End Integration Mapping

**Files:**
- Modify: `src/citeproof/adjudicator.py`
- Create: `tests/test_entailment_method_attributes.py`

- [ ] **Step 1: Add failing end-to-end tests**

Create `tests/test_entailment_method_attributes.py`:

```python
import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The method uses supervised training.", "The method uses unsupervised training without labels."),
        ("The study is randomized.", "The study is observational and not randomized."),
        ("The system performs abstractive summarization.", "The system performs extractive summarization."),
        ("The policy is trained in a multi-agent environment.", "The policy is trained in a single-agent environment."),
    ],
)
def test_method_attribute_conflicts_are_not_supported(claim: str, evidence: str) -> None:
    judgment = judge_evidence(claim, evidence)

    assert judgment.label == Label.CONTRADICTED


def test_method_attribute_conflict_maps_to_entity_failure() -> None:
    judgment = adjudicate_evidence(
        "The method uses supervised training.",
        "The method uses unsupervised training without labels.",
    )

    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_entailment_method_attributes.py -q -p no:cacheprovider`

Expected: FAIL only on the failure-mode mapping if Task 1 is already implemented; otherwise labels may still be supported.

- [ ] **Step 3: Extend adjudicator mapping**

Add these strings to `ATTRIBUTE_ENTITY_CONFLICTS` in `src/citeproof/adjudicator.py`:

```python
"supervision conflict",
"study design conflict",
"summarization style conflict",
"agent setting conflict",
```

- [ ] **Step 4: Verify focused tests**

Run:

```bash
python -m pytest tests/test_attribute_lens.py tests/test_entailment_method_attributes.py tests/test_entailment_attributes.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/adjudicator.py tests/test_entailment_method_attributes.py
git diff --check
wc -l src/citeproof/adjudicator.py tests/test_entailment_method_attributes.py
```

Expected: all focused tests pass; files remain under 300 LOC.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/adjudicator.py tests/test_entailment_method_attributes.py
git commit -m "fix: map method attribute conflicts"
```

## Task 3: Benchmark and CI

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Append benchmark rows**

Append:

```jsonl
{"id":"supervision-method-conflict","claim":"The method uses supervised training.","evidence":"The method uses unsupervised training without labels.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"study-design-method-conflict","claim":"The study is randomized.","evidence":"The study is observational and not randomized.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"summarization-style-conflict","claim":"The system performs abstractive summarization.","evidence":"The system performs extractive summarization.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"agent-setting-conflict","claim":"The policy is trained in a multi-agent environment.","evidence":"The policy is trained in a single-agent environment.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
```

- [ ] **Step 2: Update eval runner and docs**

Add the four IDs to `test_edge_cases_with_expected_failure_modes_pass`. Change the edge-case total in `docs/evaluation.md` from `46` to `50` and mention method-design attribute conflicts in the coverage sentence.

- [ ] **Step 3: Run full gate**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_method_attribute_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output /tmp/citeproof_method_attribute_hallucination.json
git diff --check
```

Expected: full tests pass; edge eval reports total `50`, accuracy `1.0`, and `false_supported_rate` `0.0`.

- [ ] **Step 4: Commit, push, verify CI**

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add method attribute edge cases"
git push origin main
gh run list --repo SebastianBoehler/citeproof --branch main --limit 10 --json databaseId,headSha,status,conclusion,url
```

Expected: pushed SHA gets a successful `tests` workflow run.
