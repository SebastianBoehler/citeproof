# Measurement Slot Conflicts Design

## Context

Fresh probes found high-overlap CS/ML citation failures that still produce
unsafe `supported` labels:

- metric scalar values: accuracy 0.92 vs 0.84, AUROC 0.91 vs 0.82
- generation metrics: BLEU score 31.2 vs 27.4
- compact model quantities: 7B parameters vs 13B parameters
- context length quantities: 32k tokens vs 128k tokens
- versioned benchmark names: MMLU-Pro vs MMLU

These are common paper-writing facts where the evidence can share almost every
word with the claim while the decisive measurement slot is wrong.

## Brainstormed Approaches

1. Typed deterministic measurement slots. Add a compact lens for metric scalar
   values and versioned benchmark anchors, and extend quantity parsing for B
   scale, parameters, and tokens. This is recommended because it is explainable
   and directly blocks current false-supported cases.
2. Demote high-overlap numeric fallback. Return `partially_supported` whenever
   unmatched decimals or versioned benchmark names appear. This is conservative
   but would increase manual review for many valid metric statements.
3. Use an extraction model to parse arbitrary metrics. This is broader, but it
   needs calibration data and should come after deterministic coverage for
   obvious structured cases.

## Selected Design

Implement deterministic measurement slots now.

Add `measurement_lens.py` with `inspect_measurement_conflicts(claim,
evidence)`. It should detect:

- same metric name with different bare scalar values
- same metric name with different score values
- versioned benchmark conflicts where one side names a hyphenated benchmark or
  both sides name incompatible variants

Extend `quantities.py` with:

- compact `B` scale for billions
- normalized units for `parameters`, `tokens`, and `contexts`

## Data Flow

1. Quantity parsing catches compact parameter/token conflicts through the
   existing numeric lens.
2. `inspect_facts` calls the new measurement lens with hard conflicts.
3. Metric scalar and benchmark-version conflicts return `contradicted`.
4. Scalar value conflicts route to `numeric_conflict`; benchmark-version
   conflicts route to `entity_conflict`.

## Conservative Rules

- Compare metric values only when the normalized metric name matches.
- Require non-slot context overlap before flagging a metric-value conflict.
- Treat benchmark base-only vs benchmark-variant as a conflict only when the
  surrounding evaluation/use context overlaps.
- Do not add model calls, fallback thresholds, or broad unknown metric parsing.

## Testing

Add focused tests for the five unsafe probes and matching controls. Add edge
rows for metric scalar, BLEU score, parameter count, token count, and benchmark
version conflicts.

## Success Check

The slice is complete when focused tests pass, expanded edge eval and
eval-suite remain saturated, full pytest and ruff pass, touched files stay
below 300 lines, and the commits are pushed with CI green.
