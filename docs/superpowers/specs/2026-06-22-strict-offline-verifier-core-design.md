# Strict Offline Verifier Core Design

## Purpose

CiteProof should move from a useful conservative scaffold toward a verifier that
an academic writer or paper-writing agent can trust during drafting. The target
is not a mathematically perfect verifier. The target is a system that makes
false approvals rare, makes uncertainty explicit, and produces enough evidence
trace data for a human or agent to repair the draft.

The next phase should focus on the offline verifier core before editor, SaaS,
open-domain search, or repair-loop features. If the offline verifier cannot
reliably decide whether a local cited source supports a claim, broader agentic
or web-search workflows will only add more places to over-trust weak evidence.

## Current State

The current implementation already has:

- citation-bearing claim parsing
- local source loading with PDF page preservation
- BibTeX key and metadata checks
- context-preserving claim atoms
- deterministic fact lenses for selected numeric, date, scope, hedging, and
  negation risks
- conservative adjudication
- optional local NLI
- direct and draft-level eval runners with `false_supported_rate`
- HALLMARK-compatible bibliography prediction
- a small adversarial edge-case benchmark

Current local benchmark scores are strong but not yet persuasive for academic
integrity use because the benchmark is small and partly hand-shaped around known
failure modes. The next phase must improve both verifier quality and evaluation
coverage.

## Design Principles

- `supported` is a high-precision label. It should be hard to earn.
- A source being real does not mean the cited claim is supported by that source.
- Retrieval quality and rationale precision are the main bottlenecks.
- NLI and LLM judges are audit signals, not authority to bypass retrieval,
  rationale, metadata, or deterministic contradiction gates.
- Every final label should be explainable as a sequence of gate outcomes.
- Benchmark design is product design. A verifier without adversarial evals is
  not trustworthy enough for academic integrity workflows.
- The system should be useful when it is conservative: a `partial`,
  `unsupported`, or `uncertain` label must include enough detail for repair.

## Recommended Approach

Implement the strict offline verifier core in this order:

1. Trust trace and richer metrics.
2. Hybrid retrieval over sentence/window evidence.
3. Rationale selection and atom-level coverage.
4. Model calibration for NLI, rerankers, and optional LLM audit.
5. Agentic repair suggestions after the verifier contract is reliable.

This follows the pattern suggested by scientific claim-verification and
citation-evaluation work: SciFact separates evidence retrieval, rationale
selection, and support/refute labels; FActScore motivates atom-level factual
coverage; ALCE shows citation support quality remains a major failure mode for
LLM-generated cited text; BEIR and ColBERT support improving retrieval and
reranking rather than relying on one classifier.

## Verification Pipeline

The strict verifier should execute these gates for each citation-bearing claim:

1. **Citation/source gate**
   Confirm cited keys exist, bibliography entries are plausible, and local
   sources resolve to the cited keys.

2. **Evidence retrieval gate**
   Retrieve candidate evidence from the cited source using full-claim and
   atom-level queries. Retrieval must remain citation-scoped.

3. **Rationale gate**
   Select the exact sentence or compact sentence window that supports,
   contradicts, or fails to support each atom. Whole chunks are too coarse for
   trustworthy audit output.

4. **Coverage gate**
   Require every atomic claim to have adequate rationale coverage before the
   parent claim can be `supported`.

5. **Contradiction gate**
   Run deterministic checks for numbers, years, units, negation, comparison
   direction, entities, acronyms, scope, hedging, datasets, and model names.

6. **Model-judge gate**
   Run NLI, rerankers, or LLM auditors only on retrieved rationale spans. Models
   can downgrade or flag claims freely. Promoting to `supported` still requires
   the earlier gates to pass.

7. **Calibration gate**
   Emit label, confidence, gate outcomes, failure mode, and metrics fields. Do
   not hide uncertainty behind a single label.

## Trace Data Model

Add explicit internal trace objects so the verifier can explain and score its
decisions.

`EvidenceCandidate`

- source id
- citation key
- page and section when available
- sentence/window text
- lexical score
- semantic score when available
- rerank score when available
- retrieval rank and retrieval method

`RationaleSpan`

- source id
- citation key
- page and section when available
- exact selected text
- character or sentence index when available
- relation candidate: support, contradict, neutral, undetermined

`AtomVerification`

- atomic claim text
- original claim context
- rationale spans
- deterministic fact findings
- heuristic judgment
- optional NLI judgment
- optional auditor judgment
- label
- confidence
- failure mode

`ClaimVerificationTrace`

- parent claim
- citation keys
- source gate status
- atom verifications
- final label
- final confidence
- final failure mode
- review action suggestion

The public JSON output should keep the current `VerificationResult` shape stable
where possible and add an optional `trace` field. Markdown output can summarize
the trace without dumping every candidate.

## Failure Modes

Use stable failure-mode strings so benchmarks, repair loops, and UI clients can
reason over verifier output:

- `missing_bibliography_key`
- `metadata_not_verified`
- `source_not_resolved`
- `weak_retrieval`
- `no_rationale_span`
- `missing_atom_support`
- `numeric_conflict`
- `year_conflict`
- `unit_conflict`
- `entity_conflict`
- `negation_conflict`
- `comparison_direction_conflict`
- `scope_overstatement`
- `hedged_evidence`
- `source_silence`
- `model_disagreement`
- `conflicting_sources`

These failure modes should not replace the label; they explain why the label was
chosen and what a writer or agent should fix.

## Benchmark Strategy

The benchmark should be layered.

**Tier 1: Fast Regression Set**

Small committed JSONL cases run in CI:

- fake citation key
- real source but wrong citation
- right paper but unsupported claim
- numeric conflict
- year conflict
- unit conflict
- metric swap
- entity swap
- scope overstatement
- hedged evidence
- compound claim with one unsupported atom
- paraphrase support
- source silence

