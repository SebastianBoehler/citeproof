# Comparison Direction Verification Design

## Context

CiteProof now catches missing/swapped material anchors, but a different
false-supported class remains: reverse comparisons. If a claim says `A
outperforms B` and the evidence says `B outperforms A`, the current heuristic
sees the same anchors and comparison words and returns `supported`.

Live probe before this design:

```text
Claim:    LoRA outperforms Prefix Tuning on GLUE.
Evidence: Prefix Tuning outperforms LoRA on GLUE.
Current:  supported
Wanted:   contradicted, comparison_direction_conflict
```

This is high-risk for academic writing because leaderboard, ablation, and
benchmark claims often hinge on comparison direction rather than entity
presence alone.

## Approaches Considered

### 1. Deterministic Comparison-Direction Lens (Recommended)

Extract simple comparison triples from claim and evidence when both sides are
explicitly named around a directional comparator such as `outperforms`,
`better than`, `higher than`, or `superior to`. If the evidence reverses the
left/right anchors for the same comparator family, return
`comparison_direction_conflict`.

Trade-off: It only handles explicit local comparisons, but it is auditable,
offline, precise, and directly blocks a confirmed false-supported path.

### 2. General Claim-Triplet Extraction

Introduce a broader subject-relation-object extractor inspired by RefChecker and
use it for many relation types.

Trade-off: More general, but harder to keep deterministic and precise. It is a
larger project that should follow this targeted gate.

### 3. Model Ensemble Confirmation

Rely on optional NLI or a MiniCheck-style checker to detect reversed
comparisons.

Trade-off: Useful later, but model scores need calibration and can be
unavailable. Deterministic comparison conflicts should be caught even in
offline heuristic mode.

## Design

Add a deterministic comparison-direction lens to `src/citeproof/fact_lenses.py`.
It should run with the other contradiction checks and produce a finding that
maps to the existing `FailureMode.COMPARISON_DIRECTION_CONFLICT`.

The extractor should be conservative:

- Only inspect explicit binary comparison patterns with a named left side and
  named right side.
- Require both claim-side anchors to appear in the evidence comparison.
- Treat reverse order as contradiction.
- Treat matching order as no conflict.
- Ignore weak or non-directional comparisons such as `similar to` and
  `comparable to`.
- Avoid firing when one side cannot be anchored.

Supported patterns for this slice:

- `{left} outperforms {right}`
- `{left} is better than {right}`
- `{left} has higher accuracy than {right}`
- `{left} is superior to {right}`

This catches common benchmark prose without claiming full relation extraction.

## Data Flow

1. `inspect_facts(claim, evidence)` calls `_comparison_direction_conflicts`.
2. The helper extracts at most one conservative comparison relation from each
   text.
3. If claim and evidence use the same comparator family and the evidence
   left/right anchors are reversed, `inspect_facts` returns
   `FactInspection(Label.CONTRADICTED, (...))`.
4. `adjudicate_judgments` maps the finding to
   `FailureMode.COMPARISON_DIRECTION_CONFLICT`.
5. `verify_claim` records the conflict in atom traces and exposes review action
   guidance.

## Tests

Add deterministic tests for:

- `LoRA outperforms Prefix Tuning` vs reversed evidence.
- `Model A has higher accuracy than Model B` vs reversed evidence.
- `LoRA is better than Prefix Tuning` vs reversed evidence.
- Matching direction remains supported.
- End-to-end verifier trace returns `comparison_direction_conflict`.
- Edge benchmark row asserts the expected failure mode.

## Non-Goals

- No general dependency parser.
- No broad claim-triplet extractor.
- No new ML model dependency.
- No attempt to resolve aliases or implicit baselines in this slice.
