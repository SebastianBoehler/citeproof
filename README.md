# CiteProof

CiteProof verifies whether citation-bearing claims are supported by their cited
sources. The first scaffold is intentionally small: it separates parsing,
retrieval, entailment/contradiction labels, reporting, and evaluation so we can
measure changes before building editor or SaaS surfaces.

## Current Scope

- Parse Markdown/LaTeX-style citation claims.
- Load local PDF, text, Markdown, or JSONL sources from any directory.
- Align source files to BibTeX keys by title overlap when filenames are paper titles.
- Retrieve citation-scoped evidence snippets.
- Label claims as `supported`, `partially_supported`, `contradicted`,
  `unsupported`, or `uncertain`.
- Check LaTeX citation keys against BibTeX entries and required fields.
- Export JSON and Markdown evidence ledgers.
- Run a small claim-support eval harness with false-supported rate.
- Expose an optional MCP server for agent clients.

This is not bound to one paper repository layout. Pass explicit paths for the
draft, bibliography, and source directory. CiteProof should work the same way
for a thesis folder, a LaTeX project, a Markdown draft, or a paper directory.

This is not yet a full academic verifier. It does not call external metadata
APIs or run a trained NLI model. Those are next layers after the first testable
loop is in place.

## Quick Start

```bash
uv sync --extra dev
uv run citeproof verify examples/draft.md --sources examples/sources
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl
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
next metadata-verification layer, such as CrossRef/OpenAlex/arXiv/Semantic
Scholar checks.

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

CiteProof treats contradiction as a first-class outcome. A contradiction is only
returned when a source span contains overlapping content and a material conflict,
such as a numeric mismatch or a phrase like "no statistically significant
improvement" against a claim that says a method "improves" or "outperforms".

The conservative ordering is:

1. Missing cited source -> `uncertain`
2. Retrieved contradiction -> `contradicted`
3. Strong source overlap -> `supported`
4. Moderate source overlap -> `partially_supported`
5. Source silence -> `unsupported`

The most important product metric is false-supported rate: cases where the
system says `supported` while the expected label is anything else.
