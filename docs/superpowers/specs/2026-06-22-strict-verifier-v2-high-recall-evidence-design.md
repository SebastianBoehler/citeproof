# Strict Verifier v2: High-Recall Evidence Design

## Purpose

CiteProof should keep moving toward a verifier that an academic writer or agent
can trust while drafting. The current strict verifier is traceable and
conservative, but it still depends on a small lexical evidence set and a compact
hand-built benchmark. The next slice should improve the verifier's chance of
finding both support and contradiction before a claim can receive `supported`.

The target is not a perfect oracle. The target is a stricter verifier contract:
`supported` means the cited source was resolved, enough candidate evidence was
searched, each atomic claim has supporting rationale, contradiction candidates
were adjudicated, and no enabled verifier signal disagreed.

This phase deliberately stays inside the local/offline verifier. SaaS, editor
UI, web search, repair generation, and heavy learned rerankers can build on the
same contract later.

## Current State

Merged `main` already includes:

- citation-scoped source gating
- atom-level verification traces
- sentence/window rationale selection
- deterministic fact lenses for numbers, years, units, hedging, scope, and
  selected negation or metric conflicts
- optional local NLI
- multi-candidate rationale adjudication with contradiction priority
- stable failure modes and review actions
- fast direct and draft eval commands
- local benchmark scores of `accuracy = 1.0` and `false_supported_rate = 0.0`
  on the committed small benchmarks

The current strengths are traceability and conservative label policy. The main
remaining weakness is evidence search breadth. If the right support or
contradiction is outside the top lexical candidates, the verifier may abstain or
miss the best diagnostic. The local benchmark is also too small to justify high
confidence for academic-integrity use.

## Design Principles

- `supported` remains a high-precision label.
- Contradiction search must have a fair chance before `supported` is possible.
- Retrieval should optimize recall first, then ranking.
- Every evidence candidate used for a final decision should be visible in the
  trace with retrieval method, score, rank, and relation.
- Optional ML judges can veto or downgrade. They cannot bypass citation gates,
  rationale coverage, or deterministic conflict checks.
- Evaluation must measure retrieval and rationale behavior, not only final label
  accuracy.
- New dependencies should be optional until deterministic and benchmark
  scaffolding is stronger.

## Recommended Scope

This design covers one implementation slice:

1. High-recall candidate collection.
2. Contradiction-safe multi-span adjudication.
3. Retrieval/rationale metrics in eval details.
4. Expanded adversarial benchmarks.
5. Documentation of strict support invariants.

It does not add dense embeddings, ColBERT-style retrieval, MiniCheck, AlignScore,
or another learned model yet. Those are intentionally left as a follow-up once
the candidate/metrics interfaces are ready.

## Evidence Discovery

The verifier should separate candidate collection from final adjudication.

`retrieve_evidence` currently returns a small lexical top-k list of chunks. In
v2, the verifier should construct an `EvidencePool` per claim or atom:

- citation-scoped retrieved chunks
- sentence/window rationale candidates from those chunks
- candidate scores and ranks
- candidate relation after adjudication
- coverage flags for support, contradiction, neutral, and silence

The initial implementation can stay lexical but should increase breadth in two
places:

- retrieve more citation-scoped chunks than the final evidence display needs
- select more sentence windows per atom than the final top support span

The trace should keep enough candidates to audit the decision, while Markdown
output can stay compact.

## Candidate Collection Policy

For each atom:

1. Retrieve a broad chunk set from cited sources.
2. Generate sentence windows from each retrieved chunk.
3. Score candidates lexically.
4. Keep the top candidates by lexical score.
5. Also preserve candidates with obvious deterministic conflict signals, even if
   lexical score is lower than the support-like candidate.
6. Adjudicate every kept candidate independently.

The first version can expose simple knobs as constants rather than user-facing
configuration:

- chunk candidate limit: 8
- rationale candidate limit: 5
- minimum rationale lexical score: 0.08
- deterministic conflict candidates bypass the rationale score floor only when
  they still share core claim terms

These values should be validated by benchmarks before becoming CLI options.

## Contradiction-Safe Adjudication

Final atom label aggregation should follow this order:

1. Any strong contradiction in cited evidence -> `contradicted`.
2. One or more support spans and no contradiction -> candidate support.
3. Support for some atoms but missing support for others -> `partially_supported`.
4. Evidence retrieved but silent on the atom -> `unsupported` with
   `source_silence`.
5. No usable rationale span -> `unsupported` or `uncertain` with
   `no_rationale_span` depending on source/retrieval state.

For a parent claim to become `supported`:

