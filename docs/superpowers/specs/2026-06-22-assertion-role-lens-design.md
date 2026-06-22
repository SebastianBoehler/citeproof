# Assertion Status and Role Lens Design

## Problem

The current verifier saturates the curated benchmarks, but adversarial probes still
show false `supported` labels for common academic overclaims:

- A result claim is treated as supported by future-work or hypothesis language.
- A training-data claim is treated as supported by evaluation-data evidence.
- An outperform claim is treated as supported by tie/equivalence wording.
- A provenance claim is treated as supported when the same object appears in a
  different role, e.g. a model audited annotations but did not generate them.

For academic-integrity use, these should be blocked from full support even when
lexical overlap is high.

## Scope

This slice adds deterministic checks for two narrow failure families:

1. **Assertion status mismatch:** claims framed as established findings cannot be
   fully supported by evidence framed as planned, hypothetical, intended, or only
   designed to achieve the finding.
2. **Role/provenance mismatch:** claims about generation, annotation, auditing,
   filtering, licensing, retrieval source, training, or evaluation roles cannot
   be fully supported by evidence that assigns the same object to a different
   actor, artifact, source, stage, or timing.

It also extends comparison handling so tie/equivalence evidence blocks stronger
outperformance claims.

## Non-Goals

- No broad semantic parser or LLM auditor in this slice.
- No mandatory NLI dependency.
- No speculative fallback or mock scoring.
- No attempt to classify every discourse cue in scientific writing.

## Architecture

Add two small modules:

- `assertion_lens.inspect_assertion_status_tensions(claim, evidence)`
- `role_lens.inspect_role_conflicts(claim, evidence)`

`inspect_facts` will include role conflicts in hard findings and assertion-status
tensions in partial-support findings. The comparison lens will add a neutral/tie
relation family and return `PARTIALLY_SUPPORTED` when a stronger comparison claim
is paired with neutral evidence for the same comparison pair.

## Conservative Rules

Assertion-status tension fires only when:

- the claim contains an assertive result predicate such as `improves`, `reduces`,
  `outperforms`, `shows`, or `demonstrates`; and
- the evidence contains local uncertainty/status cues such as `future work`,
  `hypothesize`, `designed to`, `intended to`, `aims to`, `will test`, or
  `proposed to`; and
- claim/evidence context overlaps after removing the status cue words.

Role/provenance conflict fires only when:

- a controlled binding pattern appears in both claim and evidence; and
- the same artifact/system/object context appears in both sides; and
- the role holder, source, artifact, stage, or timing is incompatible.

Initial controlled families:

- `generated/annotated by` vs `audited/reviewed/evaluated by`
- `trained on/learns from` vs `evaluated on/evaluated against`
- `retrieves passages from` vs `questions from`
- dataset license vs code license when the claimed dataset license differs
- filters prompts before evaluation vs filters outputs after evaluation

Tie/equivalence comparison tension fires only for the same material anchor pair
and compatible comparison context.

## Benchmark Additions

Add edge cases expected to avoid false support:

- `future-work-result-tension`: result claim vs future work will test result.
- `hypothesis-result-tension`: result claim vs hypothesis.
- `designed-to-result-tension`: result claim vs intended design goal.
- `training-evaluation-role-conflict`: trained-on claim vs evaluated-on evidence.
- `evaluation-training-role-conflict`: evaluated-on claim vs trained-on evidence.
- `generation-audit-role-conflict`: generated-by claim vs audit role evidence.
- `filter-stage-role-conflict`: prompt filtering before evaluation vs output filtering after evaluation.
- `dataset-code-license-role-conflict`: dataset license claim vs code license plus dataset non-commercial license.
- `label-source-role-conflict`: gold-label learning claim vs pseudo-label learning and gold-label evaluation.
- `retrieval-source-role-conflict`: Wikipedia retrieval claim vs Common Crawl retrieval for Wikipedia questions.
- `tie-outperform-comparison-tension`: outperform claim vs tie evidence.

Expected labels:

- Assertion-status and tie/equivalence cases: `partially_supported`.
- Role/provenance binding cases: `contradicted` with `entity_conflict`.

## Verification

Focused checks:

- `python -m pytest tests/test_assertion_lens.py tests/test_role_lens.py tests/test_entailment_assertion_roles.py tests/test_comparison_lens.py -q -p no:cacheprovider`
- `ruff check --no-cache src/citeproof/assertion_lens.py src/citeproof/role_lens.py src/citeproof/comparison_lens.py tests/test_assertion_lens.py tests/test_role_lens.py tests/test_entailment_assertion_roles.py`

Full gate:

- `python -m pytest -q -p no:cacheprovider`
- `ruff check --no-cache .`
- `PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl`
- `PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl`
- `PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl`

Success requires false-supported rate to remain `0.0` while the edge suite grows.
