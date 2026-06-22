# Outcome Protocol Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block newly verified false-supported academic claim cases involving outcome status, mixed effects, lower-is-better metrics, and protocol/measurement-slot conflicts.

**Architecture:** Add two focused deterministic lenses, `outcome_lens.py` and `protocol_lens.py`, and integrate them through `fact_lenses.inspect_facts`. Hard conflicts return `contradicted`; narrower or target-swapped evidence returns `partially_supported`. Existing labels and public APIs stay unchanged.

**Tech Stack:** Python 3.13-compatible stdlib regex/dataclasses, existing `citeproof.models`, existing pytest/ruff/uv workflow.

---

## File Structure

- Create `src/citeproof/outcome_lens.py`: controlled outcome status and mixed-effect checks.
- Create `src/citeproof/protocol_lens.py`: controlled academic protocol and measurement-slot checks.
- Modify `src/citeproof/fact_lenses.py`: call new hard-conflict and tension functions.
- Modify `src/citeproof/adjudicator.py`: map new finding text to existing failure modes.
- Create `tests/test_outcome_lens.py`: direct outcome lens unit tests.
- Create `tests/test_protocol_lens.py`: direct protocol lens unit tests.
- Create `tests/test_entailment_outcome_protocol.py`: integration tests via `judge_evidence`.
- Modify `tests/test_eval_runner.py`: include new expected failure-mode edge IDs.
- Modify `examples/edge_cases/claim_support.jsonl`: append adversarial rows.
- Modify `docs/evaluation.md`: update edge-case total and coverage wording.

## Task 1: Outcome Lens Tests

**Files:**
- Create: `tests/test_outcome_lens.py`
- Test: `tests/test_outcome_lens.py`

- [ ] **Step 1: Write direct failing tests**

```python
from citeproof.models import Label
from citeproof.outcome_lens import (
    inspect_outcome_conflicts,
    inspect_outcome_tensions,
)


def test_specific_outcome_unchanged_blocks_support() -> None:
    findings = inspect_outcome_conflicts(
        "The method improves calibration.",
        "The method improves accuracy, but calibration is unchanged.",
    )

    assert any("Outcome status conflict" in finding for finding in findings)


def test_no_change_for_resource_outcome_blocks_support() -> None:
    findings = inspect_outcome_conflicts(
        "The system reduces latency.",
        "The system reduces memory use, but latency shows no change.",
    )

    assert any("Outcome status conflict" in finding for finding in findings)


def test_lower_is_better_metric_direction_blocks_support() -> None:
    findings = inspect_outcome_conflicts(
        "DenoiseNet improves mean absolute error over Baseline.",
        "DenoiseNet reports a higher mean absolute error than Baseline.",
    )

    assert any("Lower-is-better outcome conflict" in finding for finding in findings)


def test_mixed_effects_are_partial_not_hard_conflicts() -> None:
    conflicts = inspect_outcome_conflicts(
        "The method reduces hallucinations.",
        "The method reduces hallucinations on short answers but increases hallucinations on long answers.",
    )
    tensions = inspect_outcome_tensions(
        "The method reduces hallucinations.",
        "The method reduces hallucinations on short answers but increases hallucinations on long answers.",
    )

    assert conflicts == ()
    assert any("Mixed outcome effect" in finding for finding in tensions)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_outcome_lens.py -q`

Expected: import failure for missing `citeproof.outcome_lens`.

## Task 2: Outcome Lens Implementation

**Files:**
- Create: `src/citeproof/outcome_lens.py`
- Test: `tests/test_outcome_lens.py`

- [ ] **Step 1: Implement controlled outcome checks**

Create `src/citeproof/outcome_lens.py` with:

```python
"""Outcome status and mixed-effect checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class OutcomeTerm:
    name: str
    patterns: tuple[str, ...]
    lower_is_better: bool = False


OUTCOMES = (
    OutcomeTerm("accuracy", (r"\baccuracy\b",)),
    OutcomeTerm("calibration", (r"\bcalibration\b",)),
    OutcomeTerm("discrimination", (r"\bdiscrimination\b",)),
    OutcomeTerm("factuality", (r"\bfactuality\b",)),
    OutcomeTerm("hallucinations", (r"\bhallucinations?\b",), lower_is_better=True),
    OutcomeTerm("latency", (r"\blatency\b",), lower_is_better=True),
    OutcomeTerm("mean absolute error", (r"\bmean\s+absolute\s+error\b", r"\bmae\b"), True),
    OutcomeTerm("loss", (r"\bloss\b",), True),
    OutcomeTerm("perplexity", (r"\bperplexity\b",), True),
    OutcomeTerm("mortality", (r"\bmortality\b",), True),
    OutcomeTerm("readmissions", (r"\breadmissions?\b",), True),
)

RESULT_RE = re.compile(
    r"\b(improves?|improved|reduces?|reduced|decreases?|decreased|lowers?|lowered)\b",
    re.IGNORECASE,
)
NO_CHANGE_RE = re.compile(
    r"\b("
    r"unchanged|no\s+change|shows?\s+no\s+change|no\s+difference|"
    r"no\s+(?:statistically\s+significant\s+)?(?:improvement|reduction)|"
    r"does\s+not\s+(?:improve|reduce|decrease)|did\s+not\s+(?:improve|reduce|decrease)"
    r")\b",
    re.IGNORECASE,
)
IMPROVE_RE = re.compile(r"\b(improves?|improved|increases?|increased|higher|better)\b", re.IGNORECASE)
WORSEN_RE = re.compile(r"\b(worsens?|worse|reduces?|reduced|decreases?|decreased|lowers?|lowered)\b", re.IGNORECASE)
HIGHER_RE = re.compile(r"\b(higher|increased?|larger|greater)\b", re.IGNORECASE)
MIXED_CUE_RE = re.compile(r"\b(but|whereas|while|although|however)\b", re.IGNORECASE)
VALUE_TERMS_RE = re.compile(
    r"\b("
    r"accuracy|calibration|decreas(?:e|es|ed)|discrimination|factuality|greater|"
    r"hallucinations?|higher|improv(?:e|es|ed)|increas(?:e|es|ed)|larger|latency|"
    r"loss|lowers?|lowered|mae|mean\s+absolute\s+error|mortality|perplexity|"
    r"readmissions?|reduc(?:e|es|ed)|unchanged|worse|worsens?"
    r")\b",
    re.IGNORECASE,
)


def inspect_outcome_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts for outcome status or direction."""

    if not RESULT_RE.search(claim):
        return ()
    findings: list[str] = []
    claim_outcomes = _mentioned_outcomes(claim)
    evidence_outcomes = _mentioned_outcomes(evidence)
    shared = claim_outcomes & evidence_outcomes
    for outcome in sorted(shared):
        if _outcome_has_no_change(outcome, evidence):
            findings.append(
                f"Outcome status conflict: claim asserts a result for {outcome} while evidence says it is unchanged."
            )
        if _lower_is_better(outcome) and _outcome_has_higher_direction(outcome, evidence):
            findings.append(
                f"Lower-is-better outcome conflict: evidence reports higher {outcome} against an improvement claim."
            )
    return tuple(dict.fromkeys(finding for finding in findings if _context_overlaps(claim, evidence)))


def inspect_outcome_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return partial-support findings for mixed effects on the claimed outcome."""

    if not RESULT_RE.search(claim) or not MIXED_CUE_RE.search(evidence):
        return ()
    shared = _mentioned_outcomes(claim) & _mentioned_outcomes(evidence)
    findings: list[str] = []
    for outcome in sorted(shared):
        if _has_mixed_effect(outcome, evidence):
            findings.append(
                f"Mixed outcome effect: evidence supports {outcome} in one setting but reports the opposite in another."
            )
    return tuple(dict.fromkeys(finding for finding in findings if _context_overlaps(claim, evidence)))


def _mentioned_outcomes(text: str) -> set[str]:
    outcomes: set[str] = set()
    for outcome in OUTCOMES:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in outcome.patterns):
            outcomes.add(outcome.name)
    return outcomes


def _outcome_has_no_change(outcome: str, text: str) -> bool:
    return any(NO_CHANGE_RE.search(window) for window in _outcome_windows(outcome, text))


def _outcome_has_higher_direction(outcome: str, text: str) -> bool:
    return any(HIGHER_RE.search(window) for window in _outcome_windows(outcome, text))


def _has_mixed_effect(outcome: str, text: str) -> bool:
    windows = _outcome_windows(outcome, text)
    return any(IMPROVE_RE.search(window) for window in windows) and any(
        WORSEN_RE.search(window) for window in windows
    )


def _outcome_windows(outcome: str, text: str) -> tuple[str, ...]:
    outcome_patterns = next(item.patterns for item in OUTCOMES if item.name == outcome)
    windows: list[str] = []
    for pattern in outcome_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 72)
            end = min(len(text), match.end() + 72)
            windows.append(text[start:end])
    return tuple(windows)


def _lower_is_better(outcome: str) -> bool:
    return next(item.lower_is_better for item in OUTCOMES if item.name == outcome)


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.5


def _context_tokens(text: str) -> set[str]:
    return set(tokenize(VALUE_TERMS_RE.sub(" ", text)))
```

- [ ] **Step 2: Run direct tests**

Run: `uv run pytest tests/test_outcome_lens.py -q`

Expected: all tests pass.

## Task 3: Protocol Lens Tests

**Files:**
- Create: `tests/test_protocol_lens.py`
- Test: `tests/test_protocol_lens.py`

- [ ] **Step 1: Write direct failing tests**

```python
from citeproof.protocol_lens import (
    inspect_protocol_conflicts,
    inspect_protocol_tensions,
)


def test_multiple_comparison_correction_conflict() -> None:
    findings = inspect_protocol_conflicts(
        "The analysis used Bonferroni correction as the multiple-comparison adjustment.",
        "The analysis used Benjamini-Hochberg correction as the multiple-comparison adjustment.",
    )

    assert any("Protocol conflict" in finding for finding in findings)


def test_train_test_leakage_conflict() -> None:
    findings = inspect_protocol_conflicts(
        "Benchmark-Z uses disjoint train and test patients.",
        "Benchmark-Z uses the same patients in the train and test sets.",
    )

    assert any("Protocol conflict" in finding for finding in findings)


def test_commercial_use_availability_conflict() -> None:
    findings = inspect_protocol_conflicts(
        "The dataset permits commercial use.",
        "The dataset is restricted to non-commercial research use.",
    )

    assert any("Protocol conflict" in finding for finding in findings)


def test_endpoint_swap_is_partial_support() -> None:
    conflicts = inspect_protocol_conflicts(
        "Drug A improves the primary endpoint.",
        "Drug A improves the secondary endpoint.",
    )
    tensions = inspect_protocol_tensions(
        "Drug A improves the primary endpoint.",
        "Drug A improves the secondary endpoint.",
    )

    assert conflicts == ()
    assert any("Measurement target tension" in finding for finding in tensions)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_protocol_lens.py -q`

Expected: import failure for missing `citeproof.protocol_lens`.

## Task 4: Protocol Lens Implementation

**Files:**
- Create: `src/citeproof/protocol_lens.py`
- Test: `tests/test_protocol_lens.py`

- [ ] **Step 1: Implement controlled protocol checks**

Create `src/citeproof/protocol_lens.py` with:

