import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        ("The confidence interval excludes zero.", "The 95% confidence interval includes zero."),
        ("The system improves macro-F1.", "The system improves micro-F1."),
        ("The paper reports median latency.", "The paper reports mean latency."),
        ("The error bars show standard deviation.", "The error bars show standard error."),
        ("The test uses a paired bootstrap.", "The test uses an unpaired bootstrap."),
        ("The analysis uses a one-tailed test.", "The analysis uses a two-tailed test."),
        ("The method uses a parametric test.", "The method uses a nonparametric test."),
    ],
)
def test_statistical_conflicts_are_not_supported(claim: str, evidence: str) -> None:
    judgment = judge_evidence(claim, evidence)

    assert judgment.label == Label.CONTRADICTED


def test_statistical_conflict_maps_to_entity_failure() -> None:
    judgment = adjudicate_evidence(
        "The paper reports median latency.",
        "The paper reports mean latency.",
    )

    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_p_value_conflict_maps_to_numeric_failure() -> None:
    judgment = adjudicate_evidence(
        "The model improvement has p < 0.05.",
        "The model improvement has p = 0.08.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_numeric_confidence_interval_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The treatment effect confidence interval excludes zero.",
        "The treatment effect 95% confidence interval was [-0.10, 0.30].",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_ratio_effect_conflict_maps_to_numeric_failure() -> None:
    judgment = adjudicate_evidence(
        "The treatment hazard ratio is below 1.",
        "The treatment hazard ratio was 1.20.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT
