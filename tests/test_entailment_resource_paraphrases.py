from citeproof.entailment import judge_evidence
from citeproof.models import Label


def test_training_time_fewer_hours_paraphrase_support() -> None:
    judgment = judge_evidence(
        "Method X reduces training time.",
        "Method X required fewer training hours than the baseline.",
    )

    assert judgment.label == Label.SUPPORTED


def test_sample_efficiency_fewer_interactions_paraphrase_support() -> None:
    judgment = judge_evidence(
        "Method X improves sample efficiency.",
        "Method X reaches the target success rate with fewer environment interactions.",
    )

    assert judgment.label == Label.SUPPORTED


def test_negated_resource_reduction_is_not_supported() -> None:
    judgment = judge_evidence(
        "Method X improves sample efficiency.",
        "Method X does not require fewer environment interactions than the baseline.",
    )

    assert judgment.label != Label.SUPPORTED


def test_no_fewer_resource_reduction_is_not_supported() -> None:
    judgment = judge_evidence(
        "Method X improves sample efficiency.",
        "Method X required no fewer environment interactions than the baseline.",
    )

    assert judgment.label != Label.SUPPORTED


def test_less_modifier_unrelated_to_time_is_not_supported() -> None:
    judgment = judge_evidence(
        "Method X reduces training time.",
        "Method X was less stable over time than the baseline during training.",
    )

    assert judgment.label != Label.SUPPORTED


def test_sample_efficiency_not_supported_by_fewer_training_hours() -> None:
    judgment = judge_evidence(
        "Method X improves sample efficiency.",
        "Method X required fewer training hours than the baseline.",
    )

    assert judgment.label != Label.SUPPORTED


def test_training_time_not_supported_by_fewer_samples() -> None:
    judgment = judge_evidence(
        "Method X reduces training time.",
        "Method X required fewer training samples than the baseline.",
    )

    assert judgment.label != Label.SUPPORTED
