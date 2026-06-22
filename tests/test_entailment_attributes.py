import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The dataset contains 10,000 images.", "The dataset contains 10,000 text samples."),
        (
            "The method improves summarization performance.",
            "The method improves translation performance.",
        ),
        (
            "The model was evaluated on the test set.",
            "The model was evaluated on the validation set.",
        ),
        (
            "The benchmark evaluates German documents.",
            "The benchmark evaluates English documents.",
        ),
        ("The model uses Adam optimization.", "The model uses SGD optimization."),
        ("The dataset is publicly available.", "The dataset is not publicly available."),
    ],
)
def test_attribute_conflicts_are_not_supported(claim: str, evidence: str) -> None:
    judgment = judge_evidence(claim, evidence)

    assert judgment.label == Label.CONTRADICTED


def test_availability_conflict_maps_to_negation_failure() -> None:
    judgment = adjudicate_evidence(
        "The dataset is publicly available.",
        "The dataset is not publicly available.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT


def test_task_conflict_maps_to_entity_failure() -> None:
    judgment = adjudicate_evidence(
        "The method improves summarization performance.",
        "The method improves translation performance.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT
