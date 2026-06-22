# Statistical Reporting Conflicts Design

## Goal

Reduce false `supported` labels for high-overlap statistical and reporting
claims where the cited evidence reports a different statistical property.

Fresh probes on current `main` found false support for:

- confidence intervals that exclude zero vs include zero
- macro-F1 vs micro-F1
- median vs mean latency
- standard deviation vs standard error
- paired vs unpaired tests
- one-tailed vs two-tailed tests
- parametric vs nonparametric tests

These are high-risk in academic writing because they can change the meaning of
the result while preserving most of the wording.

## Options Considered

1. Extend `technical_property_lens`.
   This would work mechanically, but statistical reporting has enough specific
   terminology to deserve its own small module.

2. Add a focused `statistical_reporting_lens`.
   This keeps statistical claim checks auditable and isolated. This is selected.

3. Rely on NLI.
   NLI may help later, but these controlled contrasts are deterministic enough
   to test directly and do not depend on model variance.

## Scope

Create `src/citeproof/statistical_lens.py` with controlled groups:

- confidence interval relation: `includes zero`, `excludes zero`
- F1 averaging: `macro-F1`, `micro-F1`
- summary statistic: `mean`, `median`
- uncertainty statistic: `standard deviation`, `standard error`
- pairedness: `paired`, `unpaired`
- tail count: `one-tailed`, `two-tailed`
- test family: `parametric`, `nonparametric`

The lens remains conservative:

- conflicts require disjoint values from the same group
- conflicts require shared non-statistical context
- evidence mentioning both values does not create a hard contradiction
- unrelated mentions of statistical terms do not create hard contradictions

## Data Flow

`inspect_statistical_conflicts(claim, evidence)` returns hard conflict findings.
`fact_lenses.inspect_facts` appends these to hard findings. `adjudicator` maps
the resulting finding labels to `entity_conflict`, since the current
failure-mode enum has no separate statistical-reporting category.

## Testing

Add direct and end-to-end tests for:

- CI excludes zero vs CI includes zero
- macro-F1 vs micro-F1
- median latency vs mean latency
- standard deviation vs standard error
- paired bootstrap vs unpaired bootstrap
- one-tailed test vs two-tailed test
- parametric test vs nonparametric test

Add boundary tests for mixed-value evidence and different-context mentions.

## Success Check

The edge-case benchmark grows from 56 to 63 cases. The full local suite, ruff,
sample eval, edge eval, hallucination eval, and GitHub CI all pass with
`false_supported_rate = 0.0`.
