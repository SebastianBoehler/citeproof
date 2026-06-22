# CiteProof Evaluation

Primary metric: `false_supported_rate`.

The target for academic-integrity use is `false_supported_rate = 0.0`. Accuracy
and macro-F1 matter, but a false `supported` result is the highest-risk error.

## Local Benchmarks

Current local scores after the conservative hybrid verifier implementation:

| Benchmark | Total | Accuracy | Macro-F1 | False-Supported Rate |
| --- | ---: | ---: | ---: | ---: |
| `examples/claim_support.jsonl` | 4 | 1.0 | 0.8 | 0.0 |
| `examples/edge_cases/claim_support.jsonl` | 12 | 1.0 | 0.8 | 0.0 |
| `examples/edge_cases/claim_support.jsonl` with local NLI | 12 | 0.8333 | 0.5492 | 0.0 |
| `examples/hallucination` draft eval | 5 | 1.0 | 0.8 | 0.0 |

These benchmarks are intentionally small and adversarial. They cover basic
support, contradiction, partial support, source silence, numeric conflicts,
temporal conflicts, hedged evidence, entity swaps, compound claims, and
bibliography-gated hallucination checks.

The local NLI row uses `cross-encoder/nli-deberta-v3-small` from the Hugging
Face cache. It preserved the zero false-supported target on the edge set, but
over-called one partial case as `contradicted` and treated one source-silence
case as `uncertain`.

## Reading Scores

- `false_supported_rate`: share of non-supported expected cases predicted as
  `supported`. This should stay at `0.0`.
- `accuracy`: exact label match rate across all cases.
- `macro_f1`: balanced label quality across all labels, including labels absent
  from a small benchmark.
- Per-case reports include `id`, `expected_label`, `predicted_label`,
  `confidence`, `false_supported`, `pass`, and `reason`.

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
