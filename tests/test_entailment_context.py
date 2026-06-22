import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        (
            "The method improves accuracy.",
            "The method improves accuracy only when oracle labels are available.",
        ),
        (
            "The model improves performance on ImageNet.",
            "The model improves performance on a 1% ImageNet subset.",
        ),
        (
            "The drug reduces inflammation in humans.",
            "The drug reduces inflammation in mice.",
        ),
    ],
)
def test_context_limitations_block_full_support(claim: str, evidence: str) -> None:
    judgment = adjudicate_evidence(claim, evidence)

    assert judgment.label == Label.PARTIALLY_SUPPORTED
    assert judgment.failure_mode == FailureMode.SCOPE_OVERSTATEMENT


def test_component_exclusion_blocks_support() -> None:
    judgment = adjudicate_evidence(
        "Retrieval improves factuality.",
        "The no-retrieval ablation improves factuality over the baseline.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT
