# Claim Strength Overstatement Design

## Goal

Reduce false `supported` labels when evidence supports a weaker version of the
claim than the draft states.

Fresh probes on current `main` found false support for:

- causal claims supported only by association or correlation
- `best` claims supported only by competitive performance
- `large` or `substantial` gains contradicted by small or modest gains
- `no overhead` claims contradicted by small overhead
- full recovery claims supported only by partial recovery

These are common academic-integrity failures because the citation is related but
does not justify the strength of the written claim.

## Options Considered

1. Add broad NLI escalation for all high-overlap evidence.
   This may help later, but it is slower and less deterministic.

2. Add only hard contradiction rules.
   This catches direct conflicts but is too aggressive for causal vs associative
   evidence, where the safer label is `partially_supported`.

3. Add a focused claim-strength lens.
   This can hard-block direct contradictions such as `large` vs `small`, and
   downgrade weaker evidence such as association-only support to partial. This
   is selected.

## Scope

Create `src/citeproof/strength_lens.py` with:

- hard conflicts:
  - large or substantial vs small or modest
  - no overhead vs small overhead
- tensions:
  - causal/proves claims vs associated, correlated, or suggests evidence
  - best claims vs competitive evidence
  - full/complete recovery claims vs partial evidence

The lens remains conservative:

- require shared non-strength context
- prefer `partially_supported` over `contradicted` for weaker-but-related evidence
- do not attempt arbitrary sentiment or effect-size interpretation

## Data Flow

`inspect_strength_conflicts` appends hard findings in `fact_lenses.inspect_facts`.
`inspect_strength_tensions` appends partial-support findings. `adjudicator`
maps strength conflicts to `conflicting_sources`; strength tensions naturally
map to `scope_overstatement` through existing partial-support handling.

## Testing

Add direct and end-to-end tests for:

- causes vs associated
- causes vs correlated
- best vs competitive
- large vs small
- substantial vs modest
- no overhead vs small overhead
- fully recovers vs partially recovers

Add boundary tests where strength words occur in different contexts and must not
fire.

## Success Check

The edge-case benchmark grows from 63 to 70 cases. The full local suite, ruff,
sample eval, edge eval, hallucination eval, and GitHub CI all pass with
`false_supported_rate = 0.0`.
