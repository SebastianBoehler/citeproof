# Context Limitation Lens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent limited-context evidence from producing false `supported` labels for broader academic claims.

**Architecture:** Add a focused `context_lens` module that emits partial-support tensions for limited evidence and hard conflicts for component-exclusion evidence. Wire it through `inspect_facts`, map component exclusions to negation-style failure mode, and expand the edge benchmark.

**Tech Stack:** Python 3.11+, pytest, ruff, existing CiteProof deterministic fact-lens architecture.

---

## File Structure

- Create `src/citeproof/context_lens.py`: controlled context-limit and component-exclusion checks.
- Create `tests/test_context_lens.py`: direct unit tests and supported guards.
- Create `tests/test_entailment_context.py`: final adjudication labels and failure modes.
- Modify `src/citeproof/fact_lenses.py`: include context tensions and component conflicts.
- Modify `src/citeproof/adjudicator.py`: map component-exclusion conflicts to `negation_conflict`.
- Modify `examples/edge_cases/claim_support.jsonl`, `tests/test_eval_runner.py`, and `docs/evaluation.md`: benchmark rows and score docs.

---

### Task 1: Direct Context Lens

**Files:**
- Create: `src/citeproof/context_lens.py`
- Create: `tests/test_context_lens.py`

- [ ] **Step 1: Write failing direct tests**

Create `tests/test_context_lens.py`:

```python
import pytest

from citeproof.context_lens import (
    inspect_component_exclusion_conflicts,
    inspect_context_tensions,
)


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        (
            "The method improves accuracy.",
            "The method improves accuracy only when oracle labels are available.",
        ),
        (
            "The method reduces latency.",
            "The method reduces latency in the simulated setting but not on hardware.",
        ),
        (
            "The model improves performance on ImageNet.",
            "The model improves performance on a 1% ImageNet subset.",
        ),
        (
            "The drug reduces inflammation in humans.",
            "The drug reduces inflammation in mice.",
        ),
        (
            "The drug reduces tumor size in patients.",
            "The drug reduces tumor size in vitro.",
        ),
        (
            "The tool improves productivity.",
            "In one case study, the tool improves productivity.",
        ),
    ],
)
def test_detects_context_limitations(claim: str, evidence: str) -> None:
    findings = inspect_context_tensions(claim, evidence)

    assert any("Context limitation" in finding for finding in findings)


def test_ignores_matching_simulation_scope() -> None:
    assert inspect_context_tensions(
        "The method reduces latency in simulation.",
        "The method reduces latency in simulation.",
    ) == ()


def test_ignores_matching_case_study_scope() -> None:
    assert inspect_context_tensions(
        "The tool improves productivity in one case study.",
        "In one case study, the tool improves productivity.",
    ) == ()


def test_detects_component_exclusion_conflict() -> None:
    findings = inspect_component_exclusion_conflicts(
        "Retrieval improves factuality.",
        "The no-retrieval ablation improves factuality over the baseline.",
    )

    assert any("Component exclusion conflict" in finding for finding in findings)


def test_ignores_matching_component_exclusion() -> None:
    assert inspect_component_exclusion_conflicts(
        "The no-retrieval ablation improves factuality.",
        "The no-retrieval ablation improves factuality over the baseline.",
    ) == ()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/test_context_lens.py -q -p no:cacheprovider
```

Expected: import failure because `citeproof.context_lens` does not exist.

- [ ] **Step 3: Implement context lens**

Create `src/citeproof/context_lens.py` with:

```python
"""Context limitation and component exclusion checks."""

from __future__ import annotations

import re

from citeproof.text import tokenize


def inspect_context_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return partial-support findings for evidence narrower than the claim."""
    findings: list[str] = []
    if _evidence_is_limited_beyond_claim(claim, evidence):
        findings.append("Context limitation: evidence supports a narrower setting than the claim.")
    if _setting_mismatch(claim, evidence):
        findings.append("Context limitation: evidence is from a different population or setting.")
    return tuple(dict.fromkeys(findings))


def inspect_component_exclusion_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts where evidence excludes the claimed component."""
    findings: list[str] = []
    for component in _claimed_result_components(claim):
        if _component_excluded(component, evidence) and _context_overlaps(claim, evidence, {component}):
            findings.append(
                "Component exclusion conflict: evidence excludes the component credited by the claim."
            )
    return tuple(dict.fromkeys(findings))
```

Use controlled regexes for condition, subset, case-study, setting, population,
and component-exclusion cues. Keep helper functions private.

- [ ] **Step 4: Run direct tests and lint**

Run:

```bash
python -m pytest tests/test_context_lens.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/context_lens.py tests/test_context_lens.py
git diff --check
```

