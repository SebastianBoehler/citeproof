# CiteProof

CiteProof verifies whether citation-bearing claims are supported by their cited
sources. The first scaffold is intentionally small: it separates parsing,
retrieval, entailment/contradiction labels, reporting, and evaluation so we can
measure changes before building editor or SaaS surfaces.

## Current Scope

- Parse Markdown/LaTeX-style citation claims, including explicit citation-level
  clauses split by semicolons.
- Load local PDF, text, Markdown, or JSONL sources from any directory.
- Preserve PDF page numbers in retrieved evidence spans.
- Align source files to BibTeX keys by title overlap when filenames are paper titles.
- Retrieve citation-scoped evidence snippets.
- Split compound claims into context-preserving atoms for coverage checks.
- Apply deterministic fact lenses for numbers, years, hedging, scope gaps, and
  selected negation risks.
- Label claims as `supported`, `partially_supported`, `contradicted`,
  `unsupported`, or `uncertain`.
- Check LaTeX citation keys against BibTeX entries and required fields.
- Verify BibTeX entries against external scholarly metadata providers.
- Run an optional transformer NLI verifier for evidence-vs-claim judgments.
- Emit HALLMARK-compatible bibliography hallucination predictions.
- Export JSON and Markdown evidence ledgers.
- Run a small claim-support eval harness with false-supported rate.
- Expose an optional MCP server for agent clients.

This is not bound to one paper repository layout. Pass explicit paths for the
draft, bibliography, and source directory. CiteProof should work the same way
for a thesis folder, a LaTeX project, a Markdown draft, or a paper directory.

HALLMARK is useful for reference-hallucination checks, not for proving that a
specific cited sentence supports a paper claim. CiteProof keeps those two loops
separate: bibliography reality is checked through metadata providers, while
claim support is checked against local paper text.

## Quick Start

```bash
uv sync --extra dev
uv run citeproof verify examples/draft.md --sources examples/sources
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl
uv run citeproof verify-metadata --bib examples/hallucination/references.bib --limit 2
uv run pytest
```

Write reports:

```bash
uv run citeproof verify examples/draft.md \
  --sources examples/sources \
  --json-output reports/draft.json \
  --markdown-output reports/draft.md
```

Verify a LaTeX paper with BibTeX and a directory of PDFs:

```bash
uv run citeproof verify-paper path/to/paper.tex \
  --bib path/to/references.bib \
  --sources path/to/papers \
  --json-output reports/paper.json \
  --markdown-output reports/paper.md
```

When `--bib` is supplied, CiteProof only trusts source files that map to BibTeX
entries. This prevents arbitrary local files from satisfying made-up citation
keys. A fabricated BibTeX entry with a fabricated local PDF still needs the
external metadata-verification layer, such as CrossRef/OpenAlex/arXiv/Semantic
Scholar checks through `verify-metadata`.

Verify BibTeX entries against external metadata:

```bash
uv run citeproof verify-metadata --bib path/to/references.bib \
  --providers crossref,openalex,semanticscholar,arxiv \
  --json-output reports/metadata.json
```

Run the optional local transformers NLI verifier. By default this uses
`cross-encoder/nli-deberta-v3-small`, the same NLI model family used in
`token-uncertainty-verifier`; it does not call the Hugging Face Space API.

```bash
uv sync --extra nli
CITEPROOF_DEVICE=cpu \
uv run citeproof verify-paper path/to/paper.tex \
  --bib path/to/references.bib \
  --sources path/to/papers \
  --verifier nli
```

Override the local NLI model with `--nli-model` or `NLI_MODEL_ID`. Override
device selection with `CITEPROOF_DEVICE=cpu|cuda|mps`.

Generate HALLMARK prediction JSONL for bibliography hallucination scoring:

```bash
uv run citeproof hallmark-predict data/v1.0/dev_public.jsonl \
  --output reports/hallmark_predictions.jsonl
```

Check only bibliography integrity:

```bash
uv run citeproof verify-bib path/to/paper.tex --bib path/to/references.bib
```

Run the MCP server if the optional dependency is installed:

```bash
uv sync --extra mcp
uv run citeproof mcp
```

## Verification Model

CiteProof optimizes first for avoiding false `supported` labels. A claim is
only `supported` when citation metadata, source resolution, retrieval, fact
lenses, and optional NLI agree. When signals disagree, CiteProof keeps the claim
in the review queue as `partially_supported`, `uncertain`, or `unsupported`.

CiteProof treats contradiction as a first-class outcome. A contradiction is
returned when a source span contains overlapping content and a material conflict,
such as a numeric mismatch, a year conflict, or a negated result against a claim
that says a method improves, reduces, or outperforms.

The conservative ordering is:

1. Missing cited source -> `uncertain`
2. Retrieved contradiction -> `contradicted`
3. Atomic subclaim coverage -> `supported` only when all atoms are supported
4. Hedged, narrower, or incomplete evidence -> `partially_supported`
5. Source silence -> `unsupported`

Strict verification results include a trust trace when available. The trace
records source-gate status, atom-level labels, selected rationale spans, stable
failure modes, and a review action. This lets a writer or agent repair the
specific unsupported atom instead of guessing why a claim failed.

The most important product metric is false-supported rate: cases where the
system says `supported` while the expected label is anything else.

## Check Modes

CiteProof exposes checks as separate commands rather than one loose mode flag:

- Bibliography mode: `verify-bib` checks citation keys and required BibTeX fields.
- Metadata mode: `verify-metadata` checks BibTeX entries against external scholarly metadata.
- Source mode: `verify-paper --bib ... --sources ...` gates local PDFs/text files through the bibliography.
- Claim mode: `verify` checks citation-bearing claims against loaded sources.
- Strict mode: `verify-paper` combines bibliography, source, retrieval, fact-lens, and optional NLI checks.
- Benchmark mode: `eval` and `eval-draft` report `accuracy`, `macro_f1`, `false_supported_rate`, and per-case failures.
