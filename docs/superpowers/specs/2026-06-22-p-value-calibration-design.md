# P-Value Calibration Design

## Goal

Prevent false `supported` labels when a draft claim states a p-value relation or
statistical significance but the cited evidence reports an incompatible p-value.
This is a high-risk academic-integrity case because the text often has strong
lexical overlap while the statistical conclusion changes.

## Current Behavior

Probes on the current verifier show:

- `The model improvement has p < 0.05.` versus
  `The model improvement has p = 0.08.` is labeled `supported`.
- `The model improvement is statistically significant.` versus
  `The model improvement has p = 0.08.` is not identified as a contradiction.
- `The model improvement is not statistically significant.` versus
  `The model improvement has p = 0.01.` is not identified as a contradiction.

## Approach

Extend `statistical_lens` with a deterministic p-value parser. The parser should
recognize local forms such as `p < 0.05`, `p = 0.08`, `p-value was 0.08`, and
`p-value greater than 0.05`. It should compare claim-side and evidence-side
relations using exact values when present.

The lens should also bridge common significance wording:

- `statistically significant` implies p-value below `0.05` unless the claim
  gives a different explicit p-value threshold.
- `not statistically significant` implies p-value at or above `0.05` unless the
  claim gives a different explicit threshold.

Conflicts remain hard contradictions because a p-value relation can directly
invalidate the cited statistical conclusion. Failure mode should map to
`numeric_conflict`.

## Boundaries

This is not a full statistical inference engine. It should not infer adjusted
significance thresholds, multiple-comparison correction outcomes, Bayesian
evidence, confidence intervals, or effect sizes beyond explicit p-value
relations and the conventional 0.05 wording bridge.

## Tests

Add lens and adjudicator tests for:

- explicit p-value threshold conflict
- significant wording contradicted by p-value above 0.05
- not-significant wording contradicted by p-value below 0.05
- matching p-value relation ignored as non-conflict

Add edge benchmark rows so `eval-suite` guards the new false-supported class.
