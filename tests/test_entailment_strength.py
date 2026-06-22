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


def test_leads_to_correlation_blocks_full_support() -> None:
    judgment = adjudicate_evidence(
        "Higher temperature leads to increased failure rates.",
        "Higher temperature correlated with increased failure rates in the logs.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
    assert judgment.failure_mode == FailureMode.SCOPE_OVERSTATEMENT


def test_randomized_intervention_supports_matching_causal_claim() -> None:
    judgment = adjudicate_evidence(
        "The intervention caused test scores to improve.",
        "The randomized intervention improved test scores relative to control.",
    )

    assert judgment.label == Label.SUPPORTED


def test_intervention_without_design_signal_does_not_fully_support_causal_claim() -> None:
    judgment = adjudicate_evidence(
        "The intervention caused test scores to improve.",
        "The intervention improved test scores in the pilot study.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
    assert judgment.failure_mode == FailureMode.SCOPE_OVERSTATEMENT


def test_randomized_non_effect_does_not_support_causal_improvement() -> None:
    judgment = adjudicate_evidence(
        "The intervention caused test scores to improve.",
        "The randomized intervention did not improve test scores relative to control.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NEGATION_CONFLICT
