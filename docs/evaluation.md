# CiteProof Evaluation

Primary metric: `false_supported_rate`.

The target for academic-integrity use is `false_supported_rate = 0.0`. Accuracy
and macro-F1 matter, but a false `supported` result is the highest-risk error.

## Local Benchmarks

Current local scores after the strict verifier v2 high-recall evidence updates:

| Benchmark | Total | Accuracy | Macro-F1 | False-Supported Rate |
| --- | ---: | ---: | ---: | ---: |
| `examples/claim_support.jsonl` | 4 | 1.0 | 0.8 | 0.0 |
| `examples/edge_cases/claim_support.jsonl` | 136 | 1.0 | 0.8 | 0.0 |
| `examples/hallucination` draft eval | 5 | 1.0 | 0.8 | 0.0 |

These benchmarks are intentionally small and adversarial. They cover basic
support, contradiction, partial support, source silence, numeric conflicts,
temporal conflicts, material anchor swaps, comparison-direction swaps,
comparison wording variants, compact quantity conflicts, resource-efficiency paraphrases, hedged
evidence, explicit negation conflicts, directional change conflicts, numeric bound conflicts,
qualitative scope conflicts, significance negations, requirement negations, descriptor swaps,
controlled attribute conflicts, method-design attribute conflicts, entity swaps,
technical property conflicts, statistical reporting conflicts, claim-strength overstatements,
causal-design support calibration, p-value/significance conflicts, numeric confidence intervals,
ratio-effect null conflicts,
academic count conflicts,
protocol-slot conflicts,
contrastive exclusions, metric-slot conflicts,
clinical effect slots, trainable-scope conflicts,
assertion-status tensions, role/provenance binding conflicts, tie-comparison tensions,
context-limitation tensions, component-exclusion conflicts,
outcome-status conflicts, mixed-effect tensions, protocol/measurement-slot conflicts,
compound claims, failure-mode classification, and bibliography-gated
hallucination checks. Passing these suites means the current
curated cases are saturated; it does not establish general 100% citation-verification accuracy on
unseen papers.

## Suite Gates

Use `eval-suite` when comparing multiple benchmark files or running private
held-out cases:

```bash
uv run citeproof eval-suite examples/eval_suite.json
```

The suite manifest resolves dataset paths relative to the manifest file. The
committed suite gates aggregate direct claim-support metrics across the primary
and edge datasets and currently require `false_supported_rate = 0.0`.
Private real-paper suites should use the same JSONL row format and a separate
manifest that is not committed when source text cannot be redistributed.

## Reading Scores

- `false_supported_rate`: share of all eval cases where a non-supported expected
  case was predicted as `supported`. This should stay at `0.0`.
- `accuracy`: exact label match rate across all cases.
- `macro_f1`: balanced label quality across all labels, including labels absent
  from a small benchmark.
- `supported_precision`: share of `supported` predictions that were actually supported.
- `supported_recall`: share of supported expected cases recovered as `supported`.
- `unsupported_recall`: share of unsupported expected cases correctly rejected.
- `contradiction_recall`: share of contradicted expected cases caught as `contradicted`.
- `manual_review_rate`: share of predictions returned as `partially_supported` or `uncertain`.
- `candidate_count`: number of rationale candidates judged for an atom.
- `support_candidate_count`: judged candidates labeled as support.
- `contradiction_candidate_count`: judged candidates labeled as contradiction.
- `best_support_rank`: retrieval rank of the best supporting rationale, when present.
- `best_contradiction_rank`: retrieval rank of the best contradictory rationale, when present.
- `failure_mode_pass`: direct eval check that the predicted failure mode matches
  `expected_failure_mode` when a case declares one.
- Direct `eval` per-case reports include `id`, `expected_label`, `predicted_label`,
  `confidence`, `false_supported`, `pass`, `reason`, and `failure_mode` when
  the verifier can assign a stable failure category.
- Draft `eval-draft` details include retrieval trace diagnostics:
  `source_gate_status`, `candidate_count`, `support_candidate_count`,
  `contradiction_candidate_count`, `best_support_rank`, and
  `best_contradiction_rank`.

Run the current checks:

```bash
uv run pytest
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output reports/hallucination_bib_gated_details.json
```
