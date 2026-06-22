from citeproof.adjudicator import adjudicate_evidence
from citeproof.models import FailureMode, Label


def test_rather_than_architecture_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "GPT-3 uses a mixture-of-experts transformer architecture.",
        (
            "GPT-3 uses a dense transformer architecture rather than a "
            "mixture-of-experts architecture."
        ),
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT


def test_rather_than_objective_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "ELECTRA uses a masked language modeling objective during pretraining.",
        (
            "ELECTRA uses replaced-token detection rather than masked language "
            "modeling as its pretraining objective."
        ),
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT


def test_matching_contrastive_evidence_still_supports_positive_side() -> None:
    judgment = adjudicate_evidence(
        "GPT-3 uses a dense transformer architecture.",
        (
            "GPT-3 uses a dense transformer architecture rather than a "
            "mixture-of-experts architecture."
        ),
    )

    assert judgment.label == Label.SUPPORTED


def test_macro_micro_auroc_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The model reports macro-AUROC on the held-out test set.",
        "The model reports micro-AUROC on the held-out test set.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_bleu_unchanged_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The system improves BLEU on WMT14 English-German translation.",
        (
            "The system improves chrF on WMT14 English-German translation, "
            "but BLEU is unchanged."
        ),
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT
