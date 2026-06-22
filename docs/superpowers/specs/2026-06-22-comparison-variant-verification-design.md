# Comparison Variant Verification Design

## Context

CiteProof now detects reversed explicit comparisons for a narrow set of
phrases, while preserving context/dimension safety. The remaining false-
supported gap is common benchmark wording that means the same thing but uses
different verbs or tense:

```text
LoRA beats Prefix Tuning on GLUE.
Prefix Tuning beats LoRA on GLUE.
```

Current result: `supported`. Desired result: `contradicted` with
`comparison_direction_conflict`.

## Approaches Considered

### 1. Extend Deterministic Comparison Variants (Recommended)

Add a small set of high-precision comparison phrases to the existing comparison
lens: `beats`, `exceeds`, `outperformed`, `achieves higher accuracy than`, and
`has lower error than`. Reuse the current context and dimension checks.

Trade-off: This is still not general relation extraction, but it catches common
paper benchmark prose and stays auditable.

### 2. General Relation Parser

Build a larger parser for arbitrary comparison predicates and metrics.

Trade-off: More coverage, but higher false-positive risk and larger code
surface. The current project benefits more from incremental verified lenses.

### 3. Push To Optional Model Verifier

Let NLI or a future MiniCheck-style model catch these variants.

Trade-off: Useful later, but deterministic benchmark-claim errors should be
caught without model downloads.

## Design

Extend `src/citeproof/comparison_lens.py` with phrase-level relation metadata.
Each relation should carry:

- direction family: higher-is-better or lower-is-better
- dimension: generic, accuracy, or error

For this slice:

- `beats`, `outperforms`, `outperformed`, `exceeds`, `is better than`, and
  `is superior to` are generic higher-is-better comparisons.
- `has higher accuracy than` and `achieves higher accuracy than` are
  higher-is-better accuracy comparisons.
- `has lower error than` is lower-is-better error comparison.

Direction conflicts only fire when both texts compare the same left/right
anchors, the same dimension family, and compatible contexts. If dimensions or
contexts differ, return partial support rather than contradiction. This keeps
the verifier conservative.

## Tests

Add deterministic tests for:

- reversed `beats`
- reversed `exceeds`
- reversed past-tense `outperformed`
- reversed `achieves higher accuracy than`
- reversed `has lower error than`
- cross-context `lower error` returns partial, not entity conflict
- dimension mismatch such as `lower error` vs `higher accuracy` returns partial
- matching-order variants remain non-conflicting

Add one edge benchmark row for `beats`, because it is the highest-frequency
plain-English variant.

## Non-Goals

- No broad comparator parser.
- No aliases or entity linking.
- No model dependency.
- No attempt to support every possible metric phrase in this slice.
