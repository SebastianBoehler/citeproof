import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The algorithm runs in linear time.", "The algorithm runs in quadratic time."),
        ("The method uses exact inference.", "The method uses approximate inference."),
        (
            "The encoder is frozen during training.",
            "The encoder is fine-tuned end-to-end during training.",
        ),
        ("The agent is trained with dense rewards.", "The agent is trained with sparse rewards."),
        (
            "The model is evaluated on out-of-domain data.",
            "The model is evaluated on in-domain data.",
        ),
        (
            "The dataset contains private medical records.",
            "The dataset contains public medical records.",
        ),
    ],
)
def test_technical_property_conflicts_are_not_supported(claim: str, evidence: str) -> None:
    judgment = judge_evidence(claim, evidence)

    assert judgment.label == Label.CONTRADICTED


def test_technical_property_conflict_maps_to_entity_failure() -> None:
    judgment = adjudicate_evidence(
        "The algorithm runs in linear time.",
        "The algorithm runs in quadratic time.",
    )

    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT
