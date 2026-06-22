---
name: citeproof-paper-verifier
description: Use CiteProof from a CLI or agent workflow to verify citation-bearing academic writing, especially LaTeX conference papers with BibTeX and local PDF/text sources. Trigger when writing, editing, reviewing, or repairing cited claims; checking whether a draft claim is supported, contradicted, unsupported, or uncertain; auditing a paper before submission; or helping an agent ground generated paper text in cited sources.
---

# CiteProof Paper Verifier

Use CiteProof as a conservative verification sidecar for academic papers. Keep the paper's source
of truth in the user's repo or writing workspace; use this skill to run checks, inspect evidence,
and repair claims without inventing sources.

## Workflow

1. Locate the paper inputs:
   - Main draft: usually `main.tex`, `paper.tex`, `draft.md`, or a user-specified file.
   - Bibliography: usually `references.bib`, `refs.bib`, or a user-specified file.
   - Sources: a folder of PDFs/text/Markdown/JSONL files, commonly `papers/`, `sources/`, or
     `literature/`.

2. Confirm the CiteProof command:
   - Prefer `citeproof` when installed.
   - Use the repo-local command, such as `uv run citeproof`, when working inside the CiteProof repo.
   - If neither works, stop and report that CiteProof is not installed instead of faking results.

3. Run the strict paper check when a LaTeX file and BibTeX file are available:

```bash
citeproof verify-paper main.tex \
  --bib references.bib \
  --sources papers \
  --json-output reports/citeproof.json \
  --markdown-output reports/citeproof.md \
  --html-output reports/citeproof.html
```

4. Run metadata verification when bibliography reality matters:

```bash
citeproof verify-metadata \
  --bib references.bib \
  --providers crossref,openalex,semanticscholar,arxiv \
  --json-output reports/citeproof-metadata.json
```

5. Run claim/draft checks when there is no BibTeX gate:

```bash
citeproof verify draft.md \
  --sources papers \
  --json-output reports/citeproof.json \
  --markdown-output reports/citeproof.md \
  --html-output reports/citeproof.html
```

6. For one risky sentence, use the targeted claim command:

```bash
citeproof verify-claim "Claim text with the citation-sensitive assertion." \
  --sources papers \
  --cite citationKey
```

## Interpreting Results

- Treat `supported` as acceptable only when the cited source, retrieved rationale, and fact checks agree.
- Treat `contradicted` as a blocking issue; revise the claim or citation before continuing.
- Treat `unsupported`, `uncertain`, and `partially_supported` as review-required. Do not present them as verified.
- Prefer narrowing or weakening a claim over forcing a citation to fit.
- Preserve the evidence report path in the final answer so the user can inspect snippets.
- Prefer the HTML dashboard when the user wants an interactive audit view.

## Writing And Repair Loop

When drafting or editing paper text:

1. Write citation-bearing claims in small, checkable sentences.
2. Run CiteProof on the changed draft or the specific high-risk claim.
3. Inspect the failure mode and evidence snippet.
4. Repair by doing one of:
   - Rewrite the claim to match the source.
   - Replace the citation with a source that actually supports the claim.
   - Add a missing source to the bibliography and source folder, then rerun metadata and paper checks.
   - Mark the claim for human review if the evidence is ambiguous.
5. Rerun CiteProof after edits and report the final verdicts.

## Conservative Rules

- Never invent BibTeX keys, papers, DOIs, sources, or evidence snippets.
- Never use an unrelated local file to satisfy a citation key.
- Do not treat HALLMARK-style bibliography checks as proof that a claim is supported.
- Do not claim the whole paper is verified if only one claim or one section was checked.
- If source retrieval is weak, say that the verification is inconclusive and ask for better sources.
