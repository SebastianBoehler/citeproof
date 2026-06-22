# Citation-Local Clauses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split explicitly separated citation-local clauses into independent `Claim` objects.

**Architecture:** Extend the existing parser boundary function, `split_citation_clauses()`, without changing retrieval, atomization, or adjudication. The parser should split only when the resulting pieces each carry citations, preserving conservative behavior for uncited prose.

**Tech Stack:** Python stdlib regex, existing parser/verifier tests, existing JSONL eval runner.

---

## File Structure

- Modify `src/citeproof/parser.py`: add explicit comma/discourse-marker citation clause splitting.
- Modify `tests/test_parser.py`: add parser-level examples for comma `while`, `but`, `and`, and non-splitting cases.
- Modify `tests/test_verifier.py` only if the file stays under 300 lines; otherwise create `tests/test_verifier_citation_clauses.py` for draft-level verification behavior.
- Optionally modify `examples/edge_cases/claim_support.jsonl`, `tests/test_eval_runner.py`, and `docs/evaluation.md` only if a compact direct eval row is useful. Prefer draft-level unit tests for clause parsing because JSONL eval rows do not exercise draft parsing.

## Task 1: Parser Boundaries

**Files:**
- Modify: `src/citeproof/parser.py`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Add failing parser tests**

Add tests to `tests/test_parser.py`:

```python
def test_parse_claims_splits_comma_while_citation_clauses() -> None:
    claims = parse_claims(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, "
        "while Prefix Tuning improves accuracy on SQuAD \\cite{prefix2021}."
    )

    assert claims == [
        Claim("LoRA improves accuracy on GLUE.", ("lora2021",)),
        Claim("Prefix Tuning improves accuracy on SQuAD.", ("prefix2021",)),
    ]


def test_split_citation_clauses_requires_citations_on_both_sides() -> None:
    clauses = split_citation_clauses(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, while the baseline is unchanged."
    )

    assert clauses == [
        "LoRA improves accuracy on GLUE \\cite{lora2021}, while the baseline is unchanged."
    ]
```

Also add one test for comma `but` and one for comma `and`, each with citations on both sides.

- [ ] **Step 2: Verify parser tests fail**

Run:

```bash
python -m pytest tests/test_parser.py -q -p no:cacheprovider
```

Expected: new comma-marker tests fail because the current parser returns one claim.

- [ ] **Step 3: Implement conservative splitting**

In `src/citeproof/parser.py`:

- add a regex for `,\s+(while|whereas|but|and)\s+`;
- split into pieces while removing the marker from the second clause;
- append terminal punctuation with `_ensure_terminal_punctuation()`;
- return split pieces only when at least two pieces contain citations.

- [ ] **Step 4: Verify Task 1**

Run:

```bash
python -m pytest tests/test_parser.py -q -p no:cacheprovider
ruff check --no-cache src/citeproof/parser.py tests/test_parser.py
git diff --check
wc -l src/citeproof/parser.py tests/test_parser.py
```

Expected: parser tests pass, lint passes, no whitespace errors, files remain under 300 lines.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/citeproof/parser.py tests/test_parser.py
git commit -m "feat: split citation-local clauses"
```

## Task 2: Draft Verification Coverage

**Files:**
- Create: `tests/test_verifier_citation_clauses.py`

- [ ] **Step 1: Add draft-level tests**

Create `tests/test_verifier_citation_clauses.py`:

```python
from pathlib import Path

from citeproof.models import Label
from citeproof.verifier import verify_draft


def test_verify_draft_localizes_supported_citation_clauses(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "lora2021.txt").write_text("LoRA improves accuracy on GLUE.", encoding="utf-8")
    (sources / "prefix2021.txt").write_text(
        "Prefix Tuning improves accuracy on SQuAD.", encoding="utf-8"
    )
    draft = tmp_path / "draft.md"
    draft.write_text(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, "
        "while Prefix Tuning improves accuracy on SQuAD \\cite{prefix2021}.",
        encoding="utf-8",
    )

    results = verify_draft(draft, sources)

    assert [result.label for result in results] == [Label.SUPPORTED, Label.SUPPORTED]
    assert [result.citations for result in results] == [("lora2021",), ("prefix2021",)]


def test_verify_draft_localizes_wrong_second_clause(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "lora2021.txt").write_text("LoRA improves accuracy on GLUE.", encoding="utf-8")
    (sources / "prefix2021.txt").write_text(
        "Prefix Tuning improves accuracy on SQuAD.", encoding="utf-8"
    )
    draft = tmp_path / "draft.md"
    draft.write_text(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, "
        "while Prefix Tuning improves accuracy on GLUE \\cite{prefix2021}.",
        encoding="utf-8",
    )

    results = verify_draft(draft, sources)

    assert results[0].label == Label.SUPPORTED
    assert results[1].label == Label.CONTRADICTED
```

- [ ] **Step 2: Verify draft tests pass**

Run:

```bash
python -m pytest tests/test_verifier_citation_clauses.py -q -p no:cacheprovider
```

Expected: both tests pass after Task 1 parser change.

- [ ] **Step 3: Full local verification**

Run:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl --details-output /tmp/citeproof_citation_clauses_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl --details-output /tmp/citeproof_citation_clauses_hallucination.json
git diff --check
wc -l src/citeproof/parser.py tests/test_parser.py tests/test_verifier_citation_clauses.py
```

Expected: all tests and evals pass; false-supported rate remains 0.0; files stay below 300 lines.

- [ ] **Step 4: Commit Task 2**

```bash
git add tests/test_verifier_citation_clauses.py
git commit -m "test: cover citation-local draft verification"
```
