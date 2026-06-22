# Negation And Comparator Fact Lenses Design

## Goal

Reduce false `supported` labels for claims where the cited evidence has high
lexical overlap but explicitly says the opposite. This slice targets
academic-integrity failures where a draft states that a method uses, trains on,
improves, increases, decreases, or exceeds a quantity, while the cited source
negates or bounds that statement.

The target remains conservative. A high-confidence explicit conflict should
become `contradicted`; a weaker tension should become `partially_supported` or
`uncertain`, never `supported`.

## Current Gap

The current verifier already catches several numeric, entity, comparison, year,
scope, and metric-negation failures. Fresh probes still show false `supported`
judgments for:

- `The method uses LoRA adapters.` vs `The method does not use LoRA adapters.`
- `The model was trained on ImageNet.` vs `The model was not trained on ImageNet.`
- `The approach uses offline pretraining.` vs `The approach works without offline pretraining.`
- `Error decreased by 5 percent.` vs `Error increased by 5 percent.`
- `Schema-Guided Dialogue contains over 16k task-oriented dialogues.` vs
  `Schema-Guided Dialogue contains up to 16,000 task-oriented dialogues.`

These cases look strongly related lexically, so they can outrank the absence of
a deterministic conflict and become `supported`.

## Approach Options

1. Add deterministic lenses for explicit negation and comparator conflicts.
   This is explainable, cheap, and fits CiteProof's current trust model.
2. Add an external benchmark adapter first. This improves measurement but does
   not fix known current failures.
3. Add a learned verifier as a veto layer first. This can help in a follow-up, but it is
   harder to calibrate and should not bypass deterministic source and citation
   gates.

Use option 1 for this slice. Keep option 2 and option 3 as follow-up work once
the committed adversarial suite is stronger.

## Design Principles

- `supported` requires absence of detected source tension.
- Deterministic contradiction findings must be narrow and explainable.
- If a pattern is plausible but not high-confidence, downgrade instead of
  contradicting.
- Fact lenses should return source-readable findings that map to stable failure
  modes.
- The implementation should be modular enough to keep files under 300 lines.

## Explicit Negation Lens

Add a small deterministic lens for predicate-object negation. It should detect
only common academic predicates where the object phrase is short and overlaps
between claim and evidence:

- `use`, `uses`, `used`
- `train on`, `trained on`
- `pretrain on`, `pretrained on`
- `fine-tune on`, `fine-tuned on`

Examples:

- claim: `The method uses LoRA adapters.`
- evidence: `The method does not use LoRA adapters.`
- finding: `Negation conflict: evidence negates use of LoRA adapters.`

Accepted negation forms:

- `does not use X`, `did not use X`, `not use X`
- `was not trained on X`, `were not trained on X`, `not trained on X`
- `without X` when the claim uses or relies on the same object phrase

The lens should not try to solve all natural language negation. It should avoid
contradicting broad claims when the negated object does not overlap materially.
For example, `does not use labels` should not contradict `uses LoRA adapters`.

## Directional Change Lens

Add a lens for explicit directional changes over the same metric or object.

Positive direction terms:

- `increase`, `increases`, `increased`
- `higher`, `more`

Negative direction terms:

- `decrease`, `decreases`, `decreased`
- `lower`, `less`, `reduced`

Examples:

- claim: `Error decreased by 5 percent.`
- evidence: `Error increased by 5 percent.`
- finding: `Direction conflict: claim says decreased while evidence says increased.`

The lens should require material token overlap around the changed quantity or
metric. It should avoid contradictions for unrelated dimensions, such as
`training time decreased` vs `accuracy increased`, unless the compared metric
also overlaps.

## Numeric Bound Lens

Extend quantity handling with comparator categories around the normalized
quantity mention.

Lower-bound comparators:

- `over`, `more than`, `greater than`, `at least`, `no less than`

Upper-bound comparators:

- `up to`, `at most`, `no more than`, `under`, `less than`

Exact comparators:

- `exactly`, plain unqualified quantities

The first version should only produce `contradicted` when:

- the unit matches,
- the normalized quantity matches or conflicts in a direction-sensitive way,
- the comparator categories are incompatible.

Examples:

- `over 16k dialogues` vs `up to 16,000 dialogues` -> contradicted
- `over 16k dialogues` vs `16,000 dialogues` -> partially supported or uncertain
- `at least 16k dialogues` vs `20,000 dialogues` -> not contradicted
- `at most 16k dialogues` vs `20,000 dialogues` -> contradicted

This requires keeping local comparator context with quantity mentions. It should
not turn every bare quantity mismatch into a bound conflict; the existing
numeric conflict lens already handles different exact values.

## Integration

The cleanest implementation is a new focused module, for example
`src/citeproof/negation_lens.py`, with functions returning finding strings.
`fact_lenses.py` should call it alongside numeric, unit, year, comparison, and
entity checks.

Failure-mode mapping can reuse existing categories where possible:

- explicit negation and direction conflicts map to `negation_conflict`;
- numeric bound conflicts map to `numeric_conflict`.

If the current enum or adjudicator lacks a precise mapping, add the smallest
stable mapping change needed for eval diagnostics.

## Benchmark Expansion

Add adversarial direct eval cases for:

- LoRA use negation
- ImageNet training negation
- offline pretraining negation
- increase vs decrease direction swap
- `over 16k` vs `up to 16,000`
- a non-conflict bound case such as `at least 16k` vs `20,000`
- an unrelated negation case that must not contradict

Each new contradiction case should declare `expected_failure_mode` when stable.
The benchmark should prove the main target: none of these known failures may
remain `supported`.

## Evaluation

Run the normal local gate:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache .
PYTHONPATH=src python -m citeproof.cli eval examples/claim_support.jsonl
PYTHONPATH=src python -m citeproof.cli eval examples/edge_cases/claim_support.jsonl \
  --details-output /tmp/citeproof_negation_edge.json
PYTHONPATH=src python -m citeproof.cli eval-draft examples/hallucination/draft.md \
  --sources examples/hallucination/sources \
  --bib examples/hallucination/references.bib \
  --expected examples/hallucination/expected.jsonl \
  --details-output /tmp/citeproof_negation_hallucination.json
```

Expected target after this slice:

- all new false-supported probes stop being `supported`;
- local `false_supported_rate` remains `0.0`;
- existing supported cases remain supported unless the evidence is genuinely
  weaker than the claim;
- all touched Python files stay under 300 lines.

## Follow-Up Work

After this deterministic slice, the next reliability layers should be:

- SciFact/SciFact-Open adapter for scientific claim verification benchmarking;
- FActScore-style long-form atomic fact scoring over paper drafts;
- RAGTruth-style hallucination-span eval adapter;
- optional MiniCheck or similar local grounding model as a veto/downgrade
  signal;
- larger held-out adversarial suites created from real papers and PDF evidence.

## References

- SciFact: https://arxiv.org/abs/2004.14974
- SciFact-Open: https://arxiv.org/abs/2210.13777
- FActScore: https://arxiv.org/abs/2305.14251
- MiniCheck: https://arxiv.org/abs/2404.10774
- RAGTruth: https://arxiv.org/abs/2401.00396
