# CiteProof Evaluation

Primary metric: `false_supported_rate`.

The target for academic-integrity use is `false_supported_rate = 0.0`. Accuracy
and macro-F1 matter, but a false `supported` result is the highest-risk error.

## Local Benchmarks

Current local scores after the strict offline verifier updates:

| Benchmark | Total | Accuracy | Macro-F1 | False-Supported Rate |
| --- | ---: | ---: | ---: | ---: |
| `examples/claim_support.jsonl` | 4 | 1.0 | 0.8 | 0.0 |
| `examples/edge_cases/claim_support.jsonl` | 15 | 1.0 | 0.8 | 0.0 |
| `examples/hallucination` draft eval | 5 | 1.0 | 0.8 | 0.0 |

These benchmarks are intentionally small and adversarial. They cover basic
support, contradiction, partial support, source silence, numeric conflicts,
temporal conflicts, hedged evidence, entity swaps, compound claims,
failure-mode classification, and bibliography-gated hallucination checks.

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
- Direct `eval` per-case reports include `id`, `expected_label`, `predicted_label`,
  `confidence`, `false_supported`, `pass`, `reason`, and `failure_mode` when
  the verifier can assign a stable failure category.

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
