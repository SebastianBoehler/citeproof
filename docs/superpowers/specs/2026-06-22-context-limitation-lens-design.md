# Context Limitation Lens Design

## Problem

The verifier now catches many explicit conflicts, but adversarial probes still
show false `supported` labels when evidence is true but narrower than the draft
claim. Examples:

- `The method improves accuracy.` supported by `only when oracle labels are available`.
- `The model improves performance on ImageNet.` supported by `a 1% ImageNet subset`.
- `The drug reduces inflammation in humans.` supported by `in mice`.
- `The drug reduces tumor size in patients.` supported by `in vitro`.
- `The tool improves productivity.` supported by `one case study`.
- `Retrieval improves factuality.` supported by `the no-retrieval ablation improves factuality`.

These are academic-integrity risks because the citation is relevant and lexical
overlap is high, but the evidence does not support the full claim.

## Scope

Add a deterministic `context_lens` with two public checks:

- `inspect_context_tensions(claim, evidence)`: returns partial-support findings
  for limited scope, subset, population, or experimental setting evidence.
- `inspect_component_exclusion_conflicts(claim, evidence)`: returns hard findings
  when the claim attributes an effect to a component that evidence explicitly
  removes or excludes.

## Non-Goals

- No broad domain ontology.
- No attempt to infer every possible population or experimental setting.
- No mandatory NLI/model call.
- No new retrieval strategy.

## Conservative Rules

Context tension fires only when evidence has a clear limiter and overlaps the
claim topic:

- condition: `only when`, `only if`, `under oracle`, `with oracle`
- subset: `1% subset`, `subset`, `small subset`, `case study`, `single site`
- setting: `simulated`, `simulation`, `in vitro`, `ex vivo`, `in mice`
- mismatch pairs: `humans/patients/adults` in the claim vs `mice/children/in vitro`
  in evidence, plus hardware/real-world claims vs simulation-only evidence
- mixed setting: evidence states support in one setting but not another, such as
  `in simulation but not on hardware`

Component exclusion conflict fires only when:

- the claim says a named component improves/reduces/increases an outcome; and
- evidence uses an exclusion phrase for the same component, such as `no-retrieval`,
  `without retrieval`, or `retrieval removed`; and
- the outcome context overlaps.

## Expected Labels

- Context limitation cases: `partially_supported`, failure mode
  `scope_overstatement`.
- Component exclusion cases: `contradicted`, failure mode `negation_conflict`.

## Benchmark Additions

Add edge cases:

- `oracle-condition-context-tension`
- `simulation-hardware-context-tension`
- `subset-context-tension`
- `human-animal-context-tension`
- `patient-invitro-context-tension`
- `case-study-context-tension`
- `component-exclusion-conflict`

Add at least two supported guards:

- exact simulation-scoped claim with simulation evidence remains supported.
- exact case-study claim with case-study evidence remains supported.

## Verification

Focused checks:

- `python -m pytest tests/test_context_lens.py tests/test_entailment_context.py -q -p no:cacheprovider`
- `ruff check --no-cache src/citeproof/context_lens.py tests/test_context_lens.py tests/test_entailment_context.py`

Full gate:

- `python -m pytest -q -p no:cacheprovider`
- `ruff check --no-cache .`
- `PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl`
- `PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl`
- `PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl`

Success requires the edge suite to grow while keeping `false_supported_rate = 0.0`.
