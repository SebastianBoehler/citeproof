from citeproof.negation_lens import (
    inspect_negation_and_comparator_conflicts,
    inspect_negation_and_comparator_tensions,
)


def test_detects_use_negation_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The method uses LoRA adapters.",
        "The method does not use LoRA adapters.",
    )

    assert any("Negation conflict" in finding for finding in findings)
    assert any("LoRA adapters" in finding for finding in findings)


def test_detects_training_negation_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The model was trained on ImageNet.",
        "The model was not trained on ImageNet.",
    )

    assert any("Negation conflict" in finding for finding in findings)
    assert any("ImageNet" in finding for finding in findings)


def test_detects_without_negation_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The approach uses offline pretraining.",
        "The approach works without offline pretraining.",
    )

    assert any("Negation conflict" in finding for finding in findings)
    assert any("offline pretraining" in finding for finding in findings)


def test_ignores_unrelated_negated_object() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The method uses LoRA adapters.",
        "The method does not use labels during training.",
    )

    assert findings == ()


def test_detects_direction_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "Error decreased by 5 percent.",
        "Error increased by 5 percent.",
    )

    assert any("Direction conflict" in finding for finding in findings)


def test_ignores_direction_change_for_different_metric() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "Training time decreased by 5 percent.",
        "Accuracy increased by 5 percent.",
    )

    assert findings == ()


def test_detects_incompatible_numeric_bounds() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains up to 16,000 task-oriented dialogues.",
    )

    assert any("Numeric bound conflict" in finding for finding in findings)


def test_allows_compatible_lower_bound_quantity() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "Schema-Guided Dialogue contains at least 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 20,000 task-oriented dialogues.",
    )

    assert findings == ()


def test_flags_bound_equality_as_partial_tension() -> None:
    hard_findings = inspect_negation_and_comparator_conflicts(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 16,000 task-oriented dialogues.",
    )
    partial_findings = inspect_negation_and_comparator_tensions(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 16,000 task-oriented dialogues.",
    )

    assert hard_findings == ()
    assert any("Numeric bound tension" in finding for finding in partial_findings)
