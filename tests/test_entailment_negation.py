from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


def test_judge_evidence_does_not_support_use_negation() -> None:
    judgment = judge_evidence(
        "The method uses LoRA adapters.",
        "The method does not use LoRA adapters.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_does_not_support_training_negation() -> None:
    judgment = judge_evidence(
        "The model was trained on ImageNet.",
        "The model was not trained on ImageNet.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_does_not_support_direction_swap() -> None:
    judgment = judge_evidence(
        "Error decreased by 5 percent.",
        "Error increased by 5 percent.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_does_not_support_bound_conflict() -> None:
    judgment = judge_evidence(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains up to 16,000 task-oriented dialogues.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_marks_bound_equality_tension_partial() -> None:
    judgment = judge_evidence(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 16,000 task-oriented dialogues.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED


def test_adjudicator_maps_negation_conflict_failure_mode() -> None:
    judgment = adjudicate_evidence(
        "The method uses LoRA adapters.",
        "The method does not use LoRA adapters.",
    )

    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT


def test_adjudicator_maps_numeric_bound_failure_mode() -> None:
    judgment = adjudicate_evidence(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains up to 16,000 task-oriented dialogues.",
    )

    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT
