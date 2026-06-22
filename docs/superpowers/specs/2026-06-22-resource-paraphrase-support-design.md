# Resource Paraphrase Support Design

## Goal

Recover clear academic resource-efficiency paraphrases without weakening the
false-supported guard. The verifier should recognize narrow cases where a
claim says a method reduces training time or improves sample efficiency and the
evidence states the equivalent resource reduction with different wording.

## Current Gap

`judge_evidence()` already supports one training-time paraphrase:
`required half as many hours`. It misses nearby wording such as `required fewer
training hours`, returning `partially_supported` even when the evidence directly
supports the claim. It also does not treat sample-efficiency claims as supported
when the source says the method reaches the target with fewer environment
interactions.

## Approach

Add a deterministic resource paraphrase lens inside `entailment.py`, reusing the
existing `_has_semantic_support()` path. This keeps retrieval, source gating,
fact lenses, NLI, and adjudication unchanged. The lens only upgrades to
`supported` when all of these hold:

- the existing token overlap gate has passed;
- the claim is an affirmative resource-efficiency claim;
- the evidence contains an affirmative resource-reduction phrase;
- the evidence does not contain a local negation such as `does not require fewer`
  or `no reduction in`.

## Supported Patterns

Training time:

- claim mentions `training` and `time`;
- claim uses a reduction verb such as `reduce`, `reduces`, `reduced`, or
  `lower`;
- evidence mentions `hours`, `time`, or `wall-clock`;
- evidence says `fewer`, `less`, `reduced`, or `half as many` near that time
  unit.

Sample efficiency:

- claim mentions `sample efficiency` or says the method improves efficiency;
- evidence mentions `samples`, `examples`, `environment interactions`, or
  `interactions`;
- evidence says `fewer`, `less`, or `reduced` near that sample-interaction
  term.

## Non-Goals

- Do not add embeddings, external models, or configurable synonym maps in this
  slice.
- Do not change retrieval ranking or candidate limits.
- Do not upgrade broad resource claims such as `uses fewer resources` without a
  specific time or sample-efficiency dimension.
- Do not treat negated reductions as support.

## Tests And Evaluation

Add direct entailment tests for:

- `reduces training time` supported by `required fewer training hours`;
- `improves sample efficiency` supported by `fewer environment interactions`;
- negated fewer-sample evidence not returning `supported`.

Add two edge benchmark rows so local metrics prove the behavior:

- `training-time-fewer-hours-support`;
- `sample-efficiency-fewer-interactions-support`.

The expected edge-case total becomes 24. The target remains
`false_supported_rate = 0.0`.
