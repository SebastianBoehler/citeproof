import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The method yields a large improvement.", "The method yields a small improvement."),
        ("The method yields substantial gains.", "The method yields modest gains."),
    ],
)
def test_strength_magnitude_conflicts_block_support(claim: str, evidence: str) -> None:
    judgment = adjudicate_evidence(claim, evidence)

    assert judgment.label == Label.CONTRADICTED
    assert "Magnitude conflict" in judgment.reason


def test_strength_overhead_conflict_gets_negation_mode() -> None:
    judgment = adjudicate_evidence(
        "The method adds no computational overhead.",
        "The method adds small computational overhead.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        (
            "The intervention causes improved accuracy.",
            "The intervention is associated with improved accuracy.",
        ),
        (
            "The variable causes higher mortality.",
            "The variable is correlated with higher mortality.",
        ),
        ("The method achieves the best accuracy.", "The method achieves competitive accuracy."),
        ("The method fully recovers the signal.", "The method partially recovers the signal."),
    ],
)
def test_strength_tensions_block_full_support(claim: str, evidence: str) -> None:
    judgment = adjudicate_evidence(claim, evidence)

    assert judgment.label == Label.PARTIALLY_SUPPORTED
    assert judgment.failure_mode == FailureMode.SCOPE_OVERSTATEMENT
