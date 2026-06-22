# Conservative Hybrid Verifier Design

## Purpose

CiteProof should help academic writers and agents verify whether a draft claim is
actually supported by the cited source. The product should be useful during
writing, not only after submission: an agent can draft a paper, CiteProof can
flag unsupported or contradictory claims, and the agent can revise or fetch
better sources.

The primary safety metric is false-supported rate. A false `supported` label is
the highest-risk error because it can make an unsupported or hallucinated
argument look verified. CiteProof should prefer `partially_supported`,
`uncertain`, or `unsupported` over `supported` whenever evidence is incomplete,
weak, mismatched, or disputed by another verifier signal.

## Design Principles

- `supported` is a high-confidence label, not a default positive match.
- Bibliography reality and claim support are separate problems.
- NLI is a semantic evidence judge, not a fact checker by itself.
- Deterministic conflicts for numbers, dates, units, entities, scope, and
  modality should override generic semantic similarity.
- Every output should be auditable: source key, page, evidence span, score,
  label, and reason.
- Evaluation should include hard negative cases, not only happy-path examples.

## Label Policy

`supported` requires all of these:

- The citation key exists in the bibliography.
- The BibTeX entry is externally verified or explicitly marked local-only.
- A source file maps to the cited key.
- Retrieval finds evidence from the cited source, not from an unrelated source.
- Every atomic subclaim is covered by evidence.
- No deterministic conflict is detected.
- NLI, when enabled, predicts entailment above the configured threshold.

`partially_supported` means at least one subclaim is supported, but coverage is
incomplete, narrower, hedged, or missing details.

`contradicted` means a relevant source span conflicts with the claim. Numeric,
date, unit, entity, negation, or modality conflicts can trigger this directly.
NLI contradiction is only accepted after retrieval confirms the evidence is about
the same cited source and subject.

`unsupported` means the cited source is present, but retrieved evidence does not
support the claim.

`uncertain` means verification cannot safely decide: missing source, unverified
metadata, weak retrieval, parser ambiguity, model disagreement, provider errors,
or unsupported document format.

## Architecture

The verifier should become a staged adjudication pipeline:

1. **Claim Atomizer**
   Splits citation-bearing text into atomic claims. It starts with explicit
   citation clauses and adds targeted splitting for conjunctions, numeric
   clauses, dataset descriptions, and method descriptions.

2. **Bibliography Gate**
   Checks citation keys, required fields, duplicate references, and external
   metadata through providers such as OpenAlex, arXiv, Crossref, and Semantic
   Scholar. HALLMARK remains a bibliography-hallucination benchmark only.

3. **Source Resolver**
   Maps source files to BibTeX keys, preserves PDF page boundaries, and records
   source trust. A source that does not map to a cited key cannot verify a claim.

4. **Evidence Retriever**
   Retrieves page-level and paragraph-level evidence from cited sources. The
   initial lexical retriever should be supplemented by a semantic retriever, but
   semantic retrieval must still respect citation scope.

5. **Deterministic Fact Lenses**
   Extracts and compares high-risk facts:
   numbers, dates, units, named entities, acronyms, dataset sizes, model names,
   method names, negation, hedging, and scope words.

6. **NLI Judge**
   Runs local transformers NLI on relevant evidence spans. The default model is
   `cross-encoder/nli-deberta-v3-small`, matching the token uncertainty project.
   NLI output is one signal in adjudication, not the sole label source.

7. **Conservative Adjudicator**
   Combines retrieval, deterministic lenses, metadata status, and NLI. It should
   explicitly explain why a claim was not marked `supported`.

## Data Flow

```text
draft + bib + sources
  -> parse cited clauses
  -> atomize claims
  -> verify bibliography metadata
  -> resolve trusted source files
  -> retrieve cited evidence
  -> run deterministic fact lenses
  -> run optional NLI
  -> adjudicate label
  -> output evidence ledger and review queue
```

## Evaluation Strategy

Primary metric:

- `false_supported_rate`, target `0.0` on every local benchmark.

Secondary metrics:

- contradiction recall
- unsupported precision
- `uncertain` coverage rate
- macro-F1
- citation metadata precision
- source-mapping precision

Benchmark layers:

- Existing direct claim-support JSONL.
- Existing hallucination draft eval with and without BibTeX gating.
- Edge-case eval for paraphrase, multi-number conflicts, date conflicts,
  wrong-source evidence, hedging, scope, and entity swaps.
- HALLMARK for BibTeX/reference hallucination only.
- SciFact or SciFact-Open adapters for scientific claim support/refute behavior.
- ALCE-style citation-quality checks for long-form cited writing.
- Manually labeled claims from the user's thesis paper.

## Expected Failure Modes

- NLI can confidently call irrelevant evidence contradictory.
- Lexical retrieval misses paraphrased support.
- Date and year metadata can differ between preprint and publication versions.
- A source can support a narrower claim than the draft states.
- A real citation can be used for an unsupported argument.
- A fabricated local source can satisfy retrieval unless bibliography and
  metadata gates are enforced.

The adjudicator should treat these as review cases unless multiple independent
signals support the same positive conclusion.

## Implementation Boundaries

The next implementation should be scoped to the CLI/library verifier, not a SaaS
or editor interface. The interface can come later once the verification contract
is trustworthy.

The first implementation phase should add:

- atomic claim structures
- deterministic fact lenses
- conservative adjudicator
- richer eval details
- expanded edge-case tests

The second phase should add:

- SciFact/SciFact-Open adapter
- HALLMARK scoring integration
- semantic retrieval experiments
- threshold calibration reports

The third phase should add:

- agent repair loop suggestions
- editor or MCP workflow improvements
- optional LLM adjudicator for explanations and source-repair suggestions

## References

- SciFact: https://arxiv.org/abs/2004.14974
- ALCE: https://arxiv.org/abs/2305.14627
- FActScore: https://arxiv.org/abs/2305.14251
- HALLMARK: https://github.com/rpatrik96/hallmark
