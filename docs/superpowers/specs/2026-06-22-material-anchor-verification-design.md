# Material Anchor Verification Design

## Context

CiteProof already checks citation keys, source resolution, rationale retrieval,
numeric/year/unit conflicts, scope overstatement, hedging, negation, optional
NLI disagreement, and lower-ranked contradictions. The next false-supported
risk is still deterministic: a retrieved span can strongly overlap with a claim
while naming a different method, dataset, benchmark, model, or citation-critical
object.

Example current failure:

```text
Claim:    LoRA improves accuracy over full fine-tuning on GLUE.
Evidence: Prefix tuning improves accuracy over full fine-tuning on GLUE.
Current:  supported
Wanted:   contradicted or at least not supported, with entity_conflict
```

This follows the direction of scientific claim-verification and grounded
factuality work: SciFact-style systems require evidence rationales, MiniCheck
uses challenging fact-level synthetic errors, and RefChecker uses fine-grained
claim units. For CiteProof, the immediate reliable step is a deterministic
material-anchor gate before we trust a span as support.

## Approaches Considered

### 1. Deterministic Material-Anchor Gate (Recommended)

Extract high-signal anchors from the claim, such as acronyms, CamelCase model
names, method names, dataset names, and short capitalized technical terms.
Before `SUPPORTED` is allowed, require those anchors to appear in evidence. If
the evidence has strong predicate overlap but misses a material claim anchor,
return `CONTRADICTED` with `ENTITY_CONFLICT`.

Trade-off: This is not full entity linking, but it is fast, offline,
deterministic, auditable, and directly targets a known false-supported class.

### 2. Local Fact-Checker Ensemble

Add MiniCheck or another factuality checker alongside the existing NLI verifier,
then require heuristic, fact lenses, NLI, and fact-checker agreement for
`SUPPORTED`.

Trade-off: Better semantic coverage, but it adds download/runtime cost and
requires calibration. It should come after deterministic gates because the
product must be trustworthy even in offline or no-model modes.

### 3. Semantic Retrieval/Reranking

Add embedding search or cross-encoder reranking to find better evidence spans,
then keep the current adjudicator.

Trade-off: Better recall, but it does not solve swapped-entity support by
itself. Stronger retrieval can even surface more topically similar wrong spans
unless adjudication is stricter.

## Design

Add material-anchor inspection to the deterministic fact-lens layer. It should
run before heuristic support is accepted and should share the existing
`ENTITY_CONFLICT` failure mode.

The extractor should prefer precision over recall:

- Keep acronym-like tokens with at least two uppercase letters, such as `LoRA`,
  `GLUE`, `PPO`, `BERTScore`, `Qwen2.5`, and `SQuAD`.
- Keep CamelCase or mixed alphanumeric technical names, such as `WildChat`,
  `GPT-4`, or `Qwen2.5`.
- Keep short capitalized multi-token names when they look like technical
  entities, but avoid generic sentence-start words such as `The`, `Method`, and
  `Figure`.
- Ignore single-letter placeholders like `X` and `Y` so existing generic tests
  keep working.

The inspection result should be conservative:

- If a claim has no material anchors, do nothing.
- If evidence contains every claim anchor, do nothing.
- If evidence has too little lexical overlap, leave the result to source-silence
  handling rather than calling an entity conflict.
- If evidence has high predicate overlap but misses one or more claim anchors,
  return `CONTRADICTED` with an entity-conflict finding.

The adjudicator should map entity-conflict findings to
`FailureMode.ENTITY_CONFLICT` and the review action should tell the writer to
fix the entity or cite a matching source.

## Data Flow

1. `adjudicate_evidence` calls `inspect_facts(claim, evidence)`.
2. `inspect_facts` extracts claim anchors and evidence anchors/text.
3. If a material claim anchor is missing from otherwise related evidence,
   `inspect_facts` returns `FactInspection(Label.CONTRADICTED, (...))`.
4. `adjudicate_judgments` converts that fact conflict into an
   `EvidenceJudgment(Label.CONTRADICTED, ..., FailureMode.ENTITY_CONFLICT)`.
5. `verify_claim` records the contradiction candidate in the atom trace, where
   it blocks `supported` even if another rationale candidate supports the claim.

## Tests

Add deterministic tests for:

- Method swap: `LoRA` claim vs `Prefix tuning` evidence is not supported and
  has `ENTITY_CONFLICT`.
- Dataset swap: `GLUE` claim vs `SQuAD` evidence is not supported and has
  `ENTITY_CONFLICT`.
- Placeholder names: `Method X` cases remain valid and are not treated as
  entity conflicts.
- End-to-end verifier trace: swapped-anchor rationale returns
  `contradicted`, `entity_conflict`, and a non-`none` review action.
- Edge benchmark row: a material-anchor swap contributes to the local
  false-supported guard.

## Non-Goals

- No new ML model dependency in this slice.
- No external entity linker.
- No dense retrieval or reranking changes.
- No UI/editor work.
- No claim-triplet extractor yet; this design only handles high-precision
  anchors that can be checked deterministically.

## Open Follow-Ups

- Add a calibrated MiniCheck-style local fact checker as an optional verifier.
- Add semantic retrieval/reranking once the adjudicator has stricter gates.
- Add aggregate failure-mode accuracy metrics to `citeproof eval`.
- Expose full atom/rationale diagnostics in `eval-draft --details-output`.