```python
"""Academic protocol and measurement-slot checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class ProtocolGroup:
    label: str
    values: tuple[tuple[str, tuple[str, ...]], ...]


CONFLICT_GROUPS = (
    ProtocolGroup(
        "Correction method",
        (
            ("Bonferroni", (r"\bbonferroni\b",)),
            ("Benjamini-Hochberg", (r"\bbenjamini[- ]hochberg\b", r"\bfdr\b")),
            ("Holm", (r"\bholm\b",)),
        ),
    ),
    ProtocolGroup(
        "Blinding",
        (
            ("blinded", (r"\bblinded\b", r"\bmasked\b")),
            ("unblinded", (r"\bunblinded\b", r"\bnot\s+blinded\b", r"\bopen[- ]label\b")),
        ),
    ),
    ProtocolGroup(
        "Study temporality",
        (
            ("prospective", (r"\bprospective\b",)),
            ("retrospective", (r"\bretrospective\b",)),
        ),
    ),
    ProtocolGroup(
        "Architecture",
        (
            ("encoder-only", (r"\bencoder[- ]only\b",)),
            ("decoder-only", (r"\bdecoder[- ]only\b",)),
            ("encoder-decoder", (r"\bencoder[- ]decoder\b", r"\bseq2seq\b")),
        ),
    ),
    ProtocolGroup(
        "Train-test relation",
        (
            ("disjoint", (r"\bdisjoint\b", r"\bheld[- ]out\b", r"\bno\s+overlap\b")),
            ("overlapping", (r"\bsame\s+(?:patients?|examples?|samples?)\b", r"\boverlap(?:ping)?\b")),
        ),
    ),
    ProtocolGroup(
        "Duplicate preprocessing",
        (
            ("removes duplicates", (r"\bremov(?:e|es|ed)\s+duplicate", r"\bdeduplicat(?:e|es|ed)")),
            ("retains duplicates", (r"\bretain(?:s|ed)?\s+duplicate", r"\bkeep(?:s|ing)?\s+duplicate")),
        ),
    ),
    ProtocolGroup(
        "Commercial availability",
        (
            ("commercial use", (r"\bcommercial\s+use\b", r"\bcommercially\s+usable\b")),
            ("non-commercial only", (r"\bnon[- ]commercial\b", r"\bresearch\s+use\s+only\b")),
        ),
    ),
    ProtocolGroup(
        "Correlation sign",
        (
            ("positive", (r"\bpositively\s+correlated\b", r"\bpositive\s+correlation\b")),
            ("negative", (r"\bnegatively\s+correlated\b", r"\bnegative\s+correlation\b")),
        ),
    ),
)
TENSION_GROUPS = (
    ProtocolGroup(
        "Endpoint",
        (
            ("primary endpoint", (r"\bprimary\s+endpoint\b",)),
            ("secondary endpoint", (r"\bsecondary\s+endpoint\b",)),
        ),
    ),
    ProtocolGroup(
        "Evaluation target",
        (
            ("calibration", (r"\bcalibration\b",)),
            ("discrimination", (r"\bdiscrimination\b",)),
        ),
    ),
)
VALUE_TERMS_RE = re.compile(
    r"\b("
    r"benjamini[- ]hochberg|blinded|bonferroni|calibration|commercial|decoder[- ]only|"
    r"deduplicat(?:e|es|ed)|discrimination|disjoint|encoder[- ]decoder|encoder[- ]only|"
    r"fdr|held[- ]out|holm|masked|negative|non[- ]commercial|open[- ]label|"
    r"overlap(?:ping)?|positive|primary|prospective|remov(?:e|es|ed)|research|"
    r"retain(?:s|ed)?|retrospective|secondary|seq2seq|unblinded"
    r")\b",
    re.IGNORECASE,
)


def inspect_protocol_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts for controlled academic protocol slots."""

    findings: list[str] = []
    for group in CONFLICT_GROUPS:
        claim_values = set(_mentioned_values(group, claim))
        evidence_values = set(_mentioned_values(group, evidence))
        if not claim_values or not evidence_values or claim_values & evidence_values:
            continue
        if _context_overlaps(claim, evidence):
            findings.extend(
                f"Protocol conflict: {group.label} claim says {claim_value} while evidence says {evidence_value}."
                for claim_value in sorted(claim_values)
                for evidence_value in sorted(evidence_values)
            )
    return tuple(dict.fromkeys(findings))


def inspect_protocol_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return partial-support findings for target swaps that share broader context."""

    findings: list[str] = []
    for group in TENSION_GROUPS:
        claim_values = set(_mentioned_values(group, claim))
        evidence_values = set(_mentioned_values(group, evidence))
        if not claim_values or not evidence_values or claim_values & evidence_values:
            continue
        if _context_overlaps(claim, evidence):
            findings.extend(
                f"Measurement target tension: {group.label} claim says {claim_value} while evidence says {evidence_value}."
                for claim_value in sorted(claim_values)
                for evidence_value in sorted(evidence_values)
            )
    return tuple(dict.fromkeys(findings))


def _mentioned_values(group: ProtocolGroup, text: str) -> tuple[str, ...]:
    values: list[str] = []
    for value, patterns in group.values:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            values.append(value)
    if "non-commercial only" in values:
        values = [value for value in values if value != "commercial use"]
    if "unblinded" in values:
        values = [value for value in values if value != "blinded"]
    return tuple(values)


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.5


def _context_tokens(text: str) -> set[str]:
    return set(tokenize(VALUE_TERMS_RE.sub(" ", text)))
```

- [ ] **Step 2: Run direct tests**

Run: `uv run pytest tests/test_protocol_lens.py -q`

Expected: all tests pass.

## Task 5: Integrate Lenses and Failure Modes

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Modify: `src/citeproof/adjudicator.py`
- Test: `tests/test_entailment_outcome_protocol.py`

- [ ] **Step 1: Write integration tests**

Create `tests/test_entailment_outcome_protocol.py`:

```python
from citeproof.entailment import judge_evidence
from citeproof.models import Label


def test_unchanged_outcome_is_not_supported() -> None:
    judgment = judge_evidence(
        "The method improves calibration.",
        "The method improves accuracy, but calibration is unchanged.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_mixed_effect_outcome_is_partial() -> None:
    judgment = judge_evidence(
        "The method reduces hallucinations.",
        "The method reduces hallucinations on short answers but increases hallucinations on long answers.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED


def test_protocol_conflict_is_not_supported() -> None:
    judgment = judge_evidence(
        "The analysis used Bonferroni correction as the multiple-comparison adjustment.",
        "The analysis used Benjamini-Hochberg correction as the multiple-comparison adjustment.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_measurement_target_swap_is_partial() -> None:
    judgment = judge_evidence(
        "Drug A improves the primary endpoint.",
        "Drug A improves the secondary endpoint.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
```

- [ ] **Step 2: Run integration tests to verify they fail**

Run: `uv run pytest tests/test_entailment_outcome_protocol.py -q`

Expected: import or label failures before integration.

- [ ] **Step 3: Integrate in `fact_lenses.py`**

Add imports:

```python
from citeproof.outcome_lens import inspect_outcome_conflicts, inspect_outcome_tensions
from citeproof.protocol_lens import inspect_protocol_conflicts, inspect_protocol_tensions
```

Add hard findings after statistical/strength checks:

```python
+ list(inspect_outcome_conflicts(claim, evidence))
+ list(inspect_protocol_conflicts(claim, evidence))
```

Add tension findings before context tensions:

```python
+ inspect_outcome_tensions(claim, evidence)
+ inspect_protocol_tensions(claim, evidence)
```

- [ ] **Step 4: Map failure modes in `adjudicator.py`**

Add these checks in `_fact_failure_mode`:

```python
if "outcome status conflict" in text or "lower-is-better outcome conflict" in text:
    return FailureMode.NEGATION_CONFLICT
if "protocol conflict" in text:
    return FailureMode.ENTITY_CONFLICT
if "measurement target tension" in text:
    return FailureMode.SCOPE_OVERSTATEMENT
```

- [ ] **Step 5: Run integration tests**

Run: `uv run pytest tests/test_entailment_outcome_protocol.py -q`

Expected: all tests pass.

## Task 6: Edge Benchmark Rows and Docs

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_eval_runner.py`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Append edge benchmark rows**

Append these JSONL rows:

```jsonl
{"id":"calibration-unchanged-outcome-conflict","claim":"The method improves calibration.","evidence":"The method improves accuracy, but calibration is unchanged.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"latency-no-change-outcome-conflict","claim":"The system reduces latency.","evidence":"The system reduces memory use, but latency shows no change.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"mae-lower-is-better-outcome-conflict","claim":"DenoiseNet improves mean absolute error over Baseline.","evidence":"DenoiseNet reports a higher mean absolute error than Baseline.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"hallucination-mixed-effect-outcome-tension","claim":"The method reduces hallucinations.","evidence":"The method reduces hallucinations on short answers but increases hallucinations on long answers.","expected_label":"partially_supported","expected_failure_mode":"scope_overstatement"}
{"id":"factuality-mixed-effect-outcome-tension","claim":"The method improves factuality.","evidence":"The method improves factuality on extractive questions but reduces factuality on abstractive questions.","expected_label":"partially_supported","expected_failure_mode":"scope_overstatement"}
{"id":"correction-method-protocol-conflict","claim":"The analysis used Bonferroni correction as the multiple-comparison adjustment.","evidence":"The analysis used Benjamini-Hochberg correction as the multiple-comparison adjustment.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"dedup-preprocessing-protocol-conflict","claim":"The dataset removes duplicate samples before training.","evidence":"The dataset retains duplicate samples before training.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"train-test-leakage-protocol-conflict","claim":"Benchmark-Z uses disjoint train and test patients.","evidence":"Benchmark-Z uses the same patients in the train and test sets.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"commercial-use-protocol-conflict","claim":"The dataset permits commercial use.","evidence":"The dataset is restricted to non-commercial research use.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"correlation-sign-protocol-conflict","claim":"GeneA expression is positively correlated with tumor grade.","evidence":"GeneA expression is negatively correlated with tumor grade.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"architecture-protocol-conflict","claim":"BioBERT is an encoder-only transformer model.","evidence":"BioBERT is a decoder-only transformer model.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"temporality-protocol-conflict","claim":"The study uses a prospective cohort design.","evidence":"The study uses a retrospective cohort design.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"blinding-protocol-conflict","claim":"Outcome assessors were blinded to treatment assignment.","evidence":"Outcome assessors were unblinded to treatment assignment.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
{"id":"endpoint-measurement-target-tension","claim":"Drug A improves the primary endpoint.","evidence":"Drug A improves the secondary endpoint.","expected_label":"partially_supported","expected_failure_mode":"scope_overstatement"}
{"id":"calibration-discrimination-target-tension","claim":"RiskNet improves calibration on the ICU cohort.","evidence":"RiskNet improves discrimination on the ICU cohort.","expected_label":"partially_supported","expected_failure_mode":"scope_overstatement"}
{"id":"training-code-release-protocol-conflict","claim":"The authors release open-source training code.","evidence":"The authors release model weights but do not release training code.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
```

- [ ] **Step 2: Update failure-mode required IDs**

Add all 16 new IDs to `tests/test_eval_runner.py::test_edge_cases_with_expected_failure_modes_pass`.

- [ ] **Step 3: Update evaluation docs**

Change the edge-case row total in `docs/evaluation.md` from `96` to `112` and add `outcome-status conflicts`, `mixed-effect tensions`, and `protocol/measurement-slot conflicts` to the coverage sentence.

- [ ] **Step 4: Run edge eval**

Run:

```bash
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output /tmp/citeproof_outcome_protocol_edge.json
```

Expected: total `112`, accuracy `1.0`, false-supported rate `0.0`.

## Task 7: Full Verification and Commits

**Files:**
- All modified source, tests, examples, docs.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
uv run pytest \
  tests/test_outcome_lens.py \
  tests/test_protocol_lens.py \
  tests/test_entailment_outcome_protocol.py \
  tests/test_eval_runner.py::test_edge_cases_with_expected_failure_modes_pass \
  -q
```

Expected: all targeted tests pass.

- [ ] **Step 2: Run full local test suite**

Run:

```bash
uv run pytest -q -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 3: Run all committed benchmark evals**

Run:

```bash
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output reports/hallucination_bib_gated_details.json
```

Expected: false-supported rate `0.0` for each eval; edge total `112`.

- [ ] **Step 4: Run lint**

Run:

```bash
uv run ruff check --no-cache .
```

Expected: no lint errors.

- [ ] **Step 5: Commit implementation**

Run:

```bash
git add src/citeproof/outcome_lens.py src/citeproof/protocol_lens.py \
  src/citeproof/fact_lenses.py src/citeproof/adjudicator.py \
  tests/test_outcome_lens.py tests/test_protocol_lens.py \
  tests/test_entailment_outcome_protocol.py tests/test_eval_runner.py \
  examples/edge_cases/claim_support.jsonl docs/evaluation.md \
  reports/edge_cases_heuristic.json reports/hallucination_bib_gated_details.json
git commit -m "fix: harden outcome and protocol verification"
```

- [ ] **Step 6: Push and check CI**

Run:

```bash
git push origin main
gh run list --branch main --limit 1
```

Expected: pushed commit appears on `main`; latest CI finishes successfully.
