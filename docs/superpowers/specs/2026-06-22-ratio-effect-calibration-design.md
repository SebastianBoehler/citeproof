# Ratio Effect Calibration Design

## Goal

Catch false support in claims about ratio effect measures such as hazard ratios,
odds ratios, risk ratios, and relative risk. These measures use `1` as the null
value, not `0`, so the existing confidence-interval calibration is insufficient.

## Current Behavior

Current probes show:

- `The treatment hazard ratio is below 1.` versus
  `The treatment hazard ratio was 1.20.` is labeled `supported`.
- `The treatment significantly reduces mortality.` versus
  `The treatment mortality hazard ratio was 0.82 with 95% CI [0.60, 1.12].`
  is only partial support, even though the CI crosses the ratio null.
- `The odds ratio excludes the null value.` versus
  `The odds ratio was 0.82 with 95% CI [0.60, 1.12].` is not contradicted.

## Approach

Add a focused `ratio_effect_lens.py` and call it from `statistical_lens.py`.
The new lens should parse only explicit ratio metrics:

- hazard ratio
- odds ratio
- risk ratio
- relative risk

It should detect two categories:

1. Point-estimate direction conflicts:
   - claim says ratio is below/less than 1 but evidence ratio is greater than 1
   - claim says ratio is above/greater than 1 but evidence ratio is below 1
2. Ratio confidence interval null conflicts:
   - claim says the ratio CI excludes the null value but evidence CI includes 1
   - claim says the ratio CI includes the null value but evidence CI excludes 1
   - significant wording conflicts with a ratio CI crossing 1
   - not-significant wording conflicts with a ratio CI excluding 1

## Boundaries

This is not a generic clinical-inference engine. It should not infer treatment
benefit from every outcome word. It should act only when a ratio metric is
explicitly present near a point estimate or CI. Directional treatment claims such
as `reduces mortality` may be handled in a future slice after more careful
outcome-specific design.

## Failure Mode

Use `numeric_conflict` for ratio point-estimate and ratio CI conflicts because
the contradiction is caused by a numeric relation against the ratio null.

## Tests

Add tests for:

- `hazard ratio below 1` contradicted by `hazard ratio was 1.20`
- `hazard ratio above 1` contradicted by `hazard ratio was 0.80`
- `odds ratio excludes the null value` contradicted by CI `[0.60, 1.12]`
- `risk ratio includes the null value` contradicted by CI `[0.70, 0.96]`
- `significantly` contradicted by a ratio CI crossing 1
- matching ratio relation ignored as non-conflict

Add edge benchmark rows so `eval-suite` protects the new false-supported class.
