# Citation-Local Clauses Design

## Goal

Verify separately cited clauses as separate claims when the sentence contains
an explicit clause boundary. This improves draft accuracy because evidence for
one citation should not mask, weaken, or contradict a neighboring cited claim.

## Current Gap

`split_citation_clauses()` currently splits only on semicolons. A sentence such
as:

`LoRA improves GLUE \cite{lora}, while Prefix Tuning improves SQuAD \cite{prefix}.`

is parsed as one claim with two citation keys. The verifier then has to judge a
compound claim against both sources, often returning `partially_supported` even
though each citation-local claim is independently supported. If one clause is
wrong, the whole sentence can become a broad contradiction rather than a local
diagnostic for the wrong citation.

## Approach Options

1. Split on all commas. This catches many cases but is too broad for academic
   prose and can split non-claim modifiers.
2. Split only on semicolons. This is safe but misses common `while`, `whereas`,
   `but`, and `and` citation patterns.
3. Split on explicit punctuation plus discourse markers when each resulting
   piece has at least one citation. This is the recommended path because it is
   conservative and citation-local.

## Design

Extend `split_citation_clauses()` with explicit marker boundaries:

- semicolon, preserving existing behavior;
- comma followed by `while`, `whereas`, `but`, or `and`;
- optional future-safe support for bare `while`/`whereas` only when both sides
  cite sources and the split does not produce empty text.

The marker should be removed from the second clause so `while Prefix Tuning ...`
becomes `Prefix Tuning ...`. The function returns split clauses only when at
least two pieces contain citations. Otherwise it returns the original sentence.

## Non-Goals

- Do not split uncited clauses.
- Do not infer citation scope from proximity when a boundary is implicit.
- Do not change claim atomization or evidence retrieval in this slice.
- Do not introduce parser dependencies beyond regex.

## Tests And Evaluation

Add parser tests proving:

- comma-`while` with two citations becomes two claims;
- comma-`but` or comma-`and` with two citations becomes two clauses;
- the parser does not split when only one side has a citation;
- existing semicolon splitting still works.

Add verifier/draft-eval coverage proving:

- two independently supported citation-local clauses are both `supported`;
- a wrong second clause is localized to the second parsed claim instead of
  contaminating the first claim.

The local benchmark should keep `false_supported_rate = 0.0`.
