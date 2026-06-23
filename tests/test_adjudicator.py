from citeproof.adjudicator import adjudicate_evidence, adjudicate_judgments
from citeproof.models import EvidenceJudgment, FactInspection, FailureMode, Label


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


def test_atom_missing_support_caps_parent_at_partial() -> None:
    result = adjudicate_evidence(
        "WildChat contains 1M conversations and provides medical expert annotations.",
        "WildChat contains 1M ChatGPT interaction logs spanning diverse topics and languages.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED


def test_mixed_supported_and_contradicted_atoms_become_partial() -> None:
    result = adjudicate_evidence(
        "POMDP-based spoken dialog systems provide robustness to recognition errors "
        "and solve exact policy learning tractably for real-world dialogs.",
        "The belief state provides an explicit representation of uncertainty leading "
        "to systems that are much more robust to speech recognition errors. Exact "
        "policy learning for POMDPs is intractable, hence efficient approximation "
        "techniques must be used.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert result.failure_mode == FailureMode.MISSING_ATOM_SUPPORT


def test_all_supported_atoms_can_support_parent() -> None:
    result = adjudicate_evidence(
        "WildChat contains 1M conversations and spans diverse languages.",
        "WildChat contains 1M ChatGPT interaction logs and covers multiple languages.",
    )

    assert result.label == Label.SUPPORTED
