# Outcome and Protocol Hardening Design

## Context

CiteProof currently saturates the committed heuristic benchmarks:

- `examples/claim_support.jsonl`: 4 cases, accuracy 1.0, false-supported rate 0.0
- `examples/edge_cases/claim_support.jsonl`: 96 cases, accuracy 1.0, false-supported rate 0.0
- `examples/hallucination`: 5 cases, accuracy 1.0, false-supported rate 0.0

Those scores prove the curated suite is passing, not that the verifier has
general 100% accuracy. Fresh adversarial probes found high-risk false-supported
cases where evidence overlaps lexically with the claim but reverses or narrows a
scientific fact:

- claimed improvement while the specific outcome is unchanged;
- mixed effects where evidence helps one subgroup but worsens another;
- lower-is-better metrics such as MAE treated as ordinary improvement;
- commercial/public availability overclaims;
- protocol-slot conflicts such as Bonferroni versus Benjamini-Hochberg,
  train/test leakage, blinded versus unblinded, and primary versus secondary
  endpoint swaps.

Optional transformer NLI helped on some availability and non-inferiority probes,
but still returned `supported` for unchanged outcomes and mixed effects. On the
96-case edge suite it preserved false-supported rate 0.0 but reduced accuracy to
0.9583, so NLI remains a diagnostic or audit signal rather than the default
answer for this slice.

## External Motivation

The design follows the scientific fact-checking framing used by SciFact:
retrieve evidence, identify rationales, and judge support or refutation. It also
matches recent error-analysis findings from scientific claim-verification
benchmarks: partially supported evidence and stance-neutral evidence are common
sources of model error. HALLMARK remains relevant for bibliography/reference
hallucinations, not direct claim-support verification.

## Chosen Approach

Add two deterministic fact lenses and keep them conservative:

1. `outcome_lens.py`
   - hard conflicts for unchanged/no-change evidence against claimed outcome
     improvement or reduction;
   - partial support for mixed-effect evidence where the claimed outcome improves
     in one context and worsens in another;
   - hard conflicts for lower-is-better metrics when evidence reports a higher
     value as the outcome.

2. `protocol_lens.py`
   - hard conflicts for mutually exclusive academic protocol slots:
     multiple-comparison correction, blinding, prospective/retrospective design,
     encoder-only/decoder-only architecture, train/test disjointness, and
     duplicate preprocessing;
   - partial support for measurement-target swaps such as primary versus
     secondary endpoint and calibration versus discrimination.

Both lenses integrate through `fact_lenses.inspect_facts`, preserving the
current adjudicator ordering:

1. deterministic contradiction blocks support;
2. deterministic partial-support tension blocks full support;
3. heuristic/NLI decisions run only after the high-risk gates.

## Alternatives Considered

Global NLI default:
This reduces some false-supported cases but regresses supported recall on the
current edge suite. It is useful in audit mode but too blunt as the default.

Raise the global lexical-support threshold:
This would reduce false support but would also damage valid paraphrase support.
The current failures are slot-specific, so slot-specific lenses are cleaner.

Single large academic-integrity lens:
This would be harder to test and likely exceed the repo's preferred file size.
Two focused modules keep boundaries clear and match the existing lens pattern.

## Data Flow

`adjudicate_evidence` calls `judge_evidence`, which calls `inspect_facts`.
`inspect_facts` will call the new outcome and protocol lenses in the hard
conflict block, and protocol/outcome tension checks in the partial-support block.
Findings remain plain strings so the existing `FactInspection` interface does
not change.

## Failure Modes

Hard outcome and protocol conflicts should map to existing failure modes:

- outcome polarity/status conflicts: `negation_conflict`;
- protocol, measurement-target, and study-design conflicts: `entity_conflict`;
- narrower mixed-effect evidence: `scope_overstatement`.

No new public label is required.

## Tests and Benchmarks

Add direct unit tests for each new lens and integration tests through
`adjudicate_evidence` or `judge_evidence`. Add the same adversarial rows to
`examples/edge_cases/claim_support.jsonl` so benchmark saturation tracks the new
risks.

Required gates:

- new direct tests fail before implementation and pass after;
- `uv run pytest -q -p no:cacheprovider`;
- `uv run citeproof eval examples/claim_support.jsonl`;
- `uv run citeproof eval examples/edge_cases/claim_support.jsonl`;
- `uv run citeproof eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl`;
- `uv run ruff check --no-cache .`.

## Out of Scope

This slice does not make NLI the default, train a model, add a SaaS/editor
surface, or claim real-world 100% accuracy. It closes verified false-supported
classes and expands the regression suite so future changes cannot silently
reintroduce them.
