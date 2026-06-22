"""Conservative verifier adjudication."""

from __future__ import annotations

from collections.abc import Callable

from citeproof.claims import atomize_claim
from citeproof.entailment import judge_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import Claim, EvidenceJudgment, FactInspection, FailureMode, Label

Judge = Callable[[str, str], EvidenceJudgment]


def adjudicate_evidence(
    claim: str,
    evidence: str,
    judge: Judge = judge_evidence,
) -> EvidenceJudgment:
    """Judge one evidence span with deterministic gates before optional NLI."""

    group = atomize_claim(Claim(claim))
    if len(group.atoms) > 1:
        return _combine_atom_judgments(
            [_adjudicate_single(atom.text, evidence, judge) for atom in group.atoms]
        )
    return _adjudicate_single(claim, evidence, judge)


def _adjudicate_single(claim: str, evidence: str, judge: Judge) -> EvidenceJudgment:
    heuristic = judge_evidence(claim, evidence)
    facts = inspect_facts(claim, evidence)
    nli = None if judge is judge_evidence else judge(claim, evidence)
    return adjudicate_judgments(heuristic=heuristic, facts=facts, nli=nli)


def adjudicate_judgments(
    heuristic: EvidenceJudgment,
    facts: FactInspection,
    nli: EvidenceJudgment | None = None,
) -> EvidenceJudgment:
    """Combine verifier signals with false-supported avoidance as primary rule."""

    if facts.label == Label.CONTRADICTED:
        mode = _fact_failure_mode(facts)
        return EvidenceJudgment(Label.CONTRADICTED, 0.9, "; ".join(facts.findings), mode)
    if facts.label == Label.PARTIALLY_SUPPORTED and heuristic.label != Label.UNSUPPORTED:
        mode = (
            FailureMode.HEDGED_EVIDENCE
            if _has_hedge_finding(facts)
            else FailureMode.SCOPE_OVERSTATEMENT
        )
        return EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.72, "; ".join(facts.findings), mode)
    if nli and nli.label == Label.CONTRADICTED and heuristic.label == Label.UNSUPPORTED:
        return EvidenceJudgment(
            Label.UNCERTAIN,
            min(nli.confidence, 0.65),
            "NLI predicts contradiction, but retrieved evidence has weak claim overlap.",
            FailureMode.MODEL_DISAGREEMENT,
        )
    if nli and nli.label == Label.CONTRADICTED:
        return _with_failure_mode(
            EvidenceJudgment(Label.CONTRADICTED, nli.confidence, nli.reason, nli.failure_mode),
            FailureMode.MODEL_DISAGREEMENT,
        )
    if heuristic.label == Label.SUPPORTED and (nli is None or nli.label == Label.SUPPORTED):
        confidence = min(heuristic.confidence, nli.confidence if nli else heuristic.confidence)
        return EvidenceJudgment(Label.SUPPORTED, confidence, "Verifier gates agree.")
    if heuristic.label == Label.SUPPORTED and nli and nli.label != Label.SUPPORTED:
        return EvidenceJudgment(
            Label.PARTIALLY_SUPPORTED,
            0.68,
            "NLI did not confirm full support.",
            FailureMode.MODEL_DISAGREEMENT,
        )
    return _with_failure_mode(heuristic, _heuristic_failure_mode(heuristic.label))


def _fact_failure_mode(facts: FactInspection) -> FailureMode:
    text = " ".join(facts.findings).lower()
    if "year conflict" in text:
        return FailureMode.YEAR_CONFLICT
    if "numeric conflict" in text:
        return FailureMode.NUMERIC_CONFLICT
    return FailureMode.CONFLICTING_SOURCES


def _has_hedge_finding(facts: FactInspection) -> bool:
    return any("hedged" in finding.lower() or "inconclusive" in finding.lower() for finding in facts.findings)


def _with_failure_mode(judgment: EvidenceJudgment, fallback: FailureMode) -> EvidenceJudgment:
    if judgment.label == Label.SUPPORTED or judgment.failure_mode is not None:
        return judgment
    return EvidenceJudgment(judgment.label, judgment.confidence, judgment.reason, fallback)


def _heuristic_failure_mode(label: Label) -> FailureMode:
    if label == Label.CONTRADICTED:
        return FailureMode.CONFLICTING_SOURCES
    if label == Label.PARTIALLY_SUPPORTED:
        return FailureMode.SCOPE_OVERSTATEMENT
    return FailureMode.NO_RATIONALE_SPAN


def combine_atom_judgments(judgments: list[EvidenceJudgment]) -> EvidenceJudgment:
    if not judgments:
        return EvidenceJudgment(
            Label.UNCERTAIN,
            0.2,
            "No atomic claims were produced.",
            FailureMode.NO_RATIONALE_SPAN,
        )
    labels = [judgment.label for judgment in judgments]
    if Label.CONTRADICTED in labels:
        strongest = max(
            (judgment for judgment in judgments if judgment.label == Label.CONTRADICTED),
            key=lambda judgment: judgment.confidence,
        )
        return _with_failure_mode(strongest, FailureMode.CONFLICTING_SOURCES)
    if all(label == Label.SUPPORTED for label in labels):
        confidence = min(judgment.confidence for judgment in judgments)
        return EvidenceJudgment(Label.SUPPORTED, confidence, "All atomic subclaims are supported.")
    has_supported_or_partial = any(
        label in {Label.SUPPORTED, Label.PARTIALLY_SUPPORTED} for label in labels
    )
    has_unsupported_or_uncertain = any(label in {Label.UNSUPPORTED, Label.UNCERTAIN} for label in labels)
    if has_supported_or_partial and has_unsupported_or_uncertain:
        return EvidenceJudgment(
            Label.PARTIALLY_SUPPORTED,
            0.66,
            "Only some atomic subclaims are supported by the retrieved evidence.",
            FailureMode.MISSING_ATOM_SUPPORT,
        )
    if Label.PARTIALLY_SUPPORTED in labels:
        strongest = max(
            (judgment for judgment in judgments if judgment.label == Label.PARTIALLY_SUPPORTED),
            key=lambda judgment: judgment.confidence,
        )
        return _with_failure_mode(strongest, FailureMode.SCOPE_OVERSTATEMENT)
    if Label.UNCERTAIN in labels:
        return EvidenceJudgment(
            Label.UNCERTAIN,
            0.45,
            "Atomic subclaims could not be verified.",
            FailureMode.NO_RATIONALE_SPAN,
        )
    return EvidenceJudgment(
        Label.UNSUPPORTED,
        0.35,
        "No atomic subclaim is supported.",
        FailureMode.MISSING_ATOM_SUPPORT,
    )


_combine_atom_judgments = combine_atom_judgments
