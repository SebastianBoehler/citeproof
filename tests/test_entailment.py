from citeproof.entailment import judge_evidence
from citeproof.models import Label


def test_detects_polarity_contradiction() -> None:
    judgment = judge_evidence(
        "Method X outperforms PPO on sparse-reward robotics tasks.",
        "Method X performed comparably to PPO, with no statistically significant improvement.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_detects_supported_claim() -> None:
    judgment = judge_evidence(
        "Adaptive replay improves sample efficiency in sparse-reward manipulation tasks.",
        "Adaptive replay improves sample efficiency in sparse-reward manipulation tasks.",
    )

    assert judgment.label == Label.SUPPORTED


def test_detects_numeric_contradiction() -> None:
    judgment = judge_evidence(
        "The method improves success by 42 percent.",
        "The method improves success by 12 percent.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_avoids_unrelated_numeric_contradiction() -> None:
    judgment = judge_evidence(
        "We train on 6000 samples from WildChat.",
        "WildChat contains 1M ChatGPT interaction logs in the wild.",
    )

    assert judgment.label != Label.CONTRADICTED


def test_detects_scope_overstatement_as_partial() -> None:
    judgment = judge_evidence(
        "Adaptive replay improves sample efficiency in all robotics tasks.",
        "Adaptive replay improves sample efficiency in sparse-reward manipulation tasks. "
        "The effect was weaker in dense-reward locomotion tasks.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
