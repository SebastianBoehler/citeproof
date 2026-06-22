# Clinical Effect Slots Design

## Context

The current verifier still marks several high-overlap but wrong citations as
`supported`:

- exact effect value swaps: hazard ratio 0.72 vs 0.95
- adjustment status swaps: adjusted vs unadjusted odds ratio
- population swaps: adults vs children
- endpoint window swaps: 30-day vs 90-day mortality
- trial-design swaps: randomized vs single-arm
- trainable-scope swaps: all model weights vs frozen base plus adapter weights

These are academic-integrity failures because the source looks topically
relevant while changing a decisive factual slot.

## Brainstormed Approaches

1. Typed deterministic slot checks. Add a compact clinical/effect lens and
   extend the technical-property lens for trainable scope. This is recommended:
   findings are explainable, stable, and conservative.
2. Demote high-risk lexical fallback. Return `partially_supported` for
   high-overlap evidence containing terms such as adjusted, adult, single-arm,
   or hazard ratio unless a lens confirms the slot. This is safer than the
   current fallback but would need calibration to avoid unnecessary manual
   review.
3. Add NLI or extraction-model voting. This can cover more phrasing, but it
   introduces model variance and should be evaluated after deterministic slots
   handle obvious structured cases.

## Selected Design

Implement typed deterministic slots now.

Add `clinical_lens.py` with `inspect_clinical_conflicts(claim, evidence)`.
It should detect:

- exact ratio/effect-estimate value conflicts for the same metric and context
- adjusted vs unadjusted estimate conflicts
- adult vs child and human vs animal population conflicts
- endpoint time-window conflicts for hyphenated or spaced windows
- randomized/controlled vs single-arm trial design conflicts

Extend `technical_property_lens.py` with trainable-scope values:

- all model weights or all parameters
- adapter/low-rank adapter weights
- frozen base/pretrained/model weights

## Data Flow

1. `inspect_facts` calls `inspect_clinical_conflicts` with the hard-conflict
   lenses.
2. Clinical conflicts return `contradicted`.
3. Exact numeric effect value and endpoint-window findings route to
   `numeric_conflict`.
4. Adjustment, population, and trial-design findings route to `entity_conflict`.
5. Trainable-scope findings use the existing technical-property conflict path.

## Conservative Rules

- Require overlapping non-slot context before flagging any slot conflict.
- Compare exact effect values only for the same ratio metric.
- Treat endpoint windows as conflicting only when the endpoint/outcome term
  overlaps.
- Do not infer clinical semantics outside controlled terms.
- Do not add a new model dependency or configurable fallback.

## Testing

Add focused tests for all six current false-supported probes and matching cases
that should remain clean. Add edge-eval rows for each probe so regression gates
cover the new behavior.

## Success Check

The slice is complete when focused tests pass, the expanded edge eval and
eval-suite remain saturated, full pytest and ruff pass, touched files stay below
300 lines, and the commits are pushed with CI green.
