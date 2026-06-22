# Contrast And Metric Slots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block high-overlap CS/ML false support caused by contrastive exclusions and metric-slot swaps.

**Architecture:** Add one deterministic contrast lens before lexical support, then extend existing statistical and outcome lenses for AUROC averaging and BLEU/chrF outcomes.

**Tech Stack:** Python stdlib regex, existing fact-lens pipeline, pytest, ruff, uv.

---

## File Structure

- Create `src/citeproof/contrast_lens.py`: contrastive exclusion detection.
- Modify `src/citeproof/fact_lenses.py`: call the new hard-conflict lens.
- Modify `src/citeproof/adjudicator.py`: route contrast exclusions to `negation_conflict`.
- Modify `src/citeproof/statistical_lens.py`: add AUROC averaging conflict.
- Modify `src/citeproof/outcome_lens.py`: add BLEU and chrF outcome terms.
- Create `tests/test_contrast_metric_slots.py`: regression tests for explorer probes.
- Modify `examples/edge_cases/claim_support.jsonl`: add four cases.
- Modify `docs/evaluation.md`: update totals and coverage text.

### Task 1: Contrastive Exclusion Lens

- [ ] **Step 1: Add failing tests**

```python
def test_rather_than_architecture_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "GPT-3 uses a mixture-of-experts transformer architecture.",
        "GPT-3 uses a dense transformer architecture rather than a mixture-of-experts architecture.",
    )
    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT


def test_rather_than_objective_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "ELECTRA uses a masked language modeling objective during pretraining.",
        "ELECTRA uses replaced-token detection rather than masked language modeling as its pretraining objective.",
    )
    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT


def test_matching_contrastive_claim_is_not_flagged() -> None:
    judgment = adjudicate_evidence(
        "GPT-3 uses a dense transformer architecture.",
        "GPT-3 uses a dense transformer architecture rather than a mixture-of-experts architecture.",
    )
    assert judgment.label == Label.SUPPORTED
```

- [ ] **Step 2: Implement `contrast_lens.py`**

Create `inspect_contrast_exclusion_conflicts(claim, evidence) -> tuple[str, ...]`.
Use cue patterns for `rather than`, `instead of`, and `as opposed to`. Extract
the excluded phrase until punctuation, require at least two content tokens, skip
if the claim has a contrast cue, require excluded-token coverage in the claim,
and require context overlap after removing excluded tokens.

- [ ] **Step 3: Integrate with fact lenses and failure mode routing**

Import the contrast lens in `fact_lenses.py`, append its findings to
`hard_findings`, and map `contrast exclusion conflict` to
`FailureMode.NEGATION_CONFLICT` in `adjudicator.py`.

### Task 2: Metric And Outcome Slots

- [ ] **Step 1: Add failing tests**

```python
def test_macro_micro_auroc_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The model reports macro-AUROC on the held-out test set.",
        "The model reports micro-AUROC on the held-out test set.",
    )
    assert judgment.label == Label.CONTRADICTED


def test_bleu_unchanged_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The system improves BLEU on WMT14 English-German translation.",
        "The system improves chrF on WMT14 English-German translation, but BLEU is unchanged.",
    )
    assert judgment.label == Label.CONTRADICTED
```

- [ ] **Step 2: Extend existing lenses**

Add an `AUROC averaging` group to `statistical_lens.py`, and add `BLEU` and
`chrF` to `outcome_lens.py` plus the trigger-term regex.

### Task 3: Benchmark, Verification, Commit

- [ ] **Step 1: Add edge rows and docs**

Add four edge rows for MoE contrast, pretraining-objective contrast, AUROC
averaging, and BLEU unchanged. Increase the edge total by four and add
contrastive exclusions plus metric-slot conflicts to `docs/evaluation.md`.

- [ ] **Step 2: Run gates**

```bash
uv run pytest tests/test_contrast_metric_slots.py -q
uv run pytest -q -p no:cacheprovider
uv run citeproof eval examples/edge_cases/claim_support.jsonl --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-suite examples/eval_suite.json
uv run ruff check --no-cache .
```

- [ ] **Step 3: Check file sizes, commit, and push**

```bash
wc -l src/citeproof/contrast_lens.py src/citeproof/fact_lenses.py src/citeproof/statistical_lens.py src/citeproof/outcome_lens.py tests/test_contrast_metric_slots.py docs/superpowers/plans/2026-06-22-contrast-metric-slots.md
git add src/citeproof/contrast_lens.py src/citeproof/fact_lenses.py src/citeproof/adjudicator.py src/citeproof/statistical_lens.py src/citeproof/outcome_lens.py tests/test_contrast_metric_slots.py examples/edge_cases/claim_support.jsonl docs/evaluation.md
git commit -m "feat: detect contrast metric slot conflicts"
git push origin main
```

## Self-Review

- Spec coverage: all four explorer false-supported probes are represented.
- Scope: no fallback threshold change and no model dependency.
- Safety invariant: contrast conflicts require excluded phrase coverage plus
  non-excluded context overlap.
