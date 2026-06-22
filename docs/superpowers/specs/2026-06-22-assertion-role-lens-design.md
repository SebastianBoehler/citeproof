# Assertion Status and Role Lens Design

## Problem

The current verifier saturates the curated benchmarks, but adversarial probes still
show false `supported` labels for common academic overclaims:

- A result claim is treated as supported by future-work or hypothesis language.
- A training-data claim is treated as supported by evaluation-data evidence.
- An outperform claim is treated as supported by tie/equivalence wording.

For academic-integrity use, these should be blocked from full support even when
lexical overlap is high.

## Scope

This slice adds deterministic checks for two narrow failure families:

1. **Assertion status mismatch:** claims framed as established findings cannot be
   fully supported by evidence framed as planned, hypothetical, intended, or only
   designed to achieve the finding.
2. **Role mismatch:** claims about training/fine-tuning/pretraining/evaluation
   roles cannot be fully supported by evidence that assigns the same dataset or
   source to a different role.

It also extends comparison handling so tie/equivalence evidence blocks stronger
outperformance claims.

## Non-Goals

- No broad semantic parser or LLM auditor in this slice.
- No mandatory NLI dependency.
- No speculative fallback or mock scoring.
- No attempt to classify every discourse cue in scientific writing.

## Architecture

Add a small `assertion_lens` module with two public functions:

- `inspect_assertion_status_tensions(claim, evidence)`
- `inspect_role_conflicts(claim, evidence)`

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

Role conflict fires only when:

- both claim and evidence mention the same object tokens; and
- the role verbs are controlled opposites, e.g. `trained on` vs `evaluated on`,
  `pretrained on` vs `tested on`, or `fine-tuned on` vs `evaluated on`; and
- the surrounding context overlaps enough to avoid unrelated-clause matches.

Tie/equivalence comparison tension fires only for the same material anchor pair
and compatible comparison context.

## Benchmark Additions

Add edge cases expected to avoid false support:

- `future-work-result-tension`: result claim vs future work will test result.
- `hypothesis-result-tension`: result claim vs hypothesis.
- `designed-to-result-tension`: result claim vs intended design goal.
- `training-evaluation-role-conflict`: trained-on claim vs evaluated-on evidence.
- `evaluation-training-role-conflict`: evaluated-on claim vs trained-on evidence.
- `tie-outperform-comparison-tension`: outperform claim vs tie evidence.

Expected labels:

- Assertion-status and tie/equivalence cases: `partially_supported`.
- Role swap cases: `contradicted` with `entity_conflict`.

## Verification

Focused checks:

- `python -m pytest tests/test_assertion_lens.py tests/test_entailment_assertion_roles.py tests/test_comparison_lens.py -q -p no:cacheprovider`
- `ruff check --no-cache src/citeproof/assertion_lens.py src/citeproof/comparison_lens.py tests/test_assertion_lens.py tests/test_entailment_assertion_roles.py`

Full gate:

- `python -m pytest -q -p no:cacheprovider`
- `ruff check --no-cache .`
- `PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl`
- `PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl`
- `PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md --sources examples/hallucination/sources --bib examples/hallucination/references.bib --expected examples/hallucination/expected.jsonl`

Success requires false-supported rate to remain `0.0` while the edge suite grows.
