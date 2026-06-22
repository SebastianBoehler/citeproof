# Eval Suite Gates Design

## Context

CiteProof now passes the committed primary, edge, and hallucination evals with
`false_supported_rate = 0.0`. That is useful, but the current commands encourage
checking one dataset at a time and then manually comparing results. For academic
integrity, the scoring surface needs to make a sharper distinction between:

- curated smoke cases;
- adversarial regression cases;
- future private held-out cases built from real papers or thesis sources;
- optional NLI/audit-mode runs.

The next reliability improvement is a suite-level benchmark runner that can
evaluate multiple JSONL datasets, preserve per-dataset metrics, compute an
aggregate score, and fail explicitly when gates are violated.

## Chosen Approach

Add an `eval-suite` command backed by a small manifest file. The manifest lists
datasets and optional gates:

```json
{
  "datasets": [
    {"name": "primary", "path": "examples/claim_support.jsonl", "split": "curated"},
    {"name": "edge", "path": "examples/edge_cases/claim_support.jsonl", "split": "adversarial"}
  ],
  "gates": {
    "max_false_supported_rate": 0.0,
    "min_accuracy": 1.0
  }
}
```

The command prints a JSON report containing:

- one summary per dataset;
- aggregate metrics across all direct claim-support rows;
- gate results with pass/fail status;
- dataset metadata such as `name`, `path`, `split`, and `total`.

The implementation reuses the existing direct JSONL eval format and
`run_eval_cases`, so no existing benchmark file needs to change.

## Alternatives Considered

Only document manual commands:
This keeps the code smaller but does not improve benchmark discipline. It also
does not help CI or future private evaluation.

Automatic adversarial PDF generation:
This is likely valuable later, but generated labels can be noisy. A gateable
suite runner should exist first so generated and human-labeled cases can be
measured consistently.

Separate held-out file format:
This would add unnecessary friction. Current JSONL rows already contain claim,
evidence, expected label, optional failure mode, and optional case IDs.

## Data Flow

`citeproof eval-suite <manifest>` reads the manifest, resolves dataset paths
relative to the manifest location, runs each dataset through `run_eval_cases`,
summarizes per dataset, then summarizes all rows together. If any gate fails,
the command exits with code `2`; otherwise it exits `0`.

## Gates

Supported gates for this slice:

- `max_false_supported_rate`
- `min_accuracy`
- `max_manual_review_rate`
- `min_supported_precision`
- `min_contradiction_recall`
- `min_unsupported_recall`

All gates apply to the aggregate direct-claim-support metrics. Per-dataset
gates can be added later if the held-out benchmark needs different thresholds.

## Tests and Verification

Add unit tests for:

- manifest path resolution relative to the manifest file;
- passing gates;
- failing gates;
- report shape for per-dataset and aggregate summaries;
- CLI exit code `2` when a gate fails.

Add `examples/eval_suite.json` that includes the primary and edge datasets with
strict gates. Update docs and CI to run the suite in addition to existing evals.

Required local verification:

- `uv run pytest -q -p no:cacheprovider`;
- `uv run citeproof eval-suite examples/eval_suite.json`;
- existing primary, edge, and hallucination evals;
- `uv run ruff check --no-cache .`.

## Out of Scope

This slice does not generate benchmark labels, ingest private PDFs, or claim
general 100% accuracy. It creates the scoring and gate infrastructure required
to evaluate those datasets honestly.
