from citeproof.entailment import judge_evidence
from citeproof.models import Label


def test_unchanged_outcome_is_not_supported() -> None:
    judgment = judge_evidence(
        "The method improves calibration.",
        "The method improves accuracy, but calibration is unchanged.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_mixed_effect_outcome_is_partial() -> None:
    judgment = judge_evidence(
        "The method reduces hallucinations.",
        "The method reduces hallucinations on short answers but increases hallucinations on long answers.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED


def test_protocol_conflict_is_not_supported() -> None:
    judgment = judge_evidence(
        "The analysis used Bonferroni correction as the multiple-comparison adjustment.",
        "The analysis used Benjamini-Hochberg correction as the multiple-comparison adjustment.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_measurement_target_swap_is_partial() -> None:
    judgment = judge_evidence(
        "Drug A improves the primary endpoint.",
        "Drug A improves the secondary endpoint.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
