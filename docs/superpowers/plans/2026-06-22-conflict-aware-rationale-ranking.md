# Conflict-Aware Rationale Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent false-supported draft results when a contradicting sentence window is retrieved but ranked below high-overlap support-like distractors.

**Architecture:** Extend `select_rationales` with a deterministic rerank score. Keep the existing lexical score as the public evidence score, add a conflict-cue bonus only for windows already above the minimum lexical threshold, and store the ranking score in `EvidenceCandidate.rerank_score`.

**Tech Stack:** Python stdlib regex, existing `EvidenceCandidate`, pytest, ruff, uv.

---

## File Structure

- Modify `src/citeproof/rationales.py`: add conflict cue detection and rerank sorting.
- Modify `tests/test_rationales.py`: add direct ranking regression.
- Modify `tests/test_verifier.py`: add end-to-end false-supported regression.

## Task 1: Failing Rationale Ranking Tests

**Files:**
- Modify: `tests/test_rationales.py`
- Modify: `tests/test_verifier.py`

- [ ] **Step 1: Add direct rationale ranking test**

Append to `tests/test_rationales.py`:

```python
def test_select_rationale_promotes_relevant_conflict_cue_window() -> None:
    distractors = " ".join(
        f"Method X improves accuracy over PPO in robotics benchmark {index}."
        for index in range(8)
    )
    chunk = SourceChunk(
        source_id="paper",
        citation_key="paper",
        chunk_id="paper:0",
        text=(
            f"{distractors} "
            "Calibration remains unchanged after applying the method. "
            "The reliability curve shows no difference from PPO."
        ),
    )

    candidates = select_rationales(
        Claim("Method X improves calibration over PPO.", ("paper",)),
        [chunk],
        limit=1,
        min_score=0.08,
    )

    assert len(candidates) == 1
    assert "Calibration remains unchanged" in candidates[0].text
    assert candidates[0].rerank_score is not None
    assert candidates[0].rerank_score > candidates[0].lexical_score
```

- [ ] **Step 2: Add end-to-end verifier regression**

Append to `tests/test_verifier.py`:

```python
def test_verify_claim_surfaces_low_ranked_calibration_contradiction() -> None:
    paragraphs = [
        (
            f"Method X improves accuracy over PPO in robotics benchmark {index}. "
            "The experiment reports higher throughput and better sample efficiency for Method X."
        )
        for index in range(12)
    ]
    paragraphs.append(
        "Calibration remains unchanged after applying the method. "
        "The reliability curve and expected calibration error show no difference from PPO."
    )
    source = Source(
        source_id="paper",
        citation_key="paper",
        text="\n\n".join(paragraphs),
    )

    result = verify_claim(
        Claim("Method X improves calibration over PPO.", ("paper",)),
        build_chunks([source]),
    )

    assert result.label == Label.CONTRADICTED
    assert result.trace is not None
    atom = result.trace.atom_verifications[0]
    assert atom.contradiction_candidate_count >= 1
    assert atom.best_contradiction_rank == 1
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest \
  tests/test_rationales.py::test_select_rationale_promotes_relevant_conflict_cue_window \
  tests/test_verifier.py::test_verify_claim_surfaces_low_ranked_calibration_contradiction \
  -q
```

Expected: both tests fail with the current lexical-only ranking.

## Task 2: Conflict-Aware Rerank Implementation

**Files:**
- Modify: `src/citeproof/rationales.py`
- Test: `tests/test_rationales.py`, `tests/test_verifier.py`

- [ ] **Step 1: Add conflict cue regex and bonus constant**

Add near the imports:

```python
import re
```

Add constants:

```python
CONFLICT_RERANK_BONUS = 0.22
CONFLICT_CUE_RE = re.compile(
    r"\b("
    r"unchanged|no\s+change|no\s+difference|no\s+improvement|no\s+reduction|"
    r"does\s+not\s+improve|did\s+not\s+improve|failed\s+to\s+improve|"
    r"not\s+statistically\s+significant|comparable\s+to|equivalent\s+to|worse\s+than"
    r")\b",
    re.IGNORECASE,
)
```

- [ ] **Step 2: Use rerank score in selection**

Replace the scoring block in `select_rationales` with:

```python
    scored: list[EvidenceCandidate] = []
    for chunk in chunks:
        for window in _sentence_windows(chunk.text, window_radius):
            lexical_score = _lexical_score(claim.text, window)
            if lexical_score < min_score:
                continue
            rerank_score = lexical_score + _conflict_rerank_bonus(window)
            scored.append(_candidate(chunk, window, lexical_score, rerank_score))
    ranked = sorted(
        scored,
        key=lambda item: (item.rerank_score or item.lexical_score, item.lexical_score),
        reverse=True,
    )[:limit]
```

- [ ] **Step 3: Store rerank score on candidates**

Change `_candidate` signature to:

```python
def _candidate(chunk: SourceChunk, text: str, lexical_score: float, rerank_score: float) -> EvidenceCandidate:
```

Set:

```python
lexical_score=round(lexical_score, 4),
rerank_score=round(rerank_score, 4),
```

When rebuilding ranked candidates, preserve `rerank_score=item.rerank_score`.

- [ ] **Step 4: Add bonus helper**

Add:

```python
def _conflict_rerank_bonus(text: str) -> float:
    return CONFLICT_RERANK_BONUS if CONFLICT_CUE_RE.search(text) else 0.0
```

- [ ] **Step 5: Run targeted tests**

Run:

```bash
uv run pytest tests/test_rationales.py tests/test_verifier.py::test_verify_claim_surfaces_low_ranked_calibration_contradiction -q
```

Expected: targeted tests pass.

## Task 3: Full Verification and Commit

**Files:**
- All modified files.

- [ ] **Step 1: Run full tests**

Run:

```bash
uv run pytest -q -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 2: Run benchmark commands**

Run:

```bash
uv run citeproof eval-suite examples/eval_suite.json
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output reports/hallucination_bib_gated_details.json
```

Expected: all commands pass; false-supported rate remains `0.0`.

- [ ] **Step 3: Run lint**

Run: `uv run ruff check --no-cache .`

Expected: no lint failures.

- [ ] **Step 4: Commit**

Run:

```bash
git add src/citeproof/rationales.py tests/test_rationales.py tests/test_verifier.py
git commit -m "fix: promote conflict rationale candidates"
```

- [ ] **Step 5: Push and check CI**

Run:

```bash
git push origin main
gh run list --branch main --limit 1
gh run watch <latest-run-id> --exit-status
```

Expected: pushed commit is on `origin/main`; CI passes.
