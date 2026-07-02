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


def test_detects_dependency_avoidance_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The training procedure depends on human labels identifying harmful outputs.",
        "The training procedure avoids human labels for harmfulness.",
    )

    assert any("Negation conflict" in finding for finding in findings)


def test_detects_requirement_not_necessary_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The classifier requires convolutional networks.",
        "The classifier shows that convolutional networks are not necessary.",
    )

    assert any("Negation conflict" in finding for finding in findings)


def test_detects_reward_modeling_nominalization_conflict() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The preference method trains an explicit reward model.",
        "The preference method works without explicit reward modeling.",
    )

    assert any("Negation conflict" in finding for finding in findings)


def test_ignores_unrelated_negated_object() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The method uses LoRA adapters.",
        "The method does not use labels during training.",
    )

    assert findings == ()


def test_ignores_scoped_negation_with_affirmative_contrast() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The method uses supervised adapters.",
        "The method does not use supervised adapters for baselines, "
        "but uses them for the final run.",
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


def test_ignores_bare_more_less_direction_words() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "The paper reports more ablations in the appendix.",
        "The paper reports less wall-clock time in the appendix.",
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


def test_ignores_numeric_bound_conflict_for_different_entities() -> None:
    findings = inspect_negation_and_comparator_conflicts(
        "Dataset A contains over 16k dialogues.",
        "Dataset B contains up to 16,000 dialogues.",
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
