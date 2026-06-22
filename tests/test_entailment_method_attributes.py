import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        (
            "The method uses supervised training.",
            "The method uses unsupervised training without labels.",
        ),
        (
            "The study is randomized.",
            "The study is observational and not randomized.",
        ),
        (
            "The system performs abstractive summarization.",
            "The system performs extractive summarization.",
        ),
        (
            "The policy is trained in a multi-agent environment.",
            "The policy is trained in a single-agent environment.",
        ),
    ],
)
def test_method_attribute_conflicts_are_not_supported(claim: str, evidence: str) -> None:
    judgment = judge_evidence(claim, evidence)

    assert judgment.label == Label.CONTRADICTED


def test_method_attribute_conflict_maps_to_entity_failure() -> None:
    judgment = adjudicate_evidence(
        "The method uses supervised training.",
        "The method uses unsupervised training without labels.",
    )

    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT
