# Conservative Hybrid Verifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Track each checkbox while executing.

**Goal:** Implement the first conservative verifier phase: context-preserving claim atoms, deterministic fact lenses, conservative adjudication, and score reporting that makes false `supported` labels visible.

**Success check:** `uv run pytest` passes; edge-case eval writes a details report with `accuracy`, `macro_f1`, and `false_supported_rate`; false-supported does not regress from the current baseline.

## Files

- Create `src/citeproof/claims.py`
- Create `src/citeproof/fact_lenses.py`
- Create `src/citeproof/adjudicator.py`
- Modify `src/citeproof/models.py`
- Modify `src/citeproof/verifier.py`
- Modify `src/citeproof/evals/runner.py`
- Modify `examples/edge_cases/claim_support.jsonl`
- Add `tests/test_claims.py`, `tests/test_fact_lenses.py`, `tests/test_adjudicator.py`
- Update `README.md`; create `docs/evaluation.md`

## Task 1: Context-Preserving Atomic Claims

- [ ] Add failing tests in `tests/test_claims.py`.

```python
from citeproof.claims import atomize_claim
from citeproof.models import Claim


def test_atomize_preserves_original_context() -> None:
    claim = Claim("WildChat contains 1M conversations and spans diverse languages.", ("wildchat",))
    group = atomize_claim(claim)
    assert [atom.text for atom in group.atoms] == [
        "WildChat contains 1M conversations.",
        "WildChat spans diverse languages.",
    ]
    assert all(atom.context == claim.text for atom in group.atoms)
    assert all(atom.citation_keys == ("wildchat",) for atom in group.atoms)


def test_atomize_does_not_split_unrelated_short_sentence() -> None:
    claim = Claim("BERTScore computes contextual embedding similarity.", ("bertscore",))
    group = atomize_claim(claim)
    assert [atom.text for atom in group.atoms] == [claim.text]
```

- [ ] Run `uv run pytest tests/test_claims.py -v`; expect import failure.
- [ ] Add to `src/citeproof/models.py`.

```python
@dataclass(frozen=True)
class AtomicClaim:
    text: str
    context: str
    citation_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaimGroup:
    original: Claim
    atoms: tuple[AtomicClaim, ...]
```

- [ ] Implement `src/citeproof/claims.py`.

```python
"""Context-preserving claim atomization."""

from __future__ import annotations

import re

from citeproof.models import AtomicClaim, Claim, ClaimGroup


AND_SPLIT_RE = re.compile(
    r"^(?P<subject>[A-Z][A-Za-z0-9_.-]+)\s+(?P<first>.+?)\s+and\s+"
    r"(?P<second>(?:spans|contains|uses|trains|provides|computes|captures|"
    r"improves|reduces|increases|decreases|outperforms)\b.+)$"
)


def atomize_claim(claim: Claim) -> ClaimGroup:
    text = claim.text.strip()
    match = AND_SPLIT_RE.match(text.rstrip("."))
    if not match:
        atoms = (_atomic(claim, text),)
    else:
        subject = match.group("subject")
        atoms = (
            _atomic(claim, f"{subject} {match.group('first').strip()}."),
            _atomic(claim, f"{subject} {match.group('second').strip()}."),
        )
    return ClaimGroup(original=claim, atoms=atoms)


def _atomic(claim: Claim, text: str) -> AtomicClaim:
    return AtomicClaim(re.sub(r"\s+", " ", text).strip(), claim.text, claim.citation_keys)
```

- [ ] Run `uv run pytest tests/test_claims.py -v`; expect pass.
- [ ] Commit: `git add src/citeproof/models.py src/citeproof/claims.py tests/test_claims.py && git commit -m "feat: add context-preserving claim atoms"`.

## Task 2: Deterministic Fact Lenses

- [ ] Add failing tests in `tests/test_fact_lenses.py`.

```python
from citeproof.fact_lenses import inspect_facts
from citeproof.models import Label


def test_detects_number_conflict_with_units() -> None:
    result = inspect_facts("Trained with 4 GPUs.", "Trained with 1 GPU.")
    assert result.label == Label.CONTRADICTED


def test_detects_year_conflict() -> None:
    result = inspect_facts("Published in 2025.", "Released in 2024.")
    assert result.label == Label.CONTRADICTED


def test_detects_hedged_partial_support() -> None:
    result = inspect_facts("The adapter improves transfer.", "The adapter may improve transfer.")
    assert result.label == Label.PARTIALLY_SUPPORTED
```

- [ ] Run `uv run pytest tests/test_fact_lenses.py -v`; expect import failure.
- [ ] Add `FactInspection` to `src/citeproof/models.py`.

```python
@dataclass(frozen=True)
class FactInspection:
    label: Label | None
    findings: tuple[str, ...] = ()
```

- [ ] Implement `src/citeproof/fact_lenses.py`.

```python
"""Deterministic checks for high-risk factual conflicts."""

from __future__ import annotations

import re

from citeproof.models import FactInspection, Label

NUMBER_UNIT_RE = re.compile(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(%|percent|examples?|samples?|GPUs?|conversations?|languages?)", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
HEDGE_RE = re.compile(r"\b(may|might|could|inconclusive|suggests|preliminary)\b", re.I)


def inspect_facts(claim: str, evidence: str) -> FactInspection:
    findings = _number_conflicts(claim, evidence) + _year_conflicts(claim, evidence)
    if findings:
        return FactInspection(Label.CONTRADICTED, tuple(findings))
    if HEDGE_RE.search(evidence) and not HEDGE_RE.search(claim):
        return FactInspection(Label.PARTIALLY_SUPPORTED, ("Evidence is hedged.",))
    return FactInspection(None, ())
```

- [ ] Add private helpers `_number_conflicts`, `_year_conflicts`, and `_number_units`.
- [ ] Run `uv run pytest tests/test_fact_lenses.py -v`; expect pass.
- [ ] Commit: `git add src/citeproof/models.py src/citeproof/fact_lenses.py tests/test_fact_lenses.py && git commit -m "feat: add deterministic fact lenses"`.

## Task 3: Conservative Adjudicator

- [ ] Add failing tests in `tests/test_adjudicator.py`.

```python
from citeproof.adjudicator import adjudicate_judgments
from citeproof.models import EvidenceJudgment, FactInspection, Label


def test_fact_contradiction_overrides_nli_support() -> None:
    result = adjudicate_judgments(
        EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.7, "overlap"),
        FactInspection(Label.CONTRADICTED, ("Year conflict",)),
        EvidenceJudgment(Label.SUPPORTED, 0.99, "entailment"),
    )
    assert result.label == Label.CONTRADICTED


def test_supported_requires_heuristic_and_nli_support() -> None:
    result = adjudicate_judgments(
        EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.72, "partial"),
        FactInspection(None, ()),
        EvidenceJudgment(Label.SUPPORTED, 0.98, "entailment"),
    )
    assert result.label == Label.PARTIALLY_SUPPORTED
```

- [ ] Run `uv run pytest tests/test_adjudicator.py -v`; expect import failure.
- [ ] Implement `src/citeproof/adjudicator.py`.

```python
"""Conservative verifier adjudication."""

from __future__ import annotations

from citeproof.models import EvidenceJudgment, FactInspection, Label


def adjudicate_judgments(
    heuristic: EvidenceJudgment,
    facts: FactInspection,
    nli: EvidenceJudgment | None = None,
) -> EvidenceJudgment:
    if facts.label == Label.CONTRADICTED:
        return EvidenceJudgment(Label.CONTRADICTED, 0.9, "; ".join(facts.findings))
    if facts.label == Label.PARTIALLY_SUPPORTED:
        return EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.72, "; ".join(facts.findings))
    if nli and nli.label == Label.CONTRADICTED and heuristic.label == Label.UNSUPPORTED:
        return EvidenceJudgment(Label.UNCERTAIN, 0.65, "NLI contradiction with weak retrieval.")
    if nli and nli.label == Label.CONTRADICTED:
        return EvidenceJudgment(Label.CONTRADICTED, nli.confidence, nli.reason)
    if heuristic.label == Label.SUPPORTED and (nli is None or nli.label == Label.SUPPORTED):
        return EvidenceJudgment(Label.SUPPORTED, min(heuristic.confidence, nli.confidence if nli else heuristic.confidence), "Verifier gates agree.")
    if heuristic.label == Label.SUPPORTED and nli:
        return EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.68, "NLI did not confirm full support.")
    return heuristic
```

- [ ] Thread adjudication into `src/citeproof/verifier.py` by running the existing heuristic judge, optional NLI judge, `inspect_facts`, then `_choose_judgment`.
- [ ] Run `uv run pytest tests/test_adjudicator.py tests/test_verifier.py -v`; expect pass.
- [ ] Commit: `git add src/citeproof/adjudicator.py src/citeproof/verifier.py tests/test_adjudicator.py && git commit -m "feat: add conservative adjudicator"`.

## Task 4: Score Reporting and Edge Cases

- [ ] Add two rows to `examples/edge_cases/claim_support.jsonl`.

```json
{"id":"compound-dataset-partial","claim":"WildChat contains 1M conversations and provides medical expert annotations.","evidence":"WildChat contains 1M ChatGPT interaction logs spanning diverse topics and languages.","expected_label":"partially_supported"}
{"id":"compound-dataset-supported","claim":"WildChat contains 1M conversations and spans diverse languages.","evidence":"WildChat contains 1M ChatGPT interaction logs and covers multiple languages.","expected_label":"supported"}
```

- [ ] Ensure eval details include `id`, `expected`, `predicted`, `confidence`, `false_supported`, and `reason`.
- [ ] Run `uv run citeproof eval examples/edge_cases/claim_support.jsonl --details-output reports/edge_cases_heuristic.json`.
- [ ] If `compound-dataset-partial` is `supported`, make atom-level missing support cap the parent at `partially_supported`.
- [ ] Run:

```bash
uv run pytest
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output reports/hallucination_bib_gated_details.json
```

- [ ] Commit: `git add examples/edge_cases/claim_support.jsonl src/citeproof/evals/runner.py tests/test_eval_runner.py && git commit -m "test: expand conservative verifier scoring"`.

## Task 5: Documentation

- [ ] Add README section:

```markdown
## Conservative Policy

CiteProof optimizes first for avoiding false `supported` labels. A claim is
only `supported` when citation metadata, source resolution, retrieval, fact
lenses, and optional NLI agree. When signals disagree, CiteProof keeps the claim
in the review queue as `partially_supported`, `uncertain`, or `unsupported`.
```

- [ ] Create `docs/evaluation.md` with benchmark list, primary metric `false_supported_rate`, and the latest local scores.
- [ ] Run `uv run pytest && git diff --check`.
- [ ] Commit: `git add README.md docs/evaluation.md && git commit -m "docs: document conservative evaluation policy"`.

## Self-Review

- Spec coverage: covers phase 1 atoms, fact lenses, conservative adjudication, score reporting, and expanded edge cases.
- Atomizer risk: atoms preserve original context and are a coverage check, not a replacement for the full claim.
- Trust requirement: report false-supported rate, accuracy, macro-F1, and per-case failures.
- Deferred: SciFact/SciFact-Open adapters, semantic retrieval calibration, HALLMARK integration, and repair-loop UI.
