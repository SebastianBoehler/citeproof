# Material Anchor Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent high-overlap evidence about a different method, dataset, benchmark, or model from being marked `supported`.

**Architecture:** Add a deterministic material-anchor lens inside `src/citeproof/fact_lenses.py`, map its findings to the existing `ENTITY_CONFLICT` failure mode, and add verifier/eval coverage. The slice stays offline and dependency-free.

**Tech Stack:** Python 3.11+, dataclasses/enums already in CiteProof, pytest, existing JSONL eval harness.

---

## File Map

- Modify `src/citeproof/fact_lenses.py`: extract high-precision claim anchors and flag missing anchors in related evidence.
- Modify `src/citeproof/adjudicator.py`: map entity-conflict findings to `FailureMode.ENTITY_CONFLICT`.
- Modify `src/citeproof/verifier.py`: add review action for `ENTITY_CONFLICT`.
- Modify `tests/test_fact_lenses.py`: unit coverage for anchor conflicts and ignored placeholders.
- Modify `tests/test_entailment.py`: adjudicated evidence coverage for method/dataset swaps.
- Modify `tests/test_verifier.py`: end-to-end trace coverage for swapped anchors.
- Modify `tests/test_eval_runner.py`: assert edge cases with expected failure modes include entity conflict.
- Modify `examples/edge_cases/claim_support.jsonl`: add a material-anchor swap case.
- Modify `docs/evaluation.md`: update local benchmark totals after the new edge case.

## Task 1: Material Anchor Fact Lens

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Test: `tests/test_fact_lenses.py`
- Test: `tests/test_entailment.py`

- [ ] **Step 1: Add failing fact-lens tests**

Append these tests to `tests/test_fact_lenses.py`:

```python
def test_detects_missing_material_anchor() -> None:
    result = inspect_facts(
        "LoRA improves accuracy over full fine-tuning on GLUE.",
        "Prefix tuning improves accuracy over full fine-tuning on GLUE.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Entity conflict" in finding for finding in result.findings)
    assert any("LoRA" in finding for finding in result.findings)


def test_detects_dataset_anchor_swap() -> None:
    result = inspect_facts(
        "LoRA improves accuracy on GLUE.",
        "LoRA improves accuracy on SQuAD.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("GLUE" in finding for finding in result.findings)


def test_ignores_single_letter_placeholders_as_anchors() -> None:
    result = inspect_facts(
        "Method X improves accuracy over the baseline.",
        "Method X improves accuracy over the baseline.",
    )

    assert result.label is None
    assert result.findings == ()
```

Append these tests to `tests/test_entailment.py`:

```python
def test_method_anchor_swap_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA improves accuracy over full fine-tuning on GLUE.",
        "Prefix tuning improves accuracy over full fine-tuning on GLUE.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_dataset_anchor_swap_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA improves accuracy on GLUE.",
        "LoRA improves accuracy on SQuAD.",
    )

    assert judgment.label == Label.CONTRADICTED
```

- [ ] **Step 2: Verify the tests fail**

Run:

```bash
uv run pytest tests/test_fact_lenses.py::test_detects_missing_material_anchor \
  tests/test_fact_lenses.py::test_detects_dataset_anchor_swap \
  tests/test_fact_lenses.py::test_ignores_single_letter_placeholders_as_anchors \
  tests/test_entailment.py::test_method_anchor_swap_is_not_supported \
  tests/test_entailment.py::test_dataset_anchor_swap_is_not_supported -v
```

Expected: the two conflict tests fail because current fact lenses do not check
anchors, and the entailment tests fail because high lexical overlap is treated
as support.

- [ ] **Step 3: Implement anchor extraction**

Add imports and constants in `src/citeproof/fact_lenses.py`:

```python
from citeproof.text import token_overlap_ratio

MATERIAL_ANCHOR_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z]*[A-Z][A-Za-z0-9.]*|[A-Z]+[A-Za-z0-9.-]*\d+[A-Za-z0-9.-]*|"
    r"[A-Z][a-z]+[A-Z][A-Za-z0-9.]*|[A-Z]{2,}[A-Za-z0-9.-]*)\b"
)
GENERIC_ANCHORS = {
    "Ablation",
    "Appendix",
    "Baseline",
    "Claim",
    "Evidence",
    "Experiment",
    "Figure",
    "Method",
    "Model",
    "Result",
    "Table",
    "The",
}
ENTITY_CONFLICT_MIN_OVERLAP = 0.45
```

Add helper functions near the other private helpers:

```python
def _entity_conflicts(claim: str, evidence: str) -> list[str]:
    if token_overlap_ratio(claim, evidence) < ENTITY_CONFLICT_MIN_OVERLAP:
        return []
    claim_anchors = _material_anchors(claim)
    if not claim_anchors:
        return []
    evidence_text = evidence.casefold()
    missing = tuple(anchor for anchor in claim_anchors if anchor.casefold() not in evidence_text)
    if not missing:
        return []
    return [f"Entity conflict: evidence is missing claim anchor(s) {', '.join(missing)}"]


def _material_anchors(text: str) -> tuple[str, ...]:
    anchors: list[str] = []
    seen: set[str] = set()
    for match in MATERIAL_ANCHOR_RE.finditer(text):
        anchor = match.group(0).strip(".,;:()[]{}")
        if _is_material_anchor(anchor) and anchor.casefold() not in seen:
            anchors.append(anchor)
            seen.add(anchor.casefold())
    return tuple(anchors)


def _is_material_anchor(anchor: str) -> bool:
    if len(anchor) <= 1:
        return False
    if anchor in GENERIC_ANCHORS:
        return False
    if len(anchor) == 2 and anchor.isupper():
        return False
    return any(character.isupper() for character in anchor) and (
        any(character.islower() for character in anchor)
        or any(character.isdigit() for character in anchor)
        or anchor.isupper()
    )
```

