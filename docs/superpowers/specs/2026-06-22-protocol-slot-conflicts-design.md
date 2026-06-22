# Protocol Slot Conflicts Design

## Context

CiteProof already saturates the committed curated suite, but adversarial probes
still found high-overlap claims that become unsafe `supported` labels when the
claim and evidence swap protocol slots:

- comparator/control: placebo vs usual care, active control vs placebo control
- timing: 30-day vs 90-day follow-up
- dosage: 10 mg vs 20 mg
- schedule: daily vs weekly dosing

These cases matter for academic integrity because they look lexically aligned
while changing the claim's factual meaning.

## Brainstormed Approaches

1. Deterministic protocol-slot hardening. Add controlled slot checks for
   comparators, follow-up timing, dose units, and dosing frequency. This is the
   recommended next step because it directly blocks known false-supported
   cases, is explainable in traces, and keeps `supported` conservative.
2. ML/NLI ensemble calibration. Add more model voters and abstain on
   disagreement. This can improve recall on unseen phrasing, but it needs
   calibration data and adds runtime/model variance.
3. Adversarial benchmark generation. Generate mutation pairs from papers and
   score verifier regressions. This improves measurement, but by itself does not
   remove the current unsafe labels.

## Selected Design

Implement deterministic protocol-slot hardening now. Extend the existing
controlled lenses rather than adding a broad biomedical parser.

The change has two parts:

- Extend quantity parsing to include duration and dose units used in academic
  claims: days, weeks, months, years, hours, minutes, seconds, mg, g, kg, ml,
  and doses.
- Extend protocol conflict checks with controlled slots:
  - comparator/control values: placebo, usual care, standard care, active
    control, sham, waitlist
  - dosing frequency values: daily, twice daily, weekly, monthly

The verifier should classify mismatches as `contradicted`, with stable failure
mode routing to `numeric_conflict` for numeric timing/dose conflicts and
`entity_conflict` for comparator/frequency protocol conflicts.

## Data Flow

1. `adjudicate_evidence` runs the existing heuristic and deterministic fact
   lenses.
2. `inspect_facts` calls quantity, protocol, and other lenses.
3. Quantity mismatches with the same normalized unit become numeric conflicts.
4. Protocol-slot mismatches with enough non-slot context become hard conflicts.
5. Contradictions outrank support in the final adjudication and rationale trace.

## Error Handling

The implementation stays conservative:

- Do not infer open-ended clinical semantics beyond controlled terms.
- Do not mark low-overlap examples as contradictions from slot words alone.
- Do not add fallbacks, mocks, or optional configurability.
- Prefer `partially_supported` or `unsupported` from existing gates when the new
  lens does not have enough context.

## Testing

Add focused tests proving the current false-supported probe cases become
contradictions:

- comparator/control conflicts are not supported
- duration and dose quantity conflicts are numeric conflicts
- dosing frequency conflicts are protocol conflicts
- matching comparator, duration, dose, and frequency examples remain clean

Add edge-eval rows for at least comparator, duration, dose, and frequency
conflicts, then update the evaluation documentation totals.

## Success Check

The slice is complete when:

- focused protocol/quantity tests pass
- edge eval remains fully passing with the new rows
- full pytest, eval-suite, and ruff pass
- all touched source/test/docs files stay below 300 lines
- the changes are committed and pushed to `main`
