# Technical Property Conflicts Design

## Goal

Reduce false `supported` labels for high-overlap claims that swap a technical
property rather than a named entity or numeric value.

Fresh probes on current `main` found false support for:

- linear vs quadratic or logarithmic complexity
- exact vs approximate inference
- frozen vs fine-tuned encoder training
- dense vs sparse rewards
- in-domain vs out-of-domain evaluation
- private vs public records

These are common academic-paper facts where lexical overlap is high, but the
claim is wrong if the cited source gives the opposite technical condition.

## Options Considered

1. Extend `attribute_lens` again.
   This would reuse existing machinery but would turn the attribute lens into a
   broad catch-all.

2. Add a focused `technical_property_lens`.
   This keeps method/data attributes separate from technical conditions while
   preserving the same deterministic, auditable pattern. This is selected.

3. Route all high-overlap property swaps through NLI.
   This may help later for broader paraphrases, but it is less deterministic
   and harder to benchmark tightly for academic-integrity guarantees.

## Scope

Create `src/citeproof/technical_property_lens.py` with controlled groups:

- complexity: `constant`, `logarithmic`, `linear`, `quadratic`, `cubic`, `exponential`
- inference fidelity: `exact`, `approximate`
- trainability: `frozen`, `fine-tuned`
- reward density: `dense`, `sparse`
- evaluation domain: `in-domain`, `out-of-domain`
- data sensitivity: `private`, `public`

The lens remains conservative:

- conflicts require disjoint values from the same group
- conflicts require shared non-property context
- evidence mentioning both values does not create a hard contradiction
- property words in clearly different contexts do not create a hard contradiction

## Data Flow

`inspect_technical_property_conflicts(claim, evidence)` returns hard conflict
findings. `fact_lenses.inspect_facts` appends these to hard findings. The
adjudicator maps these findings to `entity_conflict`, because the current public
failure-mode enum has no separate technical-property category.

## Testing

Add direct lens tests and end-to-end tests for:

- `linear time` vs `quadratic time`
- `exact inference` vs `approximate inference`
- `encoder is frozen` vs `encoder is fine-tuned`
- `dense rewards` vs `sparse rewards`
- `out-of-domain data` vs `in-domain data`
- `private medical records` vs `public medical records`

Add boundary tests for mixed-value evidence and different-context mentions.

## Success Check

The edge-case benchmark grows from 50 to 56 cases. The full local suite, ruff,
sample eval, edge eval, hallucination eval, and GitHub CI all pass with
`false_supported_rate = 0.0`.
