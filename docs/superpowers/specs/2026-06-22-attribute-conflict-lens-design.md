# Attribute Conflict Lens Design

## Goal

Reduce false `supported` labels for claims that share high lexical overlap with
evidence but swap a controlled academic attribute, such as task, data type,
evaluation split, language, optimizer, or public availability.

These are high-risk academic-integrity failures because the text looks almost
identical while the cited source supports a different experimental fact.

## Brainstormed Approaches

1. Add an ML/NLI ensemble for all borderline cases.
   This may improve coverage, but it is harder to audit and can be unstable
   across models or hardware.

2. Add semantic retrieval/reranking before evidence judgment.
   This helps source selection, but it does not directly block a high-overlap
   wrong sentence once retrieved.

3. Add a deterministic controlled attribute-conflict lens.
   This is narrower but auditable, testable, and directly attacks the current
   false-supported cluster. This is the selected approach.

## Scope

The lens detects contradictions only when both sides mention competing
values from the same controlled group and enough non-attribute context overlaps.

Initial groups:

- data modality: `images`, `text`, `audio`, `video`, `tabular`
- task: `summarization`, `translation`, `classification`, `segmentation`, `retrieval`
- evaluation split: `train`, `training`, `validation`, `dev`, `test`
- language: `English`, `German`, `French`, `Spanish`, `Chinese`
- optimizer: `Adam`, `AdamW`, `SGD`, `RMSProp`
- availability: `publicly available`, `private`, `proprietary`, `not publicly available`

Out of scope for this slice:

- arbitrary attribute extraction
- learned contradiction scoring
- broad synonym expansion beyond explicit controlled values

## Data Flow

`inspect_attribute_conflicts(claim, evidence)` returns deterministic findings.
`fact_lenses.inspect_facts` appends these to hard findings, which makes the
final judgment `contradicted`. `adjudicator` maps attribute findings to stable
failure modes:

- task/modality/split/language/optimizer conflicts: `entity_conflict`
- availability conflicts: `negation_conflict`

## Error Handling

The lens is conservative:

- require at least one shared non-attribute context token
- ignore conflicts when the evidence is clearly about a different subject
- prefer missing a contradiction over falsely contradicting unrelated context

## Testing

Add red-to-green tests for current false-supported probes:

- dataset contains `images` vs `text samples`
- improves `summarization` vs `translation`
- evaluated on `test set` vs `validation set`
- evaluates `German` vs `English`
- uses `Adam` vs `SGD`
- `publicly available` vs `not publicly available`

Add boundary tests where conflicting terms occur in different contexts and must
not contradict.

## Success Check

The focused tests pass, the edge-case eval grows from 40 to 46 cases, and all
new cases avoid false `supported` labels while the full suite, ruff, and CI stay
green.