- every atom must be supported,
- every atom must have at least one supporting rationale,
- no atom can have a contradiction candidate,
- no source or citation gate can fail,
- no enabled NLI/alignment judge can disagree.

If a support span and contradiction span both exist, contradiction wins. If
signals are inconsistent but not cleanly contradictory, the result should become
`uncertain` or `partially_supported`, never `supported`.

## Trace Additions

The existing trace model can stay stable, but candidate diagnostics need to be
more useful.

`EvidenceCandidate` should continue to carry:

- source id
- citation key
- chunk id
- page/title
- text
- lexical score
- optional semantic and rerank scores
- rank
- retrieval method

The verifier should additionally make it easy to inspect:

- total candidates considered per atom
- count of candidates by relation
- best support rank
- best contradiction rank
- whether `supported` was blocked by contradiction, missing support, or model
  disagreement

This can be represented either by new trace fields or by deriving the metrics
from `AtomVerification.rationales` and candidate ranks. The first implementation
should prefer deriving where possible to avoid growing the model too quickly.

## Metrics

Add metrics that directly measure trust-relevant behavior:

- `rationale_candidate_count`: candidates judged for a case or atom
- `support_rationale_count`: support candidates judged
- `contradiction_rationale_count`: contradiction candidates judged
- `best_support_rank`: rank of the best supporting rationale, if any
- `best_contradiction_rank`: rank of the best contradiction rationale, if any
- `rationale_hit_rate`: share of expected supported cases with at least one
  support rationale
- `contradiction_recall_at_k`: share of contradicted cases where a contradiction
  appeared in judged candidates
- `blocked_supported_count`: cases where a support candidate existed but a
  contradiction or missing atom blocked final `supported`

The existing summary metrics stay primary:

- `false_supported_rate`
- `supported_precision`
- `supported_recall`
- `unsupported_recall`
- `contradiction_recall`
- `manual_review_rate`

The new metrics should be optional in JSON details first. They do not need to
change every public summary format in the first implementation.

## Benchmark Expansion

The committed fast benchmark should grow with adversarial cases that target
evidence discovery, not only label classification.

Add cases for:

- supporting and contradictory spans in the same cited source
- contradiction ranked below support by lexical score
- paraphrase support with low lexical overlap
- support in neighboring paragraph or sentence window
- silent cited source with topically related terms
- uncited source support that must not satisfy the citation
- same-number different-unit conflict
- overlapping unit mention that should not be contradicted
- year and publication-version conflict
- metric swap and cross-metric negation
- entity/model/dataset swap
- scope overstatement from narrow evidence
- compound claim with one unsupported atom

For direct JSONL evals, add optional expected diagnostics:

- `expected_failure_mode`
- `expected_relation_counts`
- `expected_contains_rationale`

The eval runner should treat these as additional assertions when present.

## Optional ML Follow-Up

Once the high-recall evidence layer is measured, add optional learned judges:

- local NLI remains available as a semantic gate,
- MiniCheck-style or AlignScore-style grounding judge can be added as a
  source-claim alignment signal,
- dense retrieval or reranking can be introduced behind optional extras.

The first learned-model role should be conservative:

- downgrade `supported` on disagreement,
- flag `model_disagreement`,
- provide confidence calibration data,
- never mark a claim `supported` when deterministic/source gates fail.

## Evaluation Commands

The implementation plan should preserve these checks:

```bash
uv run pytest -q
uv run citeproof eval examples/claim_support.jsonl
uv run citeproof eval examples/edge_cases/claim_support.jsonl \
  --details-output reports/edge_cases_heuristic.json
uv run citeproof eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output reports/hallucination_bib_gated_details.json
```

Expected local target after this slice:

- `false_supported_rate = 0.0` on committed benchmarks
- contradiction cases with lower-ranked contradiction candidates still resolve
  as `contradicted`
- support cases with only silent evidence do not become `supported`
- all new diagnostic assertions pass

## Risks

- More candidate adjudication can reduce recall for `supported` by finding
  noisy contradiction-like spans. That is acceptable only if trace output makes
  the reason clear.
- Larger candidate pools can make output noisy. Keep JSON complete and Markdown
  compact.
- Hand-built adversarial tests can overfit. Treat them as regression tests, not
  evidence of general accuracy.
- Dense retrieval and learned rerankers can improve recall but introduce
  dependency and calibration complexity. Keep them out of this slice.

## References

- SciFact: https://aclanthology.org/2020.emnlp-main.609/
- FActScore: https://aclanthology.org/2023.emnlp-main.741/
- AlignScore: https://aclanthology.org/2023.acl-long.634/
- MiniCheck: https://aclanthology.org/2024.emnlp-main.499/
