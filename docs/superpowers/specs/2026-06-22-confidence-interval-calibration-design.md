# Confidence Interval Calibration Design

## Goal

Catch citation errors where a draft claim says a confidence interval includes
or excludes zero, or implies statistical significance, but the cited evidence
gives a numeric interval with the opposite relation. This reduces subtle false
support in statistical claims.

## Current Behavior

Current probes show numeric intervals are not interpreted:

- `The confidence interval excludes zero.` versus
  `The 95% confidence interval was [-0.10, 0.30].` returns partial support.
- `The treatment effect is statistically significant.` versus
  `The 95% confidence interval was [-0.10, 0.30].` returns source silence.
- Existing coverage only handles literal wording such as `includes zero` versus
  `excludes zero`.

## Approach

Keep `statistical_lens.py` as the coordinator, but split specialized parsers
into focused modules:

- `pvalue_lens.py` owns p-value relation parsing moved from
  `statistical_lens.py`.
- `confidence_interval_lens.py` owns numeric confidence interval parsing and
  include/exclude-zero conflict checks.

The CI parser should recognize compact bracket/parenthesis intervals near
confidence-interval language, such as `95% confidence interval was [-0.10,
0.30]` or `CI: (0.10, 0.30)`. It should infer:

- includes zero when lower <= 0 <= upper
- excludes zero when both bounds are positive or both bounds are negative

The confidence-interval lens should compare numeric evidence against:

- explicit claim wording: `includes zero`, `excludes zero`
- significance wording: `statistically significant` maps to excludes zero,
  `not statistically significant` maps to includes zero

## Boundaries

This is not a full interval parser. It should only handle two numeric bounds
inside brackets or parentheses near CI/confidence-interval wording. It should
avoid inferring from arbitrary numeric ranges that are not described as
confidence intervals.

## Tests

Add tests for:

- claim says excludes zero, evidence numeric CI includes zero
- claim says includes zero, evidence numeric CI excludes zero
- significant wording contradicted by CI including zero
- not-significant wording contradicted by CI excluding zero
- matching numeric CI relation ignored as non-conflict

Add edge benchmark rows for numeric CI contradictions and keep
`false_supported_rate = 0.0`.
