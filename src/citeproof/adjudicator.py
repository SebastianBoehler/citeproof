"""Conservative verifier adjudication."""

from __future__ import annotations

from collections.abc import Callable

from citeproof.entailment import judge_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import EvidenceJudgment, FactInspection, Label

Judge = Callable[[str, str], EvidenceJudgment]


def adjudicate_evidence(
    claim: str,
    evidence: str,
    judge: Judge = judge_evidence,
) -> EvidenceJudgment:
    """Judge one evidence span with deterministic gates before optional NLI."""

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
