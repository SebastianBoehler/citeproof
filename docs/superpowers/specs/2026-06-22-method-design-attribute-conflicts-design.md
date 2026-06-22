# Method Design Attribute Conflicts Design

## Goal

Reduce additional false `supported` labels caused by high lexical overlap when a
claim swaps a method or study-design attribute relative to the evidence.

Fresh probes on the current verifier showed false support for:

- supervised vs unsupervised training
- randomized vs observational study design
- abstractive vs extractive summarization
- multi-agent vs single-agent settings

## Options Considered

1. Add a new method-design lens.
   This keeps code names very specific, but duplicates the controlled-value and
   context-overlap machinery already present in `attribute_lens`.

2. Extend the existing attribute lens.
   This matches the current architecture: controlled academic attributes are
   centralized in one small module and integrated once through `fact_lenses`.
   This is the selected approach.

3. Route the probes through ML/NLI.
   This may catch broader paraphrases later, but it is less auditable and does
   not give deterministic benchmark guarantees for this high-risk slice.

## Scope

Extend `src/citeproof/attribute_lens.py` with four controlled groups:

- supervision: `supervised`, `unsupervised`
- study design: `randomized`, `observational`
- summarization style: `abstractive`, `extractive`
- agent setting: `single-agent`, `multi-agent`

The lens remains conservative:

- conflicts require disjoint value sets from the same group
- conflicts require shared non-attribute context
- evidence mentioning both the claim value and a competing value does not create
  a hard contradiction in this slice

## Data Flow

No new integration layer is required. `fact_lenses.inspect_facts` already calls
`inspect_attribute_conflicts`, and `adjudicator` already maps known attribute
conflict strings to `entity_conflict`. The only integration update is adding the
new conflict names to the adjudicator's attribute conflict list.

## Testing

Add direct lens tests and end-to-end entailment tests for:

- `The method uses supervised training.` vs `The method uses unsupervised training without labels.`
- `The study is randomized.` vs `The study is observational and not randomized.`
- `The system performs abstractive summarization.` vs `The system performs extractive summarization.`
- `The policy is trained in a multi-agent environment.` vs `The policy is trained in a single-agent environment.`

Add at least one boundary test showing a different-context attribute mention does
not produce a hard conflict.

## Success Check

The edge-case benchmark grows from 46 to 50 cases. The full local suite, ruff,
sample eval, edge eval, hallucination eval, and GitHub CI all pass with
`false_supported_rate = 0.0`.
