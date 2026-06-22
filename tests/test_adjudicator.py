from citeproof.adjudicator import adjudicate_evidence, adjudicate_judgments
from citeproof.models import EvidenceJudgment, FactInspection, Label


def test_fact_contradiction_overrides_nli_support() -> None:
    result = adjudicate_judgments(
        heuristic=EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.75, "lexical overlap"),
        facts=FactInspection(Label.CONTRADICTED, ("Year conflict",)),
        nli=EvidenceJudgment(Label.SUPPORTED, 0.99, "entailment"),
    )

    assert result.label == Label.CONTRADICTED
    assert "Year conflict" in result.reason


def test_supported_requires_heuristic_and_nli_support() -> None:
    result = adjudicate_judgments(
        heuristic=EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.72, "partial lexical support"),
        facts=FactInspection(None, ()),
        nli=EvidenceJudgment(Label.SUPPORTED, 0.98, "entailment"),
    )

    assert result.label == Label.PARTIALLY_SUPPORTED


def test_nli_contradiction_without_retrieval_support_becomes_uncertain() -> None:
    result = adjudicate_judgments(
        heuristic=EvidenceJudgment(Label.UNSUPPORTED, 0.25, "too little overlap"),
        facts=FactInspection(None, ()),
        nli=EvidenceJudgment(Label.CONTRADICTED, 0.99, "contradiction"),
    )

    assert result.label == Label.UNCERTAIN


def test_adjudicate_evidence_uses_fact_lenses() -> None:
    result = adjudicate_evidence(
        "The model was trained on 6000 examples with 4 GPUs.",
        "The model was trained on 6000 examples with 1 GPU.",
    )

    assert result.label == Label.CONTRADICTED
