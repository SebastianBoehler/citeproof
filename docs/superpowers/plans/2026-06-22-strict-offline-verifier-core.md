# Strict Offline Verifier Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first strict offline verifier slice: trust traces, stable failure modes, richer metrics, sentence-window rationales, atom-level rationale coverage, and stronger fast-regression cases.

**Architecture:** Keep the existing CLI and public verifier flow, but add trace data structures and rationale-span selection behind the current result objects. The verifier remains citation-scoped and conservative: `supported` requires atom-level rationale coverage, deterministic gates, and model-gate agreement when enabled.

**Tech Stack:** Python dataclasses, existing pytest suite, existing lexical tokenizer/sentence splitter, local optional NLI, no new runtime dependency in this slice.

---

## Scope

This plan implements phases 1-3 from `docs/superpowers/specs/2026-06-22-strict-offline-verifier-core-design.md`.

Deferred to separate future plans:

- SciFact/SciFact-Open adapter
- semantic embedding retrieval
- cross-encoder reranker
- LLM auditor
- repair-loop task generation beyond a simple `review_action` string

## File Structure

- Modify `src/citeproof/models.py`: add `FailureMode`, `EvidenceCandidate`, `RationaleSpan`, `AtomVerification`, `ClaimVerificationTrace`, and optional trace/failure fields on existing result objects.
- Create `src/citeproof/rationales.py`: sentence/window rationale candidate extraction and lexical scoring.
- Modify `src/citeproof/adjudicator.py`: attach failure modes to judgments and expose atom-label combination for verifier traces.
- Modify `src/citeproof/verifier.py`: build atom-level rationale traces and enforce rationale coverage for `supported`.
- Modify `src/citeproof/evals/metrics.py`: add secondary trust metrics.
- Modify `src/citeproof/evals/runner.py`: include `failure_mode` in per-case rows.
- Modify `src/citeproof/report.py`: include trace/failure-mode output in JSON and compact Markdown.
- Modify `examples/edge_cases/claim_support.jsonl`: add unit, metric, and wrong-source-style fast-regression cases.
- Add or modify tests in `tests/test_models.py`, `tests/test_rationales.py`, `tests/test_verifier.py`, `tests/test_eval_runner.py`, and `tests/test_metrics.py`.
- Modify `README.md` and `docs/evaluation.md`: document trace output and refreshed scores.

## Task 1: Trace Models And Failure Modes

**Files:**
- Modify: `src/citeproof/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing serialization tests**

Create `tests/test_models.py`:

```python
from citeproof.models import (
    AtomVerification,
    ClaimVerificationTrace,
    EvidenceCandidate,
    FailureMode,
    Label,
    RationaleSpan,
    VerificationResult,
)


def test_verification_result_serializes_trace_and_failure_mode() -> None:
    rationale = RationaleSpan(
        source_id="paper",
        citation_key="smith2024",
        text="Method X improves sample efficiency.",
        page=3,
        relation="support",
        score=0.91,
    )
    atom = AtomVerification(
        text="Method X improves sample efficiency.",
        context="Method X improves sample efficiency.",
        label=Label.SUPPORTED,
        confidence=0.91,
        rationales=(rationale,),
        failure_mode=None,
        reason="Rationale supports the atom.",
    )
    trace = ClaimVerificationTrace(
        claim="Method X improves sample efficiency.",
        citations=("smith2024",),
        source_gate_status="passed",
        atom_verifications=(atom,),
        final_label=Label.SUPPORTED,
        final_confidence=0.91,
        final_failure_mode=None,
        review_action="none",
    )
    result = VerificationResult(
        claim="Method X improves sample efficiency.",
        label=Label.SUPPORTED,
        confidence=0.91,
        citations=("smith2024",),
        evidence=(),
        reason="All atomic subclaims are supported.",
        failure_mode=None,
        trace=trace,
    )

    data = result.to_dict()

    assert data["label"] == "supported"
    assert data["failure_mode"] is None
    assert data["trace"]["final_label"] == "supported"
    assert data["trace"]["atom_verifications"][0]["rationales"][0]["relation"] == "support"


def test_evidence_candidate_serializes_scores() -> None:
    candidate = EvidenceCandidate(
        source_id="paper",
        citation_key="smith2024",
        text="The adapter used 4 GPUs.",
        chunk_id="paper:p1:0",
        page=1,
        lexical_score=0.7,
        semantic_score=None,
        rerank_score=None,
        rank=1,
        retrieval_method="sentence_window",
    )

    assert candidate.to_dict()["lexical_score"] == 0.7
    assert candidate.to_dict()["retrieval_method"] == "sentence_window"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_models.py -v
```

Expected: FAIL because trace dataclasses and `FailureMode` do not exist.

- [ ] **Step 3: Add trace dataclasses and serializer**

In `src/citeproof/models.py`, add `FailureMode` after `Label`:

```python
class FailureMode(StrEnum):
    """Stable verifier failure modes for traces and repair clients."""

    MISSING_BIBLIOGRAPHY_KEY = "missing_bibliography_key"
    METADATA_NOT_VERIFIED = "metadata_not_verified"
    SOURCE_NOT_RESOLVED = "source_not_resolved"
    WEAK_RETRIEVAL = "weak_retrieval"
    NO_RATIONALE_SPAN = "no_rationale_span"
    MISSING_ATOM_SUPPORT = "missing_atom_support"
    NUMERIC_CONFLICT = "numeric_conflict"
    YEAR_CONFLICT = "year_conflict"
    UNIT_CONFLICT = "unit_conflict"
    ENTITY_CONFLICT = "entity_conflict"
    NEGATION_CONFLICT = "negation_conflict"
    COMPARISON_DIRECTION_CONFLICT = "comparison_direction_conflict"
    SCOPE_OVERSTATEMENT = "scope_overstatement"
    HEDGED_EVIDENCE = "hedged_evidence"
    SOURCE_SILENCE = "source_silence"
    MODEL_DISAGREEMENT = "model_disagreement"
    CONFLICTING_SOURCES = "conflicting_sources"
```

Add these dataclasses before `VerificationResult`:

```python
@dataclass(frozen=True)
class EvidenceCandidate:
    """Sentence/window evidence candidate with retrieval diagnostics."""

    source_id: str
    citation_key: str
    text: str
    chunk_id: str
    title: str | None = None
    page: int | None = None
    lexical_score: float = 0.0
    semantic_score: float | None = None
    rerank_score: float | None = None
    rank: int = 0
    retrieval_method: str = "lexical"

    def to_evidence(self) -> "EvidenceSpan":
        return EvidenceSpan(
            source_id=self.source_id,
            text=self.text,
            citation_key=self.citation_key,
            page=self.page,
            score=self.lexical_score,
            title=self.title,
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(frozen=True)
class RationaleSpan:
    """Exact rationale text selected for an atomic claim."""

    source_id: str
    citation_key: str
    text: str
    page: int | None = None
    section: str | None = None
    relation: str = "undetermined"
    score: float = 0.0

    def to_evidence(self) -> "EvidenceSpan":
        return EvidenceSpan(
            source_id=self.source_id,
            text=self.text,
            citation_key=self.citation_key,
            page=self.page,
            score=self.score,
        )


@dataclass(frozen=True)
class AtomVerification:
    """Trace for one atomic subclaim."""

    text: str
    context: str
    label: Label
    confidence: float
    rationales: tuple[RationaleSpan, ...] = ()
    failure_mode: FailureMode | None = None
    reason: str = ""


@dataclass(frozen=True)
class ClaimVerificationTrace:
    """Trace for one parent claim verification."""

    claim: str
    citations: tuple[str, ...]
    source_gate_status: str
    atom_verifications: tuple[AtomVerification, ...]
    final_label: Label
    final_confidence: float
    final_failure_mode: FailureMode | None
    review_action: str
```

Update `VerificationResult`:

```python
@dataclass(frozen=True)
class VerificationResult:
    """A claim verification result with evidence and rationale."""

    claim: str
    label: Label
    confidence: float
    citations: tuple[str, ...]
    evidence: tuple[EvidenceSpan, ...]
    reason: str
    failure_mode: FailureMode | None = None
    trace: ClaimVerificationTrace | None = None

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)
```

Update `EvidenceJudgment`:

```python
@dataclass(frozen=True)
class EvidenceJudgment:
    """A single evidence-vs-claim judgment."""

    label: Label
    confidence: float
    reason: str
    failure_mode: FailureMode | None = None
```

Add serializer at the end of `models.py`:

```python
def _serialize(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {key: _serialize(item) for key, item in asdict(value).items()}
    return value
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Run existing model consumers**

Run:

```bash
uv run pytest tests/test_verifier.py tests/test_eval_runner.py tests/test_paper.py -v
```

Expected: PASS because the new `VerificationResult` fields have defaults.

- [ ] **Step 6: Commit**

```bash
git add src/citeproof/models.py tests/test_models.py
git commit -m "feat: add verifier trace models"
```

## Task 2: Secondary Trust Metrics

**Files:**
- Modify: `src/citeproof/evals/metrics.py`
- Create: `tests/test_metrics.py`

- [ ] **Step 1: Write failing metrics tests**

Create `tests/test_metrics.py`:

```python
from citeproof.evals.metrics import summarize
from citeproof.models import Label


def test_summary_reports_secondary_trust_metrics() -> None:
    summary = summarize(
        expected=[
            Label.SUPPORTED,
            Label.SUPPORTED,
            Label.CONTRADICTED,
            Label.UNSUPPORTED,
            Label.PARTIALLY_SUPPORTED,
        ],
        predicted=[
            Label.SUPPORTED,
            Label.PARTIALLY_SUPPORTED,
            Label.CONTRADICTED,
            Label.UNCERTAIN,
            Label.SUPPORTED,
        ],
    )

    assert summary.supported_precision == 0.5
    assert summary.supported_recall == 0.5
    assert summary.unsupported_recall == 0.0
    assert summary.contradiction_recall == 1.0
    assert summary.manual_review_rate == 0.4
    assert summary.to_dict()["supported_precision"] == 0.5
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_metrics.py -v
```

Expected: FAIL because secondary metric fields do not exist.

- [ ] **Step 3: Extend `EvalSummary`**

In `src/citeproof/evals/metrics.py`, change `EvalSummary` to:

```python
@dataclass(frozen=True)
class EvalSummary:
    """Aggregate eval metrics."""

    total: int
    accuracy: float
    macro_f1: float
    false_supported_rate: float
    supported_precision: float
    supported_recall: float
    unsupported_recall: float
    contradiction_recall: float
    manual_review_rate: float
    confusion: dict[str, dict[str, int]]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "accuracy": self.accuracy,
            "macro_f1": self.macro_f1,
            "false_supported_rate": self.false_supported_rate,
            "supported_precision": self.supported_precision,
            "supported_recall": self.supported_recall,
            "unsupported_recall": self.unsupported_recall,
            "contradiction_recall": self.contradiction_recall,
            "manual_review_rate": self.manual_review_rate,
            "confusion": self.confusion,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)
```

Update `summarize` return block:

```python
    manual_review = sum(
        pred in {Label.PARTIALLY_SUPPORTED, Label.UNCERTAIN}
        for pred in predicted
    )
    return EvalSummary(
        total=total,
        accuracy=round(accuracy, 4),
        macro_f1=round(macro_f1, 4),
        false_supported_rate=round(_safe_div(false_supported, total), 4),
        supported_precision=round(_precision(Label.SUPPORTED, confusion), 4),
        supported_recall=round(_recall(Label.SUPPORTED, confusion), 4),
        unsupported_recall=round(_recall(Label.UNSUPPORTED, confusion), 4),
        contradiction_recall=round(_recall(Label.CONTRADICTED, confusion), 4),
        manual_review_rate=round(_safe_div(manual_review, total), 4),
        confusion=confusion,
    )
```

Add helpers:

```python
def _precision(label: Label, confusion: dict[str, dict[str, int]]) -> float:
    tp = confusion[label.value][label.value]
    fp = sum(confusion[other.value][label.value] for other in Label if other != label)
    return _safe_div(tp, tp + fp)


def _recall(label: Label, confusion: dict[str, dict[str, int]]) -> float:
    tp = confusion[label.value][label.value]
    fn = sum(confusion[label.value][other.value] for other in Label if other != label)
    return _safe_div(tp, tp + fn)
```

Refactor `_f1` to use `_precision` and `_recall`:

```python
def _f1(label: Label, confusion: dict[str, dict[str, int]]) -> float:
    precision = _precision(label, confusion)
    recall = _recall(label, confusion)
    return _safe_div(2 * precision * recall, precision + recall)
```

- [ ] **Step 4: Run metrics and eval tests**

Run:

```bash
uv run pytest tests/test_metrics.py tests/test_eval_runner.py -v
```

Expected: PASS.

- [ ] **Step 5: Run sample eval command**

Run:

```bash
uv run citeproof eval examples/edge_cases/claim_support.jsonl
```

Expected: JSON includes `supported_precision`, `supported_recall`, `unsupported_recall`, `contradiction_recall`, and `manual_review_rate`.

- [ ] **Step 6: Commit**

```bash
git add src/citeproof/evals/metrics.py tests/test_metrics.py
git commit -m "feat: add trust eval metrics"
```

## Task 3: Sentence-Window Rationale Selection

**Files:**
- Create: `src/citeproof/rationales.py`
- Create: `tests/test_rationales.py`

- [ ] **Step 1: Write failing rationale tests**

Create `tests/test_rationales.py`:

```python
from citeproof.models import Claim, SourceChunk
from citeproof.rationales import select_rationales


def test_select_rationale_prefers_sentence_window_with_claim_terms() -> None:
    chunk = SourceChunk(
        source_id="paper",
        citation_key="smith2024",
        chunk_id="paper:p1:0",
        page=1,
        text=(
            "The introduction discusses related work. "
            "Training with Method X required half as many hours as the baseline. "
            "The conclusion discusses deployment."
        ),
    )

    candidates = select_rationales(
        Claim("Method X reduces training time.", ("smith2024",)),
        [chunk],
        limit=1,
    )

    assert len(candidates) == 1
    assert "half as many hours" in candidates[0].text
    assert candidates[0].retrieval_method == "sentence_window"
    assert candidates[0].rank == 1


def test_select_rationale_returns_empty_for_source_silence() -> None:
    chunk = SourceChunk(
        source_id="paper",
        citation_key="smith2024",
        chunk_id="paper:p1:0",
        page=1,
        text="This paper describes a dataset collection interface.",
    )

    candidates = select_rationales(
        Claim("Method X reduces training time.", ("smith2024",)),
        [chunk],
        limit=3,
        min_score=0.2,
    )

    assert candidates == ()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_rationales.py -v
```

Expected: FAIL because `citeproof.rationales` does not exist.

- [ ] **Step 3: Implement rationale selector**

Create `src/citeproof/rationales.py`:

```python
"""Sentence-window rationale selection."""

from __future__ import annotations

from collections import Counter
from math import sqrt

from citeproof.models import Claim, EvidenceCandidate, SourceChunk
from citeproof.text import split_sentences, tokenize


def select_rationales(
    claim: Claim,
    chunks: list[SourceChunk],
    limit: int = 3,
    min_score: float = 0.12,
    window_radius: int = 1,
) -> tuple[EvidenceCandidate, ...]:
    """Return sentence/window evidence candidates for a claim."""

    scored: list[EvidenceCandidate] = []
    for chunk in chunks:
        for window in _sentence_windows(chunk.text, window_radius):
            score = _lexical_score(claim.text, window)
            if score >= min_score:
                scored.append(_candidate(chunk, window, score))
    ranked = sorted(scored, key=lambda item: item.lexical_score, reverse=True)[:limit]
    return tuple(
        EvidenceCandidate(
            source_id=item.source_id,
            citation_key=item.citation_key,
            text=item.text,
            chunk_id=item.chunk_id,
            title=item.title,
            page=item.page,
            lexical_score=item.lexical_score,
            semantic_score=item.semantic_score,
            rerank_score=item.rerank_score,
            rank=index,
            retrieval_method=item.retrieval_method,
        )
        for index, item in enumerate(ranked, start=1)
    )


def _sentence_windows(text: str, radius: int) -> tuple[str, ...]:
    sentences = split_sentences(text)
    if not sentences:
        return ()
    windows = []
    for index, _sentence in enumerate(sentences):
        start = max(0, index - radius)
        end = min(len(sentences), index + radius + 1)
        windows.append(" ".join(sentences[start:end]))
    return tuple(dict.fromkeys(windows))


def _candidate(chunk: SourceChunk, text: str, score: float) -> EvidenceCandidate:
    return EvidenceCandidate(
        source_id=chunk.source_id,
        citation_key=chunk.citation_key,
        text=text,
        chunk_id=chunk.chunk_id,
        title=chunk.title,
        page=chunk.page,
        lexical_score=round(score, 4),
        retrieval_method="sentence_window",
    )


def _lexical_score(claim: str, evidence: str) -> float:
    claim_terms = tokenize(claim)
    evidence_terms = tokenize(evidence)
    if not claim_terms or not evidence_terms:
        return 0.0
    claim_counts = Counter(claim_terms)
    evidence_counts = Counter(evidence_terms)
    overlap = sum(min(count, evidence_counts[term]) for term, count in claim_counts.items())
    return overlap / sqrt(len(claim_terms) * len(evidence_terms))
```

- [ ] **Step 4: Run rationale tests**

Run:

```bash
uv run pytest tests/test_rationales.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/citeproof/rationales.py tests/test_rationales.py
git commit -m "feat: add rationale span selection"
```

## Task 4: Trace-Aware Verifier

**Files:**
- Modify: `src/citeproof/adjudicator.py`
- Modify: `src/citeproof/verifier.py`
- Modify: `src/citeproof/report.py`
- Modify: `tests/test_verifier.py`

- [ ] **Step 1: Add failing verifier trace tests**

Append to `tests/test_verifier.py`:

```python
def test_verify_claim_includes_trace_for_supported_result(tmp_path: Path) -> None:
    (tmp_path / "smith2024.txt").write_text(
        "Training with Method X required half as many hours as the baseline.",
        encoding="utf-8",
    )

    result = verify_claim_text(
        "Method X reduces training time.",
        tmp_path,
        ["smith2024"],
    )
    data = result.to_dict()

    assert result.label == Label.SUPPORTED
    assert data["failure_mode"] is None
    assert data["trace"]["source_gate_status"] == "passed"
    assert data["trace"]["atom_verifications"][0]["rationales"]
    assert data["trace"]["atom_verifications"][0]["label"] == "supported"


def test_verify_claim_reports_failure_mode_for_missing_source(tmp_path: Path) -> None:
    (tmp_path / "smith2024.txt").write_text("Method X improves accuracy.", encoding="utf-8")

    result = verify_claim_text(
        "Method X improves accuracy.",
        tmp_path,
        ["missing2026"],
    )

    assert result.label == Label.UNCERTAIN
    assert result.failure_mode.value == "source_not_resolved"
    assert result.trace.final_failure_mode.value == "source_not_resolved"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_verifier.py::test_verify_claim_includes_trace_for_supported_result tests/test_verifier.py::test_verify_claim_reports_failure_mode_for_missing_source -v
```

Expected: FAIL because verifier results do not include traces or failure modes yet.

- [ ] **Step 3: Add failure-mode support to adjudicator**

In `src/citeproof/adjudicator.py`, import `FailureMode` and update judgment creation:

```python
from citeproof.models import Claim, EvidenceJudgment, FactInspection, FailureMode, Label
```

When facts contradict, choose a stable failure mode:

```python
    if facts.label == Label.CONTRADICTED:
        mode = _fact_failure_mode(facts)
        return EvidenceJudgment(Label.CONTRADICTED, 0.9, "; ".join(facts.findings), mode)
```

When facts partially support:

```python
    if facts.label == Label.PARTIALLY_SUPPORTED and heuristic.label != Label.UNSUPPORTED:
        mode = FailureMode.HEDGED_EVIDENCE if _has_hedge_finding(facts) else FailureMode.SCOPE_OVERSTATEMENT
        return EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.72, "; ".join(facts.findings), mode)
```

When NLI disagrees:

```python
        return EvidenceJudgment(
            Label.UNCERTAIN,
            min(nli.confidence, 0.65),
            "NLI predicts contradiction, but retrieved evidence has weak claim overlap.",
            FailureMode.MODEL_DISAGREEMENT,
        )
```

Add helpers:

```python
def _fact_failure_mode(facts: FactInspection) -> FailureMode:
    text = " ".join(facts.findings).lower()
    if "year conflict" in text:
        return FailureMode.YEAR_CONFLICT
    if "numeric conflict" in text:
        return FailureMode.NUMERIC_CONFLICT
    return FailureMode.CONFLICTING_SOURCES


def _has_hedge_finding(facts: FactInspection) -> bool:
    return any("hedged" in finding.lower() or "inconclusive" in finding.lower() for finding in facts.findings)
```

Expose atom combination for verifier traces by renaming `_combine_atom_judgments`:

```python
def combine_atom_judgments(judgments: list[EvidenceJudgment]) -> EvidenceJudgment:
    if not judgments:
        return EvidenceJudgment(
            Label.UNCERTAIN,
            0.2,
            "No atomic claims were produced.",
            FailureMode.NO_RATIONALE_SPAN,
        )
    labels = [judgment.label for judgment in judgments]
    if Label.CONTRADICTED in labels:
        strongest = max(
            (judgment for judgment in judgments if judgment.label == Label.CONTRADICTED),
            key=lambda judgment: judgment.confidence,
        )
        return strongest
    if all(label == Label.SUPPORTED for label in labels):
        confidence = min(judgment.confidence for judgment in judgments)
        return EvidenceJudgment(
            Label.SUPPORTED,
            confidence,
            "All atomic subclaims are supported.",
        )
    if any(label in {Label.SUPPORTED, Label.PARTIALLY_SUPPORTED} for label in labels):
        return EvidenceJudgment(
            Label.PARTIALLY_SUPPORTED,
            0.66,
            "Only some atomic subclaims are supported by the retrieved evidence.",
            FailureMode.MISSING_ATOM_SUPPORT,
        )
    if Label.UNCERTAIN in labels:
        return EvidenceJudgment(
            Label.UNCERTAIN,
            0.45,
            "Atomic subclaims could not be verified.",
            FailureMode.NO_RATIONALE_SPAN,
        )
    return EvidenceJudgment(
        Label.UNSUPPORTED,
        0.35,
        "No atomic subclaim is supported.",
        FailureMode.MISSING_ATOM_SUPPORT,
    )
```

Keep a compatibility alias:

```python
_combine_atom_judgments = combine_atom_judgments
```

- [ ] **Step 4: Implement trace construction in verifier**

In `src/citeproof/verifier.py`, import new pieces:

```python
from citeproof.adjudicator import adjudicate_evidence, combine_atom_judgments
from citeproof.claims import atomize_claim
from citeproof.models import (
    AtomVerification,
    Claim,
    ClaimVerificationTrace,
    EvidenceJudgment,
    FailureMode,
    Label,
    RationaleSpan,
    SourceChunk,
    VerificationResult,
)
from citeproof.rationales import select_rationales
```

For missing cited keys, return:

```python
        trace = ClaimVerificationTrace(
            claim=claim.text,
            citations=claim.citation_keys,
            source_gate_status="source_not_resolved",
            atom_verifications=(),
            final_label=Label.UNCERTAIN,
            final_confidence=0.2,
            final_failure_mode=FailureMode.SOURCE_NOT_RESOLVED,
            review_action="load cited source or fix citation key",
        )
        return VerificationResult(
            claim=claim.text,
            label=Label.UNCERTAIN,
            confidence=0.2,
            citations=claim.citation_keys,
            evidence=(),
            reason="At least one cited source key is missing from the loaded source set.",
            failure_mode=FailureMode.SOURCE_NOT_RESOLVED,
            trace=trace,
        )
```

For no retrieved evidence, return the same structure with `FailureMode.WEAK_RETRIEVAL`, label `Label.UNSUPPORTED`, source gate status `passed`, and review action `"find stronger evidence or remove citation"`.

Replace the final judgment block with:

```python
    atom_verifications = _verify_atoms(claim, retrieved, judge)
    atom_judgment = combine_atom_judgments(
        [
            EvidenceJudgment(atom.label, atom.confidence, atom.reason, atom.failure_mode)
            for atom in atom_verifications
        ]
    )
    evidence = tuple(
        rationale.to_evidence()
        for atom in atom_verifications
        for rationale in atom.rationales
    )
    trace = ClaimVerificationTrace(
        claim=claim.text,
        citations=claim.citation_keys,
        source_gate_status="passed",
        atom_verifications=tuple(atom_verifications),
        final_label=atom_judgment.label,
        final_confidence=round(atom_judgment.confidence, 3),
        final_failure_mode=atom_judgment.failure_mode,
        review_action=_review_action(atom_judgment.failure_mode),
    )
    return VerificationResult(
        claim=claim.text,
        label=atom_judgment.label,
        confidence=round(atom_judgment.confidence, 3),
        citations=claim.citation_keys,
        evidence=evidence,
        reason=atom_judgment.reason,
        failure_mode=atom_judgment.failure_mode,
        trace=trace,
    )
```

Add helpers:

```python
def _verify_atoms(claim: Claim, chunks: list[SourceChunk], judge: Judge) -> list[AtomVerification]:
    verifications: list[AtomVerification] = []
    group = atomize_claim(claim)
    for atom in group.atoms:
        atom_claim = Claim(atom.text, atom.citation_keys)
        candidates = select_rationales(atom_claim, chunks, limit=2)
        if not candidates:
            verifications.append(
                AtomVerification(
                    text=atom.text,
                    context=atom.context,
                    label=Label.UNSUPPORTED,
                    confidence=0.3,
                    rationales=(),
                    failure_mode=FailureMode.NO_RATIONALE_SPAN,
                    reason="No rationale span was selected for this atom.",
                )
            )
            continue
        top = candidates[0]
        judgment = adjudicate_evidence(atom.text, top.text, judge=judge)
        rationales = tuple(
            RationaleSpan(
                source_id=candidate.source_id,
                citation_key=candidate.citation_key,
                text=candidate.text,
                page=candidate.page,
                relation=_relation_for(judgment.label),
                score=candidate.lexical_score,
            )
            for candidate in candidates
        )
        verifications.append(
            AtomVerification(
                text=atom.text,
                context=atom.context,
                label=judgment.label,
                confidence=round(judgment.confidence, 3),
                rationales=rationales,
                failure_mode=judgment.failure_mode,
                reason=judgment.reason,
            )
        )
    return verifications


def _relation_for(label: Label) -> str:
    if label == Label.SUPPORTED:
        return "support"
    if label == Label.CONTRADICTED:
        return "contradict"
    if label == Label.UNSUPPORTED:
        return "neutral"
    return "undetermined"


def _review_action(mode: FailureMode | None) -> str:
    if mode is None:
        return "none"
    actions = {
        FailureMode.SOURCE_NOT_RESOLVED: "load cited source or fix citation key",
        FailureMode.WEAK_RETRIEVAL: "find stronger evidence or remove citation",
        FailureMode.NO_RATIONALE_SPAN: "find exact supporting span or narrow the claim",
        FailureMode.MISSING_ATOM_SUPPORT: "rewrite unsupported atom or add a better citation",
        FailureMode.NUMERIC_CONFLICT: "fix the numeric value or cite a matching source",
        FailureMode.YEAR_CONFLICT: "fix the year or cite a matching source",
        FailureMode.HEDGED_EVIDENCE: "hedge the claim or cite stronger evidence",
        FailureMode.SCOPE_OVERSTATEMENT: "narrow the claim scope",
        FailureMode.MODEL_DISAGREEMENT: "manually inspect model disagreement",
    }
    return actions.get(mode, "manually inspect cited evidence")
```

- [ ] **Step 5: Update report rendering**

In `src/citeproof/report.py`, after `Reason`, add:

```python
                f"**Failure mode:** {result.failure_mode.value if result.failure_mode else 'none'}",
                "",
```

After evidence rendering, add compact atom trace lines:

```python
        if result.trace:
            lines.extend(["**Atoms:**", ""])
            for atom in result.trace.atom_verifications:
                mode = atom.failure_mode.value if atom.failure_mode else "none"
                lines.append(f"- `{atom.label.value}` {atom.text} (failure={mode})")
            lines.append("")
```

- [ ] **Step 6: Run verifier tests**

Run:

```bash
uv run pytest tests/test_verifier.py tests/test_adjudicator.py tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 7: Run report smoke command**

Run:

```bash
uv run citeproof verify examples/draft.md --sources examples/sources --format json
```

Expected: JSON results include `trace` and `failure_mode`.

- [ ] **Step 8: Commit**

```bash
git add src/citeproof/adjudicator.py src/citeproof/verifier.py src/citeproof/report.py tests/test_verifier.py
git commit -m "feat: add trace-aware verification"
```

## Task 5: Eval Failure Modes And Fast Regression Cases

**Files:**
- Modify: `src/citeproof/evals/runner.py`
- Modify: `tests/test_eval_runner.py`
- Modify: `examples/edge_cases/claim_support.jsonl`

- [ ] **Step 1: Update eval diagnostics test**

Change the expected row in `tests/test_eval_runner.py::test_eval_cases_include_trust_diagnostics` to include `failure_mode`:

```python
    assert cases == [
        {
            "id": "fake-support",
            "expected_label": "unsupported",
            "predicted_label": "supported",
            "confidence": 0.95,
            "failure_mode": None,
            "false_supported": True,
            "pass": False,
            "reason": "Verifier gates agree.",
        }
    ]
```

- [ ] **Step 2: Run eval diagnostics test to verify failure**

Run:

```bash
uv run pytest tests/test_eval_runner.py::test_eval_cases_include_trust_diagnostics -v
```

Expected: FAIL because rows do not include `failure_mode`.

- [ ] **Step 3: Include failure mode in eval rows**

In `src/citeproof/evals/runner.py`, add this field:

```python
                "failure_mode": judgment.failure_mode.value if judgment.failure_mode else None,
```

Place it between `confidence` and `false_supported`.

- [ ] **Step 4: Add fast-regression edge cases**

Append to `examples/edge_cases/claim_support.jsonl`:

```json
{"id":"unit-conflict","claim":"The evaluation used 42 percent of the dataset.","evidence":"The evaluation used 42 examples from the dataset.","expected_label":"contradicted"}
{"id":"metric-swap","claim":"Method X improves F1 score over the baseline.","evidence":"Method X improves accuracy over the baseline but does not improve F1 score.","expected_label":"contradicted"}
{"id":"neighboring-paragraph-support","claim":"Method X reduces training time.","evidence":"The first paragraph describes setup. Training with Method X required half as many hours as the baseline. The next paragraph discusses limitations.","expected_label":"supported"}
```

- [ ] **Step 5: Add targeted deterministic tests for new edge categories**

Add to `tests/test_fact_lenses.py`:

```python
def test_detects_unit_conflict_for_same_number() -> None:
    result = inspect_facts(
        "The evaluation used 42 percent of the dataset.",
        "The evaluation used 42 examples from the dataset.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Unit conflict" in finding for finding in result.findings)
```

Add to `tests/test_entailment.py`:

```python
def test_detects_metric_negation_as_contradiction() -> None:
    judgment = judge_evidence(
        "Method X improves F1 score over the baseline.",
        "Method X improves accuracy over the baseline but does not improve F1 score.",
    )

    assert judgment.label == Label.CONTRADICTED
```

- [ ] **Step 6: Run targeted deterministic tests to verify failure**

Run:

```bash
uv run pytest tests/test_fact_lenses.py::test_detects_unit_conflict_for_same_number tests/test_entailment.py::test_detects_metric_negation_as_contradiction -v
```

Expected: FAIL until the deterministic checks below are added.

- [ ] **Step 7: Add unit-conflict fact lens**

In `src/citeproof/fact_lenses.py`, update `inspect_facts`:

```python
    findings = (
        _number_conflicts(claim, evidence)
        + _unit_conflicts(claim, evidence)
        + _year_conflicts(claim, evidence)
    )
```

Add helpers:

```python
def _unit_conflicts(claim: str, evidence: str) -> list[str]:
    claim_numbers = _numbers_to_units(claim)
    evidence_numbers = _numbers_to_units(evidence)
    findings: list[str] = []
    for number, claim_units in claim_numbers.items():
        evidence_units = evidence_numbers.get(number, set())
        if evidence_units and claim_units != evidence_units:
            findings.append(
                f"Unit conflict for {number}: claim {sorted(claim_units)} vs evidence {sorted(evidence_units)}"
            )
    return findings


def _numbers_to_units(text: str) -> dict[str, set[str]]:
    numbers: dict[str, set[str]] = {}
    for unit, mentions in _number_units(text).items():
        for mention in mentions:
            numbers.setdefault(mention.number, set()).add(unit)
    return numbers
```

- [ ] **Step 8: Add metric negation pattern**

In `src/citeproof/entailment.py`, extend `NEGATING_EVIDENCE_RE`:

```python
NEGATING_EVIDENCE_RE = re.compile(
    r"\b(no statistically significant|not significant|does not improve|did not improve|"
    r"failed to improve|does not reduce|did not reduce|failed to reduce|no reduction|"
    r"does not cover|did not cover|does not span|did not span|does not improve f1 score|"
    r"did not improve f1 score|failed to improve f1 score|"
    r"comparable to|similar to|no improvement|worse than|lower than)\b",
    re.IGNORECASE,
)
```

- [ ] **Step 9: Run focused eval tests**

Run:

```bash
uv run pytest tests/test_eval_runner.py -v
uv run citeproof eval examples/edge_cases/claim_support.jsonl --details-output reports/edge_cases_heuristic.json
```

Expected:

- tests pass
- eval prints JSON with secondary metrics
- `false_supported_rate` remains `0.0`

- [ ] **Step 10: Commit**

```bash
git add src/citeproof/evals/runner.py tests/test_eval_runner.py examples/edge_cases/claim_support.jsonl src/citeproof/fact_lenses.py src/citeproof/entailment.py tests/test_fact_lenses.py tests/test_entailment.py
git commit -m "test: expand strict verifier regressions"
```

## Task 6: Documentation And Score Ledger

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Update README verification model**

In `README.md`, add this paragraph after the conservative ordering:

```markdown
Strict verification results include a trust trace when available. The trace
records source-gate status, atom-level labels, selected rationale spans, stable
failure modes, and a review action. This lets a writer or agent repair the
specific unsupported atom instead of guessing why a claim failed.
```

- [ ] **Step 2: Update evaluation docs**

In `docs/evaluation.md`, add secondary metric definitions:

```markdown
- `supported_precision`: share of `supported` predictions that were actually supported.
- `supported_recall`: share of supported expected cases recovered as `supported`.
- `unsupported_recall`: share of unsupported expected cases correctly rejected.
- `contradiction_recall`: share of contradicted expected cases caught as `contradicted`.
- `manual_review_rate`: share of predictions returned as `partially_supported` or `uncertain`.
```

Refresh the local score table after running the commands in Step 3.

- [ ] **Step 3: Run full verification commands**

Run:

```bash
uv run pytest
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output reports/hallucination_bib_gated_details.json
git diff --check
```

Expected:

- pytest passes
- all eval commands complete
- `false_supported_rate` stays `0.0` on local benchmarks
- diff check is clean

- [ ] **Step 4: Commit**

```bash
git add README.md docs/evaluation.md reports/edge_cases_heuristic.json reports/hallucination_bib_gated_details.json
git commit -m "docs: document strict verifier traces"
```

## Task 7: Push And CI Verification

**Files:**
- No source changes.

- [ ] **Step 1: Inspect local status**

Run:

```bash
git status --short --branch
```

Expected: branch is ahead of `origin/main` with no uncommitted source changes.

- [ ] **Step 2: Push**

Run:

```bash
git push
```

Expected: push to `https://github.com/SebastianBoehler/citeproof.git` succeeds.

- [ ] **Step 3: Watch CI**

Run:

```bash
gh run list --repo SebastianBoehler/citeproof --branch main --limit 3
gh run watch <latest-run-id> --repo SebastianBoehler/citeproof --exit-status
```

Expected: tests workflow passes on Python 3.11, 3.12, and 3.13.

## Self-Review Notes

- Spec coverage: This plan implements trace data models, stable failure modes, richer JSON details, secondary metrics, adversarial fast-regression cases, sentence/window rationale selection, and atom-level rationale coverage. It intentionally defers semantic embeddings, rerankers, LLM auditor, SciFact adapters, and repair-loop generation to separate future plans.
- Type consistency: `FailureMode`, `EvidenceCandidate`, `RationaleSpan`, `AtomVerification`, and `ClaimVerificationTrace` are defined before any task consumes them. `EvidenceJudgment.failure_mode` is added with a default, so existing call sites remain valid.
- Safety invariant: every task preserves the central rule that `supported` must not bypass citation scope, rationale coverage, deterministic fact lenses, or enabled model-gate disagreement.
