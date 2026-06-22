# CiteProof

CiteProof verifies whether citation-bearing claims are supported by their cited
sources. The first scaffold is intentionally small: it separates parsing,
retrieval, entailment/contradiction labels, reporting, and evaluation so we can
measure changes before building editor or SaaS surfaces.

## Current Scope

- Parse Markdown/LaTeX-style citation claims.
- Load local text sources from a directory.
- Retrieve citation-scoped evidence snippets.
- Label claims as `supported`, `partially_supported`, `contradicted`,
  `unsupported`, or `uncertain`.
- Export JSON and Markdown evidence ledgers.
- Run a small claim-support eval harness with false-supported rate.
- Expose an optional MCP server for agent clients.

This is not yet a full academic verifier. It does not parse PDFs, call external
metadata APIs, or run a trained NLI model. Those are next layers after the first
testable loop is in place.

## Quick Start

```bash
uv sync --extra dev
uv run citeproof verify examples/draft.md --sources examples/sources
uv run citeproof eval examples/claim_support.jsonl
uv run pytest
```

Write reports:

```bash
uv run citeproof verify examples/draft.md \
  --sources examples/sources \
  --json-output reports/draft.json \
  --markdown-output reports/draft.md
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
