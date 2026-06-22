# Strict Verifier v2 High-Recall Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `supported` harder to reach by broadening cited-evidence candidate collection, preserving contradiction candidates, and exposing retrieval/rationale diagnostics in traces and evals.

**Architecture:** Keep the current citation-scoped verifier pipeline and add high-recall candidate diagnostics around it. The verifier should judge multiple sentence-window candidates per atom, keep candidate rank/relation data in the trace, and add adversarial cases proving that lower-ranked contradictions block `supported`.

**Tech Stack:** Python 3.11+, dataclasses, existing CiteProof CLI/test stack, pytest, no new runtime dependency in this slice.

---

## File Structure

- Modify `src/citeproof/models.py`: add rank and diagnostic fields to `RationaleSpan` and `AtomVerification`.
- Modify `src/citeproof/verifier.py`: add local constants for chunk/candidate breadth, judge more candidates, populate diagnostics, and preserve contradiction priority.
- Modify `tests/test_models.py`: prove trace serialization includes new diagnostic fields.
- Modify `tests/test_verifier.py`: prove low-ranked contradictions block support and diagnostics are present.
- Modify `src/citeproof/evals/runner.py`: support optional expected diagnostics fields in direct JSONL eval rows.
- Modify `tests/test_eval_runner.py`: prove optional expected diagnostics are enforced.
- Modify `examples/edge_cases/claim_support.jsonl`: add direct adversarial cases that target source silence, cross-metric negation, and low-overlap support.
- Modify `docs/evaluation.md`: document the new trace/eval diagnostic fields.
- Modify `README.md`: document the strict support invariant for broad candidate search.

No dense retrieval, reranker, external benchmark adapter, or learned judge is added in this plan. Those become separate plans after the trace/eval surface can measure candidate recall.

## Task 1: Trace Diagnostics Model Fields

**Files:**
- Modify: `src/citeproof/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Add failing serialization test**

Append this test to `tests/test_models.py`:

```python
def test_atom_trace_serializes_candidate_diagnostics() -> None:
    rationale = RationaleSpan(
        source_id="paper",
        citation_key="smith2024",
        text="Method X improves accuracy.",
        relation="support",
        score=0.91,
        rank=2,
    )
    atom = AtomVerification(
        text="Method X improves accuracy.",
        context="Method X improves accuracy.",
        label=Label.SUPPORTED,
        confidence=0.91,
        rationales=(rationale,),
        candidate_count=5,
        support_candidate_count=2,
        contradiction_candidate_count=1,
        best_support_rank=2,
        best_contradiction_rank=4,
        reason="All cited evidence was adjudicated.",
    )
    trace = ClaimVerificationTrace(
        claim="Method X improves accuracy.",
        citations=("smith2024",),
        source_gate_status="passed",
        atom_verifications=(atom,),
        final_label=Label.SUPPORTED,
        final_confidence=0.91,
        final_failure_mode=None,
        review_action="none",
    )
    result = VerificationResult(
        claim="Method X improves accuracy.",
        label=Label.SUPPORTED,
        confidence=0.91,
        citations=("smith2024",),
        evidence=(rationale.to_evidence(),),
        reason="All atomic subclaims are supported.",
        trace=trace,
    )

    data = result.to_dict()

    atom_data = data["trace"]["atom_verifications"][0]
    assert atom_data["candidate_count"] == 5
    assert atom_data["support_candidate_count"] == 2
    assert atom_data["contradiction_candidate_count"] == 1
    assert atom_data["best_support_rank"] == 2
    assert atom_data["best_contradiction_rank"] == 4
    assert atom_data["rationales"][0]["rank"] == 2
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run pytest tests/test_models.py::test_atom_trace_serializes_candidate_diagnostics -v
```

Expected: FAIL with `TypeError` about unexpected `rank` or diagnostic keyword arguments.

- [ ] **Step 3: Add model fields**

In `src/citeproof/models.py`, update `RationaleSpan`:

```python
@dataclass(frozen=True)
class RationaleSpan:
    """Evidence text selected as the rationale for an atomic judgment."""

    source_id: str
    citation_key: str
    text: str
    page: int | None = None
    section: str | None = None
    relation: str = "undetermined"
    score: float = 0.0
    rank: int = 0
```

Update `AtomVerification`:

```python
@dataclass(frozen=True)
class AtomVerification:
    """Verification result for one atomic claim."""

    text: str
    context: str
    label: Label
    confidence: float
    rationales: tuple[RationaleSpan, ...] = ()
    failure_mode: FailureMode | None = None
    reason: str = ""
    candidate_count: int = 0
    support_candidate_count: int = 0
    contradiction_candidate_count: int = 0
    best_support_rank: int | None = None
    best_contradiction_rank: int | None = None
```

Do not change `RationaleSpan.to_evidence()` score behavior; `rank` is trace-only.

- [ ] **Step 4: Run model tests**

Run:

```bash
uv run pytest tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/models.py tests/test_models.py
git commit -m "feat: add rationale diagnostic fields"
```

## Task 2: High-Recall Candidate Diagnostics In Verifier

**Files:**
- Modify: `src/citeproof/verifier.py`
- Modify: `tests/test_verifier.py`

- [ ] **Step 1: Add failing verifier diagnostic tests**

Append these tests to `tests/test_verifier.py`:

```python
def test_verify_claim_records_candidate_diagnostics() -> None:
    chunks = [
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="support",
            text="Method X improves accuracy.",
        ),
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="neutral",
            text="Method X reports accuracy metrics.",
        ),
    ]

    result = verify_claim(
        Claim("Method X improves accuracy.", ("smith2024",)),
        chunks,
        evidence_limit=8,
    )

    atom = result.trace.atom_verifications[0]
    assert atom.candidate_count >= 2
    assert atom.support_candidate_count >= 1
    assert atom.best_support_rank == 1
    assert atom.rationales[0].rank == 1


def test_lower_ranked_contradiction_blocks_supported() -> None:
    chunks = [
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="support",
            text="Method X improves accuracy in benchmark A.",
        ),
        SourceChunk(
            source_id="paper",
            citation_key="smith2024",
            chunk_id="long-contradiction",
            text=(
                "In the ablation appendix for benchmark A, Method X does not improve "
                "accuracy over the baseline after controlling for random seed, optimizer, "
                "and dataset split effects."
            ),
        ),
    ]

    result = verify_claim(
        Claim("Method X improves accuracy in benchmark A.", ("smith2024",)),
        chunks,
        evidence_limit=8,
    )

    atom = result.trace.atom_verifications[0]
    assert result.label == Label.CONTRADICTED
    assert result.failure_mode == FailureMode.NEGATION_CONFLICT
    assert atom.support_candidate_count >= 1
    assert atom.contradiction_candidate_count >= 1
    assert atom.best_contradiction_rank is not None
    assert atom.best_contradiction_rank > atom.best_support_rank
```

- [ ] **Step 2: Run the failing verifier tests**

Run:

```bash
uv run pytest tests/test_verifier.py::test_verify_claim_records_candidate_diagnostics tests/test_verifier.py::test_lower_ranked_contradiction_blocks_supported -v
```

Expected: FAIL because `AtomVerification` diagnostics are not populated.

- [ ] **Step 3: Add verifier constants and helpers**

In `src/citeproof/verifier.py`, after `Judge = ...`, add:

```python
CHUNK_CANDIDATE_LIMIT = 8
RATIONALE_CANDIDATE_LIMIT = 5
RATIONALE_MIN_SCORE = 0.08
```

In `verify_claim`, replace:

```python
retrieved = retrieve_evidence(claim, chunks, limit=evidence_limit)
```

with:

```python
retrieved = retrieve_evidence(
    claim,
    chunks,
    limit=max(evidence_limit, CHUNK_CANDIDATE_LIMIT),
)
```

In `_verify_atoms`, replace:

```python
candidates = select_rationales(atom_claim, chunks, limit=3)
```

with:

```python
candidates = select_rationales(
    atom_claim,
    chunks,
    limit=RATIONALE_CANDIDATE_LIMIT,
    min_score=RATIONALE_MIN_SCORE,
)
```

Add these helpers below `_choose_candidate_judgment`:

```python
def _count_relation(
    judgments: tuple[tuple[EvidenceCandidate, EvidenceJudgment], ...],
    label: Label,
) -> int:
    return sum(candidate_judgment.label == label for _candidate, candidate_judgment in judgments)


def _best_rank_for(
    judgments: tuple[tuple[EvidenceCandidate, EvidenceJudgment], ...],
    label: Label,
) -> int | None:
    ranks = [
        candidate.rank
        for candidate, candidate_judgment in judgments
        if candidate_judgment.label == label
    ]
    return min(ranks) if ranks else None