**Tier 2: Adversarial Local Corpus**

Generate a larger benchmark from real local papers. For each source paper, keep
some supported claims and create controlled mutations:

- swap numbers, datasets, metrics, years, methods, and model names
- append unsupported `and` clauses
- overgeneralize from `some` or `one setting` to `all`
- flip positive results into negative claims or vice versa
- cite a topically similar but wrong paper
- cite a real paper that is silent on the mutated claim
- move support to a neighboring paragraph to test retrieval robustness

**Tier 3: External Benchmarks**

- SciFact or SciFact-Open for scientific support/refute behavior.
- ALCE-inspired citation precision and recall metrics for cited long-form text.
- HALLMARK for bibliography/reference hallucination only.
- Optional AVeriTeC-style evidence-chain scoring once question decomposition is
  needed for complex claims.

## Metrics

Primary:

- `false_supported_rate`, target `0.0`.

Secondary:

- `supported_precision`
- `supported_recall`
- `unsupported_recall`
- `contradiction_recall`
- `evidence_recall_at_k`
- `rationale_precision`
- `atom_coverage_rate`
- `manual_review_rate`
- `macro_f1`
- calibration error for confidence bins

`manual_review_rate` is important because an overly conservative verifier can
avoid false approvals while becoming too noisy to use. Optimization should keep
false approvals at zero first, then reduce unnecessary `uncertain` and
`partially_supported` outcomes.

## Retrieval And ML Options

**Option A: Hybrid retriever plus reranker**

- BM25-style lexical scoring over sentence/window chunks.
- Optional embedding retriever for paraphrases.
- Optional cross-encoder reranker for candidate rationale spans.
- Retrieve by parent claim and each atom.

This is the recommended first implementation direction because current lexical
retrieval is the most obvious bottleneck.

**Option B: Scientific NLI ensemble**

- Keep the current local DeBERTa NLI path.
- Add SciFact-trained verifier models if available and practical.
- Calibrate thresholds against local adversarial benchmarks.
- Let contradiction predictions flag review aggressively, but require strong
  retrieval and rationale context before accepting them.

This is useful after retrieval is stronger. Current local NLI already preserved
zero false-supported on the edge set, but lowered accuracy by over-calling one
partial case and one source-silence case.

**Option C: LLM auditor**

- Input only atomic claim plus selected rationale spans.
- Output structured JSON with supported atoms, missing atoms, contradictions,
  uncertainty reason, and cited evidence indexes.
- No web search and no outside knowledge in strict offline mode.
- Allowed to downgrade or flag. Promotion to `supported` still requires all
  hard gates.

This can handle nuanced language in Phase 4, but should not be the first line
of defense.

## Trust Policy

- If retrieval fails, never return `supported`.
- If citation keys or sources are missing, return `uncertain`.
- If evidence is topically related but silent about an atom, return
  `unsupported` or `partially_supported`.
- If any atom is missing support, cap the parent label at
  `partially_supported`.
- If deterministic facts conflict, return `contradicted` even when NLI predicts
  entailment.
- If model signals disagree with hard gates, surface `model_disagreement`.
- If sources conflict, return `contradicted` or `uncertain` with both spans.
- If evidence is hedged and the claim is absolute, return
  `partially_supported`.
- If evidence supports only a narrower scope, return `partially_supported`.

The verifier should feel slightly annoying during writing. That is acceptable
for academic integrity because the product should avoid silent false approval.

## Implementation Phases

**Phase 1: Trust trace and metrics**

- Add trace data models.
- Add stable failure modes.
- Add richer JSON details.
- Add secondary metrics.
- Expand adversarial local benchmark.

**Phase 2: Retrieval upgrade**

- Add sentence/window candidate extraction.
- Add BM25-style scorer.
- Retrieve per atom and parent claim.
- Preserve page and section provenance.
- Add optional semantic retrieval adapter behind an explicit extra.

**Phase 3: Rationale coverage**

- Select exact rationale spans.
- Score coverage per atom.
- Require atom rationale coverage for `supported`.
- Add rationale diagnostics to reports.

**Phase 4: Model calibration**

- Compare heuristic, local NLI, optional reranker, and optional LLM auditor.
- Store score reports.
- Tune thresholds only against false-supported, review-rate, and contradiction
  recall tradeoffs.

**Phase 5: Repair loop**

- Emit structured repair actions:
  - rewrite claim narrower
  - source does not support atom
  - citation key missing
  - numeric conflict
  - stronger source needed
- Require verification rerun after every repair.

## Out Of Scope For This Phase

- SaaS/editor UI.
- Open-domain web source search.
- Automatic citation insertion without verifier rerun.
- Treating LLM output as evidence.
- Training a custom model before the benchmark is stronger.

## Acceptance Criteria

- The existing test suite remains green.
- CI still runs tests and sample evals across supported Python versions.
- The fast regression benchmark includes the new adversarial categories.
- Evaluation reports include the primary metric and secondary metrics listed
  above.
- Every non-`supported` result can expose a stable failure mode.
- Every `supported` result can expose source, rationale, atom coverage, and
  hard-gate status.
- Optional NLI can lower confidence or flag disagreement without bypassing
  deterministic contradiction gates.

## References

- [SciFact: Fact or Fiction: Verifying Scientific Claims](https://arxiv.org/abs/2004.14974)
- [SciFact-Open: Towards open-domain scientific claim verification](https://arxiv.org/abs/2210.13777)
- [ALCE: Enabling Large Language Models to Generate Text with Citations](https://arxiv.org/abs/2305.14627)
- [FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation](https://arxiv.org/abs/2305.14251)
- [BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663)
- [ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT](https://arxiv.org/abs/2004.12832)
