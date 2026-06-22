# Numeric Quantity Normalization Design

## Goal

Catch dataset-size and experiment-size contradictions expressed with compact or
spelled numeric forms. Academic drafts often use `16k`, `1M`, `1 million`, or
`four GPUs`; the verifier should not mark those as supported when the cited
source gives a different quantity.

## Current Gap

The fact lens only reads plain digit-plus-unit forms such as `6000 examples`.
The entailment fallback separately parses one plain number and unit. That means
the claim `Schema-Guided Dialogue contains over 16k task-oriented dialogues`
against evidence `Schema-Guided Dialogue contains 15,000 task-oriented
dialogues` currently returns `supported` through high lexical overlap, even
though the quantity is wrong.

## Approach Options

1. Extend regexes separately in `fact_lenses.py` and `entailment.py`.
   This is fast but duplicates high-risk parsing and grows `entailment.py`
   beyond the local 300-line limit.
2. Add a shared deterministic quantity parser and use it from both places.
   This keeps behavior consistent and shrinks the entailment file.
3. Use an NLP number parser dependency. This covers more language but adds a
   new dependency for a small deterministic problem.

Use option 2.

## Design

Create `src/citeproof/quantities.py` with one responsibility: extract normalized
quantity mentions from text. A quantity mention contains:

- normalized number string;
- normalized unit string;
- original matched text.

Supported numeric forms:

- plain digits with commas or decimals: `15,000`, `42`, `4`;
- compact suffixes: `16k`, `16K`, `1M`, `1m`;
- scale words after digits: `1 million`, `2 thousand`;
- common small spelled numbers used in papers and tests: `one` through `ten`,
  plus `twenty`, `thirty`, `forty`, `fifty`, and two-word forms such as
  `forty two`.

Supported units remain conservative and academic:

- examples, samples, GPUs, turns, conversations, dialogues, domains, languages,
  and percent/%.

The parser should normalize plural units and `percent` to `%`. It should not
try to parse arbitrary free-form quantities or ordinals.

## Integration

- `fact_lenses.py` should call the shared parser for numeric and unit conflict
  checks.
- `entailment.py` should use the same parser for its single-number conflict
  fallback and remove its duplicate number regex/function.
- Existing unit-overlap behavior must remain: evidence that says `42 percent`
  and also `42 examples` should not be a unit conflict for a claim that says
  `42 percent`.

## Tests And Evaluation

Add tests for:

- `16k dialogues` vs `15,000 dialogues` -> contradicted;
- `1M conversations` vs `1 million conversations` -> no contradiction;
- `4 GPUs` vs `four GPUs` -> no contradiction;
- `4 GPUs` vs `three GPUs` -> contradicted;
- `42 percent` vs `42 examples` remains unit conflict;
- `42 percent ... 42 examples` remains non-conflict.

Add one edge benchmark row:

- `compact-number-conflict`: claim `Schema-Guided Dialogue contains over 16k
  task-oriented dialogues`; evidence `Schema-Guided Dialogue contains 15,000
  task-oriented dialogues`; expected `contradicted` with
  `numeric_conflict`.

The edge-case total becomes 25 and `false_supported_rate` must remain `0.0`.