```

- [ ] **Step 4: Populate atom diagnostics**

In `_verify_atoms`, update `RationaleSpan(...)` creation:

```python
RationaleSpan(
    source_id=candidate.source_id,
    citation_key=candidate.citation_key,
    text=candidate.text,
    page=candidate.page,
    relation=_relation_for(candidate_judgment.label),
    score=candidate.lexical_score,
    rank=candidate.rank,
)
```

Update `AtomVerification(...)` creation in the judged-candidate path:

```python
AtomVerification(
    text=atom.text,
    context=atom.context,
    label=judgment.label,
    confidence=round(judgment.confidence, 3),
    rationales=rationales,
    failure_mode=judgment.failure_mode,
    reason=judgment.reason,
    candidate_count=len(judged_candidates),
    support_candidate_count=_count_relation(judged_candidates, Label.SUPPORTED),
    contradiction_candidate_count=_count_relation(judged_candidates, Label.CONTRADICTED),
    best_support_rank=_best_rank_for(judged_candidates, Label.SUPPORTED),
    best_contradiction_rank=_best_rank_for(judged_candidates, Label.CONTRADICTED),
)
```

Keep the no-candidate path with diagnostic defaults.

- [ ] **Step 5: Run verifier tests**

Run:

```bash
uv run pytest tests/test_verifier.py tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/citeproof/verifier.py tests/test_verifier.py
git commit -m "feat: record candidate diagnostics"
```

## Task 3: Optional Expected Diagnostics In Direct Eval

**Files:**
- Modify: `src/citeproof/evals/runner.py`
- Modify: `tests/test_eval_runner.py`

- [ ] **Step 1: Add failing eval diagnostics assertion test**

Append this test to `tests/test_eval_runner.py`:

```python
def test_eval_cases_assert_optional_expected_failure_mode(tmp_path: Path) -> None:
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        '{"id":"negation","claim":"A improves B.",'
        '"evidence":"A does not improve B.","expected_label":"contradicted",'
        '"expected_failure_mode":"negation_conflict"}\n',
        encoding="utf-8",
    )

    cases = run_eval_cases(dataset)

    assert cases == [
        {
            "id": "negation",
            "expected_label": "contradicted",
            "predicted_label": "contradicted",
            "confidence": 0.78,
            "failure_mode": "negation_conflict",
            "expected_failure_mode": "negation_conflict",
            "failure_mode_pass": True,
            "false_supported": False,
            "pass": True,
            "reason": "Evidence uses an incompatible polarity for the claimed result.",
        }
    ]
```

- [ ] **Step 2: Run the failing eval test**

Run:

```bash
uv run pytest tests/test_eval_runner.py::test_eval_cases_assert_optional_expected_failure_mode -v
```

Expected: FAIL because `expected_failure_mode` and `failure_mode_pass` are not included.

- [ ] **Step 3: Add optional diagnostic assertion fields**

In `src/citeproof/evals/runner.py`, replace the `rows.append({...})` block with:

```python
        failure_mode = judgment.failure_mode.value if judgment.failure_mode else None
        row = {
            "id": data["id"],
            "expected_label": expected_label.value,
            "predicted_label": judgment.label.value,
            "confidence": round(judgment.confidence, 3),
            "failure_mode": failure_mode,
            "false_supported": expected_label != Label.SUPPORTED and judgment.label == Label.SUPPORTED,
            "pass": expected_label == judgment.label,
            "reason": judgment.reason,
        }
        if "expected_failure_mode" in data:
            row["expected_failure_mode"] = data["expected_failure_mode"]
            row["failure_mode_pass"] = data["expected_failure_mode"] == failure_mode
            row["pass"] = row["pass"] and row["failure_mode_pass"]
        rows.append(row)
```

- [ ] **Step 4: Run eval runner tests**

Run:

```bash
uv run pytest tests/test_eval_runner.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/evals/runner.py tests/test_eval_runner.py
git commit -m "feat: assert eval failure modes"
```

## Task 4: Expand Fast Adversarial Benchmark

**Files:**
- Modify: `examples/edge_cases/claim_support.jsonl`
- Modify: `tests/test_entailment.py`
- Modify: `tests/test_fact_lenses.py`
- Modify: `tests/test_eval_runner.py`

- [ ] **Step 1: Add direct edge cases with expected failure modes**

Append these lines to `examples/edge_cases/claim_support.jsonl`:

```json
{"id":"source-silence-related","claim":"Method X improves accuracy over the baseline.","evidence":"Method X reports accuracy metrics for the baseline experiment.","expected_label":"partially_supported","expected_failure_mode":"scope_overstatement"}
{"id":"metric-cross-support","claim":"Method X improves accuracy over the baseline.","evidence":"Method X improves accuracy over the baseline, with no improvement in F1.","expected_label":"supported"}
{"id":"metric-cross-contradiction","claim":"Method X improves accuracy over the baseline.","evidence":"Method X improves F1 score over the baseline, with no accuracy improvement.","expected_label":"contradicted","expected_failure_mode":"negation_conflict"}
{"id":"unit-overlap-not-conflict","claim":"The evaluation used 42 percent of the dataset.","evidence":"The evaluation used 42 percent of the dataset, or 42 examples.","expected_label":"supported"}
```

- [ ] **Step 2: Add regression tests for direct hard cases**

Append to `tests/test_entailment.py`:

```python
def test_metric_cross_support_with_no_improvement_in_f1() -> None:
    judgment = judge_evidence(
        "Method X improves accuracy over the baseline.",
        "Method X improves accuracy over the baseline, with no improvement in F1.",
    )

    assert judgment.label == Label.SUPPORTED


def test_metric_cross_contradicts_matching_metric() -> None:
    judgment = judge_evidence(
        "Method X improves accuracy over the baseline.",
        "Method X improves F1 score over the baseline, with no accuracy improvement.",
    )

    assert judgment.label == Label.CONTRADICTED
```

Append to `tests/test_fact_lenses.py`:

```python
def test_does_not_flag_unit_overlap_as_conflict() -> None:
    result = inspect_facts(
        "The evaluation used 42 percent of the dataset.",
        "The evaluation used 42 percent of the dataset, or 42 examples.",
    )

    assert result.label is None
```

- [ ] **Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/test_entailment.py::test_metric_cross_support_with_no_improvement_in_f1 tests/test_entailment.py::test_metric_cross_contradicts_matching_metric tests/test_fact_lenses.py::test_does_not_flag_unit_overlap_as_conflict -v
```

Expected: PASS. These regressions should already be supported by the merged strict verifier; if one fails, fix only the matching deterministic lens.

- [ ] **Step 4: Update eval runner expected case test**

Append to `tests/test_eval_runner.py`:

```python
def test_edge_cases_with_expected_failure_modes_pass() -> None:
    cases = run_eval_cases(Path("examples/edge_cases/claim_support.jsonl"))

    failed = [case for case in cases if not case["pass"]]

    assert failed == []
    assert any(case.get("expected_failure_mode") == "negation_conflict" for case in cases)
```

- [ ] **Step 5: Run edge eval**

Run:

```bash
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
```

Expected: command succeeds, `false_supported_rate` remains `0.0`, and `total` increases by 4 from the pre-task value.

- [ ] **Step 6: Commit**

```bash
git add examples/edge_cases/claim_support.jsonl tests/test_entailment.py tests/test_fact_lenses.py tests/test_eval_runner.py
git commit -m "test: expand strict evidence adversaries"
```

## Task 5: Document High-Recall Evidence Diagnostics

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Update README strict model**

In `README.md`, after the existing trust-trace paragraph, add:

```markdown
Strict traces include every judged rationale candidate for each atom. A claim
cannot be marked `supported` when a cited contradiction candidate is found, even
if another candidate supports the same atom.
```

- [ ] **Step 2: Update evaluation docs**

In `docs/evaluation.md`, add these bullets under "Reading Scores":

```markdown
- `candidate_count`: number of rationale candidates judged for an atom.
- `support_candidate_count`: judged candidates labeled `supported`.
- `contradiction_candidate_count`: judged candidates labeled `contradicted`.
- `best_support_rank`: retrieval rank of the best supporting rationale, when present.
- `best_contradiction_rank`: retrieval rank of the best contradictory rationale, when present.
- `failure_mode_pass`: direct eval diagnostic check for expected failure modes.
```

Also update the local benchmark table totals after running Task 4.

- [ ] **Step 3: Run documentation verification commands**

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

Expected: tests pass; direct and draft evals keep `false_supported_rate = 0.0`.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/evaluation.md
git commit -m "docs: document evidence diagnostics"
```

## Task 6: Push And CI Verification

**Files:**
- No source changes.

- [ ] **Step 1: Inspect local status**

Run:

```bash
git status --short --branch
```

Expected: `main` is ahead of `origin/main` with no uncommitted changes.

- [ ] **Step 2: Push**

Run:

```bash
git push origin main
```

Expected: push succeeds.

- [ ] **Step 3: Watch CI**

Run:

```bash
gh run list --repo SebastianBoehler/citeproof --branch main --limit 3
gh run watch <latest-run-id> --repo SebastianBoehler/citeproof --exit-status
```

Expected: tests workflow passes on Python 3.11, 3.12, and 3.13.

## Self-Review Notes

- Spec coverage: The plan implements high-recall candidate collection, contradiction-safe adjudication diagnostics, optional expected failure-mode assertions, adversarial benchmark expansion, documentation updates, and CI verification.
- Deferred scope: Dense retrieval, semantic rerankers, SciFact adapter, MiniCheck, AlignScore, and calibration reports remain out of this slice.
- Type consistency: `RationaleSpan.rank`, `AtomVerification.candidate_count`, `support_candidate_count`, `contradiction_candidate_count`, `best_support_rank`, and `best_contradiction_rank` are introduced before verifier tasks consume them.
- Safety invariant: `supported` still requires citation/source gates, atom support, rationale coverage, no deterministic contradiction, and no enabled model disagreement.
