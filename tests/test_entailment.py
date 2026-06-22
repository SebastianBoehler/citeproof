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


def test_detects_training_time_paraphrase_support() -> None:
    judgment = judge_evidence(
        "Method X reduces training time.",
        "Training with Method X required half as many hours as the baseline.",
    )

    assert judgment.label == Label.SUPPORTED


def test_reduce_negation_is_not_supported() -> None:
    judgment = judge_evidence(
        "Method X reduces training time.",
        "Method X does not reduce training time.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_detects_metric_paraphrase_support() -> None:
    judgment = judge_evidence(
        "BERTScore captures semantic similarity beyond exact lexical overlap.",
        "BERTScore computes token-level contextual embedding similarity rather than n-gram matching.",
    )

    assert judgment.label == Label.SUPPORTED


def test_language_negation_is_not_supported() -> None:
    judgment = judge_evidence(
        "WildChat spans diverse languages.",
        "WildChat does not cover multiple languages.",
    )

    assert judgment.label != Label.SUPPORTED
