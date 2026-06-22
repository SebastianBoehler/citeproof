# Contrast And Metric Slots Design

## Context

After protocol-slot hardening, fresh probes still found CS/ML claims that are
unsafe because `overlap >= 0.68` can become `supported` when no deterministic
lens fires. Four high-value cases are:

- evidence excludes the claimed architecture with "rather than"
- evidence excludes the claimed pretraining objective with "rather than"
- evidence swaps macro-AUROC and micro-AUROC
- evidence says BLEU is unchanged while another metric improves

These are common paper-writing errors: the cited source is nearby and relevant,
but it supports a different slot or directly excludes the claim.

## Brainstormed Approaches

1. Add typed deterministic checks. Use a contrastive-exclusion lens plus small
   metric/outcome expansions. This is recommended because each finding is
   explainable and can route to a stable failure mode.
2. Tighten lexical fallback. Demote high-overlap evidence containing cue words
   like "rather than", "but", "unchanged", or "macro" unless another lens
   accounts for them. This is safer than the current fallback, but it can reduce
   supported recall for correctly stated contrastive evidence.
3. Add an NLI ensemble. This may catch wider paraphrases, but it adds runtime
   variance and needs calibration before it can be trusted for academic
   integrity.

## Selected Design

Implement deterministic checks now. Broader fallback tightening needs separate
calibration data before it should affect supported-recall behavior.

Add `contrast_lens.py` with `inspect_contrast_exclusion_conflicts(claim,
evidence)`. It flags evidence patterns such as "rather than X", "instead of X",
and "as opposed to X" when:

- the claim itself is not already contrastive
- the excluded phrase has enough content tokens
- the excluded phrase is substantially present in the claim
- the surrounding claim/evidence context overlaps after excluding that phrase

Extend existing metric/outcome lenses:

- add macro-AUROC vs micro-AUROC to `statistical_lens`
- add BLEU and chrF to `outcome_lens`

## Data Flow

1. `inspect_facts` calls the new contrast lens with the other hard-conflict
   lenses.
2. Contrast exclusions become `contradicted` and route to
   `negation_conflict`.
3. AUROC averaging conflicts route through existing statistical conflict
   handling.
4. BLEU unchanged evidence routes through the existing outcome-status conflict.

## Error Handling

The contrast lens should stay conservative:

- do not fire when the claim itself contains a contrast cue
- do not fire on short excluded phrases
- do not fire without enough context overlap
- do not add model calls or fallbacks

## Testing

Add focused tests for the four false-supported probes and for matching/positive
contrast cases that should remain clean. Add edge-eval rows so the new cases are
part of the regression suite.

## Success Check

The slice is complete when focused tests pass, the expanded edge eval and
eval-suite remain saturated, full pytest and ruff pass, touched files stay below
300 lines, and the commits are pushed with CI green.