Expected: direct tests pass and ruff is clean.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/context_lens.py tests/test_context_lens.py
git commit -m "feat: add context limitation lens"
```

---

### Task 2: Integrate Context Lens

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Modify: `src/citeproof/adjudicator.py`
- Create: `tests/test_entailment_context.py`

- [ ] **Step 1: Write failing adjudication tests**

Create `tests/test_entailment_context.py`:

```python
import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The method improves accuracy.", "The method improves accuracy only when oracle labels are available."),
        ("The model improves performance on ImageNet.", "The model improves performance on a 1% ImageNet subset."),
        ("The drug reduces inflammation in humans.", "The drug reduces inflammation in mice."),
    ],
)
def test_context_limitations_block_full_support(claim: str, evidence: str) -> None:
    judgment = adjudicate_evidence(claim, evidence)

    assert judgment.label == Label.PARTIALLY_SUPPORTED
    assert judgment.failure_mode == FailureMode.SCOPE_OVERSTATEMENT


def test_component_exclusion_blocks_support() -> None:
    judgment = adjudicate_evidence(
        "Retrieval improves factuality.",
        "The no-retrieval ablation improves factuality over the baseline.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/test_entailment_context.py -q -p no:cacheprovider
```

Expected: failures because `inspect_facts` does not use the lens yet.

- [ ] **Step 3: Wire into fact lenses**

In `src/citeproof/fact_lenses.py`, import:

```python
from citeproof.context_lens import (
    inspect_component_exclusion_conflicts,
    inspect_context_tensions,
)
```

Add component-exclusion conflicts to `hard_findings`, and context tensions to
`tension_findings`.

- [ ] **Step 4: Map failure mode**

In `src/citeproof/adjudicator.py`, add:

```python
if "component exclusion conflict" in text:
    return FailureMode.NEGATION_CONFLICT
```

- [ ] **Step 5: Run focused tests and commit**

Run:

```bash
python -m pytest tests/test_context_lens.py tests/test_entailment_context.py tests/test_fact_lenses.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_entailment_context.py
git diff --check
```

Expected: focused integration passes. Commit:

```bash
git add src/citeproof/fact_lenses.py src/citeproof/adjudicator.py tests/test_entailment_context.py
git commit -m "fix: block context limitation false support"
```

---

### Task 3: Benchmark and Docs

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add benchmark rows**

Append to `examples/edge_cases/claim_support.jsonl`:

```jsonl
{"id":"oracle-condition-context-tension","claim":"The method improves accuracy.","evidence":"The method improves accuracy only when oracle labels are available.","expected_label":"partially_supported"}
{"id":"simulation-hardware-context-tension","claim":"The method reduces latency.","evidence":"The method reduces latency in the simulated setting but not on hardware.","expected_label":"partially_supported"}
{"id":"subset-context-tension","claim":"The model improves performance on ImageNet.","evidence":"The model improves performance on a 1% ImageNet subset.","expected_label":"partially_supported"}
{"id":"human-animal-context-tension","claim":"The drug reduces inflammation in humans.","evidence":"The drug reduces inflammation in mice.","expected_label":"partially_supported"}
{"id":"patient-invitro-context-tension","claim":"The drug reduces tumor size in patients.","evidence":"The drug reduces tumor size in vitro.","expected_label":"partially_supported"}
{"id":"case-study-context-tension","claim":"The tool improves productivity.","evidence":"In one case study, the tool improves productivity.","expected_label":"partially_supported"}
{"id":"component-exclusion-conflict","claim":"Retrieval improves factuality.","evidence":"The no-retrieval ablation improves factuality over the baseline.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"simulation-context-support","claim":"The method reduces latency in simulation.","evidence":"The method reduces latency in simulation.","expected_label":"supported"}
{"id":"case-study-context-support","claim":"The tool improves productivity in one case study.","evidence":"In one case study, the tool improves productivity.","expected_label":"supported"}
```

- [ ] **Step 2: Update expected failure mode set**

In `tests/test_eval_runner.py`, add:

```python
"component-exclusion-conflict",
```

- [ ] **Step 3: Update docs**

Update `docs/evaluation.md` edge total from `82` to `91` and add
`context-limitation tensions` and `component-exclusion conflicts` to the coverage
sentence.

- [ ] **Step 4: Full verification**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_context_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output /tmp/citeproof_context_hallucination.json
git diff --check
```

Expected: tests and ruff pass, edge eval total is `91`, and all evals have
`false_supported_rate = 0.0`.

- [ ] **Step 5: Commit, push, watch CI**

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_eval_runner.py docs/evaluation.md
git commit -m "test: add context limitation edge cases"
git push origin main
run_id=$(gh run list --repo SebastianBoehler/citeproof --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$run_id" --repo SebastianBoehler/citeproof --exit-status
```

Expected: GitHub Actions succeeds on the pushed head SHA.
