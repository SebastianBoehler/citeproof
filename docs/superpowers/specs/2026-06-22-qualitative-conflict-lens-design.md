# Qualitative Conflict Lens Design

## Goal

Reduce false `supported` labels for high-overlap qualitative claims where the
cited evidence changes scope, statistical strength, method property, or
descriptor category. These are common academic-integrity failures because the
same source terms appear while the factual relation changes.

## Current Gap

Fresh probes after the negation/comparator slice still show `supported` for:

- `only method evaluated` vs `one of three methods evaluated`;
- `all evaluated tasks` vs `most evaluated tasks`;
- `achieves state-of-the-art` vs `does not achieve state-of-the-art`;
- `requires no labeled data` vs `requires labeled data`;
- `uses a transformer architecture` vs `uses a convolutional architecture`;
- `uses offline reinforcement learning` vs `uses online reinforcement learning`;
- `significantly improves` vs `not statistically significant`.

These failures are not primarily numeric. They are qualitative scope, strength,
and descriptor conflicts.

## Approach

Add a focused module, `src/citeproof/qualitative_lens.py`, with two public
functions:

- `inspect_qualitative_conflicts(claim, evidence) -> tuple[str, ...]`
- `inspect_qualitative_tensions(claim, evidence) -> tuple[str, ...]`

`fact_lenses.py` should call conflicts as hard contradiction findings and
tensions before the generic lexical support path.

## Hard Conflicts

Return `contradicted` for narrow explicit oppositions:

- exclusivity conflict: claim says `only` while evidence says `one of`,
  `among`, `several`, `multiple`, or `both`;
- significant result conflict: claim says `significant` or `significantly`,
  evidence says `not statistically significant`, `not significant`, or
  `no statistically significant`;
- state-of-the-art conflict: claim says `achieves state-of-the-art`, evidence
  says `does not achieve state-of-the-art`;
- requirement conflict: claim says `requires no X` or `without X`, evidence says
  `requires X` for materially overlapping `X`, or the reverse;
- descriptor conflict pairs over overlapping context:
  `transformer` vs `convolutional`, `offline` vs `online`, `supervised` vs
  `unsupervised`, `synthetic/simulated` vs `real-world`.

These findings should map to existing failure modes:

- significant, SOTA, requirement, and descriptor conflicts -> `negation_conflict`;
- exclusivity conflict -> `scope_overstatement`.

If failure-mode mapping needs one new string check in `adjudicator.py`, keep it
small and stable.

## Partial Tensions

Return `partially_supported` for narrower evidence that still supports a weaker
version of the claim:

- claim says `all`, `every`, or `universally`;
- evidence says `most`, `many`, `some`, `subset`, `not all`, or `majority`.

This should block `supported` while avoiding a hard contradiction unless the
evidence explicitly says the universal claim is false.

## Conservative Guards

All checks should require material context overlap after removing the trigger
words. Descriptor conflicts should only fire when the compared descriptor is
attached to the same broad noun or surrounding claim context, such as
`architecture`, `reinforcement learning`, `data`, `tasks`, or `experiments`.

Do not try to solve arbitrary antonymy. The lens is a curated safety layer for
recurring academic writing failures.

## Benchmarks

Add edge cases for:

- `only` vs `one of three`;
- `all` vs `most`;
- SOTA negation;
- `requires no labeled data` vs `requires labeled data`;
- transformer vs convolutional architecture;
- offline vs online reinforcement learning;
- significant vs not statistically significant.

The edge benchmark total becomes 40. Target scores remain:

- `accuracy = 1.0`;
- `false_supported_rate = 0.0`;
- no regressions on primary or hallucination draft evals.

## Follow-Up

After this slice, the next robustness step should move beyond handcrafted
heuristics into external held-out benchmark adapters, starting with SciFact or
SciFact-Open for scientific claim verification.
