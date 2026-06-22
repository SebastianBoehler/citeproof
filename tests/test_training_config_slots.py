from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label
from citeproof.pvalue_lens import inspect_p_value_conflicts
from citeproof.training_config_lens import inspect_training_config_conflicts


def test_training_config_numeric_slots_are_not_supported() -> None:
    cases = (
        (
            "The model was trained with a learning rate of 1e-4.",
            "The model was trained with a learning rate of 5e-5.",
        ),
        (
            "The model was trained with a batch size of 64.",
            "The model was trained with a batch size of 128.",
        ),
        (
            "The model was trained for 3 epochs.",
            "The model was trained for 10 epochs.",
        ),
        ("The model uses dropout 0.1.", "The model uses dropout 0.3."),
        ("The decoder uses temperature 0.7.", "The decoder uses temperature 1.0."),
        ("The decoder uses top-p 0.9 sampling.", "The decoder uses top-p 0.95 sampling."),
        ("Training used weight decay 0.01.", "Training used weight decay 0.1."),
        ("The decoder uses beam size 4.", "The decoder uses beam size 8."),
        ("Training used lr=1e-4.", "Training used lr=5e-5."),
        ("The run used batch size: 64.", "The run used batch size: 128."),
    )

    for claim, evidence in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_matching_training_config_slots_remain_clean() -> None:
    result = inspect_facts(
        "The decoder uses top-p 0.9 sampling.",
        "The decoder uses top-p 0.9 sampling.",
    )

    assert result.label is None


def test_top_p_is_not_treated_as_statistical_p_value() -> None:
    claim = "The decoder uses top-p 0.9 sampling."
    evidence = "The decoder uses top-p 0.95 sampling."

    assert inspect_p_value_conflicts(claim, evidence, context_overlaps=True) == ()
    assert inspect_training_config_conflicts(claim, evidence)


def test_unrelated_training_config_subjects_do_not_conflict() -> None:
    result = inspect_training_config_conflicts(
        "The model was trained with a batch size of 64.",
        "The baseline was trained with a batch size of 128.",
    )

    assert result == ()
