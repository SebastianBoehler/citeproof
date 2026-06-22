from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label


def test_data_origin_conflicts_are_not_supported() -> None:
    cases = (
        (
            "The dataset contains synthetic images.",
            "The dataset contains real clinical images.",
        ),
        (
            "The benchmark uses real user queries.",
            "The benchmark uses synthetic user queries.",
        ),
        (
            "The benchmark evaluates simulated user interactions.",
            "The benchmark evaluates real user interactions.",
        ),
        (
            "The corpus contains synthetic dialogues.",
            "The corpus contains real user dialogues.",
        ),
    )

    for claim, evidence in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_matching_data_origin_remains_clean() -> None:
    result = inspect_facts(
        "The benchmark uses synthetic user queries.",
        "The benchmark uses synthetic user queries.",
    )

    assert result.label is None
