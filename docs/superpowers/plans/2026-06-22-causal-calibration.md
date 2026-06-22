# Causal Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calibrate causal claim verification so association-only evidence blocks full support while explicit randomized/intervention evidence can support matching causal claims.

**Architecture:** Extend the existing `strength_lens` causal-overstatement patterns and add a small semantic causal-support helper used by `entailment`. Keep deterministic conflict and tension gates ahead of semantic support.

**Tech Stack:** Python, pytest, ruff, CiteProof heuristic verifier.

---

### Task 1: Causal Overstatement Coverage

**Files:**
- Modify: `src/citeproof/strength_lens.py`
- Test: `tests/test_strength_lens.py`
- Test: `tests/test_entailment_strength.py`

- [ ] **Step 1: Add failing strength-lens tests**

```python
@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        (
            "Higher temperature leads to increased failure rates.",
            "Higher temperature is correlated with increased failure rates.",
        ),
        (
            "The policy resulted in lower dropout rates.",
            "The policy was studied in an observational cohort with lower dropout rates.",
        ),
    ],
)
def test_detects_broader_causal_overstatement_forms(claim: str, evidence: str) -> None:
    findings = inspect_strength_tensions(claim, evidence)

    assert any("Causal overstatement" in finding for finding in findings)
```

- [ ] **Step 2: Add failing adjudicator test**

```python
def test_leads_to_correlation_blocks_full_support() -> None:
    judgment = adjudicate_evidence(
        "Higher temperature leads to increased failure rates.",
        "Higher temperature correlated with increased failure rates in the logs.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
    assert judgment.failure_mode == FailureMode.SCOPE_OVERSTATEMENT
```

- [ ] **Step 3: Broaden causal and weak-evidence patterns**

Update `CAUSAL_CLAIM_RE`, `WEAK_CAUSAL_RE`, and `TRIGGER_WORDS_RE` with the
new causal forms and weak causal-design terms from the spec.

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_strength_lens.py tests/test_entailment_strength.py -q
```

Expected: all tests pass.

### Task 2: Explicit Causal-Design Support

**Files:**
- Create: `src/citeproof/causal_support.py`
- Modify: `src/citeproof/entailment.py`
- Test: `tests/test_entailment_strength.py`

- [ ] **Step 1: Add failing support and negation tests**

```python
def test_randomized_intervention_supports_matching_causal_claim() -> None:
    judgment = adjudicate_evidence(
        "The intervention caused test scores to improve.",
        "The randomized intervention improved test scores relative to control.",
    )

    assert judgment.label == Label.SUPPORTED


def test_randomized_non_effect_does_not_support_causal_improvement() -> None:
    judgment = adjudicate_evidence(
        "The intervention caused test scores to improve.",
        "The randomized intervention did not improve test scores relative to control.",
    )

    assert judgment.label == Label.CONTRADICTED
```

- [ ] **Step 2: Implement `has_causal_design_support`**

Create `src/citeproof/causal_support.py` with a helper that returns `True` only
when the claim has causal language, evidence has a randomized/controlled
intervention design signal, overlap is at least `0.5`, and evidence has an
affirmative result verb.

- [ ] **Step 3: Wire semantic support**

Import `has_causal_design_support` in `entailment.py` and call it from
`_has_semantic_support` before the existing BERTScore/language paraphrases.

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_entailment_strength.py tests/test_entailment.py -q
```

Expected: all tests pass.

### Task 3: Benchmark And Documentation

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add eval rows**

Append one `partially_supported` row for causal correlation evidence and one
`supported` row for randomized intervention evidence.

- [ ] **Step 2: Update documented benchmark total**

Update the edge benchmark total from `112` to `114` and mention causal design
support in the covered case list.

- [ ] **Step 3: Run full gate**

Run:

```bash
uv run pytest -q -p no:cacheprovider
uv run citeproof eval-suite examples/eval_suite.json
uv run ruff check --no-cache .
```

Expected: tests pass, eval-suite passes, false-supported rate remains `0.0`,
and ruff reports no issues.

- [ ] **Step 4: Commit and push**

```bash
git add src/citeproof/strength_lens.py src/citeproof/causal_support.py \
  src/citeproof/entailment.py tests/test_strength_lens.py \
  tests/test_entailment_strength.py examples/edge_cases/claim_support.jsonl \
  docs/evaluation.md
git commit -m "feat: calibrate causal claim support"
git push origin main
```
