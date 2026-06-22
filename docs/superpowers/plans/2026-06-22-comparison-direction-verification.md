# Comparison Direction Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block false `supported` labels when evidence reverses an explicit comparison direction.

**Architecture:** Add a conservative comparison-direction fact lens, map its finding to `comparison_direction_conflict`, then add edge-eval and docs coverage. The implementation stays deterministic and dependency-free.

**Tech Stack:** Python 3.11+, regex helpers, existing `FactInspection`, pytest, existing JSONL eval harness.

---

## File Map

- Modify `src/citeproof/fact_lenses.py`: extract explicit binary comparison anchors and flag reversed direction.
- Modify `src/citeproof/adjudicator.py`: map comparison-direction findings to `FailureMode.COMPARISON_DIRECTION_CONFLICT`.
- Modify `src/citeproof/verifier.py`: add review action for comparison-direction conflicts.
- Modify `tests/test_fact_lenses.py` and `tests/test_entailment.py`: direct fact-lens and heuristic coverage.
- Modify `tests/test_verifier.py` and `tests/test_eval_runner.py`: trace and edge-eval coverage.
- Modify `examples/edge_cases/claim_support.jsonl`: add reversed comparison case.
- Modify `README.md` and `docs/evaluation.md`: document the new check and updated edge total.

## Task 1: Comparison Direction Fact Lens

**Files:**
- Modify: `src/citeproof/fact_lenses.py`
- Test: `tests/test_fact_lenses.py`
- Test: `tests/test_entailment.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_fact_lenses.py`:

```python
def test_detects_reversed_outperforms_comparison() -> None:
    result = inspect_facts(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "Prefix Tuning outperforms LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Comparison direction conflict" in finding for finding in result.findings)


def test_detects_reversed_higher_than_comparison() -> None:
    result = inspect_facts(
        "AlphaModel has higher accuracy than BetaModel.",
        "BetaModel has higher accuracy than AlphaModel.",
    )

    assert result.label == Label.CONTRADICTED


def test_matching_comparison_direction_is_not_conflict() -> None:
    result = inspect_facts(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "LoRA outperforms Prefix Tuning on GLUE.",
    )

    assert result.label is None
```

Append to `tests/test_entailment.py`:

```python
def test_reversed_comparison_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "Prefix Tuning outperforms LoRA on GLUE.",
    )

    assert judgment.label == Label.CONTRADICTED
```

- [ ] **Step 2: Run red tests**

Run:

```bash
uv run pytest tests/test_fact_lenses.py::test_detects_reversed_outperforms_comparison \
  tests/test_fact_lenses.py::test_detects_reversed_higher_than_comparison \
  tests/test_fact_lenses.py::test_matching_comparison_direction_is_not_conflict \
  tests/test_entailment.py::test_reversed_comparison_is_not_supported -v
```

Expected: reversed-comparison tests fail because current code returns no fact
conflict / direct support.

- [ ] **Step 3: Implement comparison helpers**

Add comparison constants and helpers in `src/citeproof/fact_lenses.py`:

```python
COMPARISON_RE = re.compile(
    r"(?P<left>.+?)\s+"
    r"(?P<relation>outperforms|is better than|has higher accuracy than|is superior to)\s+"
    r"(?P<right>.+?)(?:\s+on\s+|\s+in\s+|\.|$)",
    re.IGNORECASE,
)
COMPARISON_RELATIONS = {
    "outperforms": "positive",
    "is better than": "positive",
    "has higher accuracy than": "positive",
    "is superior to": "positive",
}
```

Add a small dataclass and helpers:

```python
@dataclass(frozen=True)
class _Comparison:
    left: str
    right: str
    relation: str


def _comparison_direction_conflicts(claim: str, evidence: str) -> list[str]:
    claim_comparison = _extract_comparison(claim)
    evidence_comparison = _extract_comparison(evidence)
    if claim_comparison is None or evidence_comparison is None:
        return []
    if claim_comparison.relation != evidence_comparison.relation:
        return []
    claim_left = _normalize_anchor(claim_comparison.left)
    claim_right = _normalize_anchor(claim_comparison.right)
    evidence_left = _normalize_anchor(evidence_comparison.left)
    evidence_right = _normalize_anchor(evidence_comparison.right)
    if claim_left == evidence_right and claim_right == evidence_left:
        return [
            "Comparison direction conflict: claim ranks "
            f"{claim_comparison.left} over {claim_comparison.right}, but evidence ranks "
            f"{evidence_comparison.left} over {evidence_comparison.right}"
        ]
    return []


def _extract_comparison(text: str) -> _Comparison | None:
    match = COMPARISON_RE.search(text)
    if not match:
        return None
    left = _comparison_anchor(match.group("left"), from_left=True)
    right = _comparison_anchor(match.group("right"), from_left=False)
    relation = COMPARISON_RELATIONS[match.group("relation").casefold()]
    if not left or not right:
        return None
    return _Comparison(left, right, relation)


def _comparison_anchor(text: str, from_left: bool) -> str | None:
    anchors = _material_anchors(text)
    if not anchors:
        return None
    return anchors[-1] if from_left else anchors[0]
```

Update `inspect_facts` findings order so comparison direction runs after entity
conflicts:

```python
+ _comparison_direction_conflicts(claim, evidence)
```

- [ ] **Step 4: Run green tests**

Run:

```bash
uv run pytest tests/test_fact_lenses.py tests/test_entailment.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add src/citeproof/fact_lenses.py tests/test_fact_lenses.py tests/test_entailment.py
git commit -m "feat: detect comparison direction conflicts"
```

## Task 2: Verifier, Eval, And Docs Wiring

**Files:**
- Modify: `src/citeproof/adjudicator.py`
- Modify: `src/citeproof/verifier.py`
- Modify: `tests/test_verifier.py`
- Modify: `tests/test_eval_runner.py`
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `README.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Add failing verifier/eval coverage**

Append to `tests/test_verifier.py`:

```python
def test_verify_claim_flags_comparison_direction_conflict() -> None:
    chunks = [
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="reverse",
            text="Prefix Tuning outperforms LoRA on GLUE.",
        )
    ]

    result = verify_claim(
        Claim("LoRA outperforms Prefix Tuning on GLUE.", ("smith2024",)),
        chunks,
    )

    assert result.label == Label.CONTRADICTED
    assert result.failure_mode == FailureMode.COMPARISON_DIRECTION_CONFLICT
    assert result.trace is not None
    assert result.trace.review_action == "fix the comparison direction or cite a matching source"
```

Append to `examples/edge_cases/claim_support.jsonl`:

```json
{"id":"comparison-direction-swap","claim":"LoRA outperforms Prefix Tuning on GLUE.","evidence":"Prefix Tuning outperforms LoRA on GLUE.","expected_label":"contradicted","expected_failure_mode":"comparison_direction_conflict"}
```

Update `tests/test_eval_runner.py::test_edge_cases_with_expected_failure_modes_pass`
so the expected ID set includes `comparison-direction-swap`.

- [ ] **Step 2: Map failure mode and review action**

In `src/citeproof/adjudicator.py`, add before the default return:

```python
if "comparison direction conflict" in text:
    return FailureMode.COMPARISON_DIRECTION_CONFLICT
```

In `src/citeproof/verifier.py`, add:

```python
FailureMode.COMPARISON_DIRECTION_CONFLICT: "fix the comparison direction or cite a matching source",
```

- [ ] **Step 3: Update docs**

In `README.md`, include comparison direction in the deterministic fact-lens
bullet. In `docs/evaluation.md`, update edge total from `20` to `21` and add
comparison-direction swaps to the benchmark coverage sentence.

- [ ] **Step 4: Run full verification**

Run:

```bash
uv run pytest -q
uv run ruff check .
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
- edge eval: total `21`, accuracy `1.0`, false-supported rate `0.0`.
- generated reports stay untracked.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add src/citeproof/adjudicator.py src/citeproof/verifier.py tests/test_verifier.py \
  tests/test_eval_runner.py examples/edge_cases/claim_support.jsonl README.md docs/evaluation.md
git commit -m "test: add comparison direction adversary"
```

## Final Verification And Merge

- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run ruff check .`.
- [ ] Merge branch into `main`.
- [ ] Push `main`.
- [ ] Watch GitHub Actions for the merge commit.
