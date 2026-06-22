# Conflict-Aware Rationale Ranking Design

## Context

The current verifier catches contradictions well once a relevant evidence span is
judged, but an end-to-end draft can still fail if rationale selection ranks a
contradicting span below several high-overlap distractors.

A synthetic probe exposed this false-supported path:

- claim: `Method X improves calibration over PPO.`
- source: many paragraphs say `Method X improves accuracy over PPO`, followed
  by `Calibration remains unchanged ... no difference from PPO.`
- current result: `supported`
- trace: five selected rationale windows, all support-like distractors;
  `contradiction_candidate_count = 0`

The contradicting chunk is retrieved, so the miss is not chunk-level retrieval.
It is sentence-window ranking: lexical overlap favors distractors with `Method X`
and `improves`, while the actual contradiction is more outcome-specific and uses
`unchanged` / `no difference`.

## Chosen Approach

Add conflict-aware reranking inside `rationales.select_rationales`.

For every sentence window, keep the existing lexical score. If the window also
contains high-risk contradiction cues and has enough claim overlap to be
relevant, assign a deterministic rerank bonus. Sort by rerank score, while
preserving the original lexical score in the public evidence score.

Initial conflict cues:

- `unchanged`
- `no change`
- `no difference`
- `no improvement`
- `no reduction`
- `does not improve`
- `did not improve`
- `failed to improve`
- `not statistically significant`
- `comparable to`
- `equivalent to`
- `worse than`

The bonus only applies when the window already clears the existing minimum
lexical score. This prevents unrelated negated sentences from entering the
candidate set solely because they contain a risk cue.

## Data Flow

`verify_claim` retrieves chunks, then `_verify_atoms` calls
`select_rationales`. The updated selector computes:

1. lexical score for the claim/window pair;
2. rerank score as lexical score plus conflict bonus;
3. selected candidates sorted by rerank score;
4. `EvidenceCandidate.lexical_score` remains the original lexical value;
5. `EvidenceCandidate.rerank_score` records the score used for ranking.

The adjudicator then sees the contradiction candidate and the existing
contradiction-first combination rule blocks false support.

## Alternatives Considered

Increase `RATIONALE_CANDIDATE_LIMIT`:
This would reduce misses but adds more noise and does not prioritize risky
evidence. It also makes traces less focused.

Change chunk retrieval:
The probe showed the contradicting chunk was already retrieved. Chunk retrieval
is not the narrow cause for this failure.

Add dense retrieval:
Potentially useful later, but this deterministic miss has a cheaper and more
auditable fix.

## Tests

Add tests that:

- prove a conflict-cue window is selected ahead of high-overlap distractors;
- prove the full verifier changes the synthetic calibration case from
  `supported` to `contradicted`;
- preserve existing direct and draft eval scores.

The expected behavior is not to make every negated sentence a contradiction.
The window must still overlap the claim enough to pass the existing candidate
threshold and then the adjudicator must judge the relation.

## Out of Scope

This slice does not add semantic search, embeddings, external rerankers, or a
new retrieval benchmark file. It fixes a verified deterministic ranking blind
spot and exposes the rerank score already supported by `EvidenceCandidate`.
