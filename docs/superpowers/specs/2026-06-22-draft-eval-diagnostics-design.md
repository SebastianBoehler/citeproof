# Draft Eval Diagnostics Design

## Context

Direct claim-support evals now run through `eval-suite`, but the paper-writing
workflow depends on more than direct entailment. A real draft has to be parsed,
citation keys must resolve to source chunks, retrieval must surface the right
rationale, and then the verifier can judge support or contradiction.

`eval-draft` already exercises that end-to-end path, but its details currently
only report claim match, expected label, predicted label, pass status, and
reason. That is too thin for academic-integrity debugging: a failed or risky
case should show whether the problem was source resolution, no rationale span,
weak retrieval, missing atom support, model disagreement, or a contradiction
ranked below another candidate.

## Chosen Approach

Strengthen `eval-draft` rather than creating a separate retrieval benchmark.
The existing expected JSONL format remains compatible, with optional
`expected_failure_mode` added for rows that need stable diagnostics.

Each `eval-draft --details-output` case should include:

- `false_supported`;
- `failure_mode`;
- optional `expected_failure_mode` and `failure_mode_pass`;
- `confidence`;
- `source_gate_status`;
- `candidate_count`;
- `support_candidate_count`;
- `contradiction_candidate_count`;
- `best_support_rank`;
- `best_contradiction_rank`.

The CLI should also accept the same `--verifier heuristic|nli` and
`--nli-model` arguments already used by direct `eval`, `verify`, and
`verify-paper`, so the full draft workflow can be evaluated with optional local
NLI.

## Data Flow

`citeproof eval-draft` builds the judge with `_make_judge(args)` and passes it
into `run_draft_eval`. `run_draft_eval` forwards that judge into
`verify_draft` or `verify_claim` for BibTeX-aligned sources. For each expected
case, it finds the verified claim, computes the label pass and optional failure
mode pass, then extracts aggregate atom diagnostics from the result trace.

## Alternatives Considered

Separate retrieval-eval command:
Useful later if we need specialized retrieval-label datasets, but it would
duplicate current draft parsing and source-gating behavior.

Change retrieval now:
The trace from the example draft already shows retrieval candidate data. The
responsible next step is to measure retrieval behavior clearly before changing
ranking.

Only document how to inspect traces:
Too manual. Benchmark outputs should include the diagnostics needed to compare
changes and gate future regressions.

## Testing

Add tests that:

- preserve current `eval-draft` label behavior;
- include `false_supported` and failure mode diagnostics in rows;
- assert `expected_failure_mode` changes `pass` when mismatched;
- verify a custom judge can be passed through `run_draft_eval`;
- verify CLI `eval-draft --verifier nli` is accepted by parser-level tests
  without loading a real model.

## Out of Scope

This slice does not change retrieval ranking, add semantic search, or require
the optional NLI dependency in default CI. It makes the draft evaluation path
diagnostic enough to support those changes safely.