Update `inspect_facts` so `_entity_conflicts` participates in the contradiction
finding list:

```python
findings = (
    _number_conflicts(claim, evidence)
    + _unit_conflicts(claim, evidence)
    + _year_conflicts(claim, evidence)
    + _entity_conflicts(claim, evidence)
)
```

- [ ] **Step 4: Verify Task 1 passes**

Run:

```bash
uv run pytest tests/test_fact_lenses.py tests/test_entailment.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add src/citeproof/fact_lenses.py tests/test_fact_lenses.py tests/test_entailment.py
git commit -m "feat: detect material anchor conflicts"
```

## Task 2: Failure Mode, Verifier Trace, And Edge Eval

**Files:**
- Modify: `src/citeproof/adjudicator.py`
- Modify: `src/citeproof/verifier.py`
- Modify: `tests/test_verifier.py`
- Modify: `tests/test_eval_runner.py`
- Modify: `examples/edge_cases/claim_support.jsonl`

- [ ] **Step 1: Add failing verifier and eval tests**

Append this test to `tests/test_verifier.py`:

```python
def test_verify_claim_flags_material_anchor_conflict() -> None:
    chunks = [
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="swap",
            text="Prefix tuning improves accuracy over full fine-tuning on GLUE.",
        )
    ]

    result = verify_claim(
        Claim("LoRA improves accuracy over full fine-tuning on GLUE.", ("smith2024",)),
        chunks,
    )

    assert result.label == Label.CONTRADICTED
    assert result.failure_mode == FailureMode.ENTITY_CONFLICT
    assert result.trace is not None
    assert result.trace.review_action == "fix the entity or cite a matching source"
```

Append this JSONL row to `examples/edge_cases/claim_support.jsonl`:

```json
{"id":"material-anchor-swap","claim":"LoRA improves accuracy over full fine-tuning on GLUE.","evidence":"Prefix tuning improves accuracy over full fine-tuning on GLUE.","expected_label":"contradicted","expected_failure_mode":"entity_conflict"}
```

Update the ID assertion in `tests/test_eval_runner.py`:

```python
assert {"source-silence-related", "metric-cross-contradiction", "material-anchor-swap"} <= {
    case["id"] for case in mode_cases
}
```

- [ ] **Step 2: Verify the new verifier/eval checks fail**

Run:

```bash
uv run pytest tests/test_verifier.py::test_verify_claim_flags_material_anchor_conflict \
  tests/test_eval_runner.py::test_edge_cases_with_expected_failure_modes_pass -v
```

Expected: verifier failure mode/review action is not yet `entity_conflict`.

- [ ] **Step 3: Wire entity failure mode and review action**

Update `_fact_failure_mode` in `src/citeproof/adjudicator.py`:

```python
if "entity conflict" in text:
    return FailureMode.ENTITY_CONFLICT
```

Add this entry to `_review_action` in `src/citeproof/verifier.py`:

```python
FailureMode.ENTITY_CONFLICT: "fix the entity or cite a matching source",
```

- [ ] **Step 4: Verify Task 2 passes**

Run:

```bash
uv run pytest tests/test_verifier.py::test_verify_claim_flags_material_anchor_conflict \
  tests/test_eval_runner.py::test_edge_cases_with_expected_failure_modes_pass -v
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
```

Expected: tests pass; edge eval total is 20, accuracy is 1.0,
false-supported rate is 0.0.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add src/citeproof/adjudicator.py src/citeproof/verifier.py tests/test_verifier.py \
  tests/test_eval_runner.py examples/edge_cases/claim_support.jsonl
git commit -m "test: add material anchor adversary"
```

## Task 3: Documentation And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Update docs**

In `README.md`, add material anchors to the deterministic fact-lens bullet:

```text
Apply deterministic fact lenses for material anchors, numbers, years, hedging,
scope gaps, and selected negation risks.
```

In `docs/evaluation.md`, update the edge benchmark row total from 19 to 20 and
add material anchor swaps to the local benchmark coverage sentence:

```text
support, contradiction, partial support, source silence, numeric conflicts,
temporal conflicts, material anchor swaps, hedged evidence, entity swaps,
compound claims, failure-mode classification, and bibliography-gated
hallucination checks.
```

- [ ] **Step 2: Run full verification**

Run:

```bash
uv run pytest -q
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output reports/hallucination_bib_gated_details.json
git diff --check
```

Expected:

- `pytest`: all tests pass.
- `examples/claim_support.jsonl`: total 4, accuracy 1.0, false-supported rate 0.0.
- `examples/edge_cases/claim_support.jsonl`: total 20, accuracy 1.0, false-supported rate 0.0.
- `examples/hallucination` draft eval: total 5, accuracy 1.0, false-supported rate 0.0.
- `git diff --check`: no output.

- [ ] **Step 3: Commit Task 3**

Run:

```bash
git add README.md docs/evaluation.md
git commit -m "docs: document material anchor checks"
```

## Final Verification And Merge

- [ ] Run `uv run ruff check .`.
- [ ] Run `git status --short --branch`.
- [ ] Merge the branch into `main` with a merge commit.
- [ ] Push `main`.
- [ ] Watch GitHub Actions for the pushed merge commit until all jobs pass.
