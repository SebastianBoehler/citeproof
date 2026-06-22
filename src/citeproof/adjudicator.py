"""Conservative verifier adjudication."""

from __future__ import annotations

from collections.abc import Callable

from citeproof.claims import atomize_claim
from citeproof.entailment import judge_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import Claim, EvidenceJudgment, FactInspection, Label

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
        return EvidenceJudgment(Label.CONTRADICTED, 0.9, "; ".join(facts.findings))
    if facts.label == Label.PARTIALLY_SUPPORTED and heuristic.label != Label.UNSUPPORTED:
        return EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.72, "; ".join(facts.findings))
    if nli and nli.label == Label.CONTRADICTED and heuristic.label == Label.UNSUPPORTED:
        return EvidenceJudgment(
            Label.UNCERTAIN,
            min(nli.confidence, 0.65),
            "NLI predicts contradiction, but retrieved evidence has weak claim overlap.",
        )
    if nli and nli.label == Label.CONTRADICTED:
        return EvidenceJudgment(Label.CONTRADICTED, nli.confidence, nli.reason)
    if heuristic.label == Label.SUPPORTED and (nli is None or nli.label == Label.SUPPORTED):
        confidence = min(heuristic.confidence, nli.confidence if nli else heuristic.confidence)
        return EvidenceJudgment(Label.SUPPORTED, confidence, "Verifier gates agree.")
    if heuristic.label == Label.SUPPORTED and nli and nli.label != Label.SUPPORTED:
        return EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.68, "NLI did not confirm full support.")
    return heuristic


def _combine_atom_judgments(judgments: list[EvidenceJudgment]) -> EvidenceJudgment:
    if not judgments:
        return EvidenceJudgment(Label.UNCERTAIN, 0.2, "No atomic claims were produced.")
    labels = [judgment.label for judgment in judgments]
    if Label.CONTRADICTED in labels:
        strongest = max(
            (judgment for judgment in judgments if judgment.label == Label.CONTRADICTED),
            key=lambda judgment: judgment.confidence,
        )
        return strongest
    if all(label == Label.SUPPORTED for label in labels):
        confidence = min(judgment.confidence for judgment in judgments)
        return EvidenceJudgment(Label.SUPPORTED, confidence, "All atomic subclaims are supported.")
    if any(label in {Label.SUPPORTED, Label.PARTIALLY_SUPPORTED} for label in labels):
        return EvidenceJudgment(
            Label.PARTIALLY_SUPPORTED,
            0.66,
            "Only some atomic subclaims are supported by the retrieved evidence.",
        )
    if Label.UNCERTAIN in labels:
        return EvidenceJudgment(Label.UNCERTAIN, 0.45, "Atomic subclaims could not be verified.")
    return EvidenceJudgment(Label.UNSUPPORTED, 0.35, "No atomic subclaim is supported.")
