# Causal Calibration Design

## Goal

Reduce false `supported` labels and unnecessary partial labels around causal
claims. A draft claim that says a result was caused by a factor must not be
fully supported by merely associative, correlational, observational, or
non-causal evidence. Conversely, a causal claim can be supported when the cited
span gives an explicit causal design signal and the same outcome direction.

## Current Behavior

The existing strength lens catches direct `causes` versus `associated` or
`correlated` cases. A probe still showed two gaps:

- `Higher temperature leads to increased failure rates.` versus
  `Higher temperature correlated with increased failure rates ...` was labeled
  `supported`.
- `The intervention caused test scores to improve.` versus
  `The randomized intervention improved test scores relative to control.` was
  labeled `partially_supported`.

The first gap is a false-supported academic-integrity risk. The second gap is a
supported-recall issue, but only when the evidence contains a credible design
signal.

## Approach

Extend the existing strength lens instead of adding a separate causal lens.
That lens already owns claim-strength overstatements, and causal language is a
strength/claim-type issue. The implementation should:

- Treat `leads to`, `led to`, `results in`, `resulted in`, and `drives` as
  causal claim language.
- Treat `observational`, `cross-sectional`, `retrospective`, `non-randomized`,
  `association`, and `correlation` as weaker causal evidence when local context
  overlaps the claim.
- Keep these weaker-evidence cases as `partially_supported`, not
  `contradicted`, because association can be relevant evidence but cannot prove
  a causal statement.
- Add a narrow semantic-support helper for explicit causal-design evidence:
  randomized or controlled intervention evidence may support a causal claim
  when overlap is high and no deterministic conflict fires first.

## Scope

This is not a general causal inference engine. It is a conservative calibration
layer for common wording mistakes. It should avoid inferring causality from
generic experiments, correlations, or observational cohorts unless the evidence
contains an explicit randomized/controlled/intervention signal.

## Tests

Add unit tests for:

- causal verbs beyond `causes`
- observational/correlation evidence blocking full support
- randomized intervention evidence supporting a matching causal claim
- negated randomized evidence still contradicting or failing support

Add direct eval rows so `eval-suite` tracks both the new false-supported guard
and the new supported-recall path.
