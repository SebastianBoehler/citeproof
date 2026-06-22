# Academic Count Quantities Design

## Goal

Prevent false `supported` labels when a draft claim gives a study/cohort count
but the cited evidence reports a different count. Academic writing frequently
states counts for patients, participants, subjects, studies, arms, sites, and
cohorts. These are material claims, not incidental numbers.

## Current Behavior

The current quantity parser recognizes units such as samples, examples, GPUs,
dialogues, domains, and languages. It does not recognize common study-count
units. Probes show these are currently labeled `supported`:

- `The study enrolled 100 patients.` versus
  `The study enrolled 120 patients.`
- `The trial included 240 participants.` versus
  `The trial included 180 participants.`
- `The review included 12 studies.` versus
  `The review included 9 studies.`
- `The intervention used 4 treatment arms.` versus
  `The intervention used 2 treatment arms.`

## Approach

Extend `src/citeproof/quantities.py` with academic count units:

- patients
- participants
- subjects
- studies
- trials
- cohorts
- groups
- arms
- sites
- centers/centres

Do not add a new fact lens. Once these units are parsed, the existing
`fact_lenses._number_conflicts` path will produce `numeric_conflict` when claim
and evidence share the same unit but different values.

## Boundaries

This is intentionally about exact count claims. It does not infer bounds from
phrases like `approximately 100 patients`, `more than 100 patients`, or
`between 80 and 100 patients` beyond the existing bounded-quantity behavior. It
also does not try to normalize semantically different units such as patients and
participants as equivalent in this slice.

## Tests

Add tests for:

- parser recognition of the new academic units
- numeric contradiction through `inspect_facts`
- end-to-end adjudication rejecting the current false `supported` case
- matching count not flagged as a conflict

Add edge benchmark rows for patient and participant count conflicts.
