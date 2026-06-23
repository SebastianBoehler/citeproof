from citeproof.adjudicator import adjudicate_evidence
from citeproof.models import Label


def test_metric_value_does_not_treat_benchmark_year_as_score() -> None:
    judgment = adjudicate_evidence(
        "The big Transformer achieved 28.4 BLEU on WMT 2014 English-to-German translation.",
        "On the WMT 2014 English-to-German translation task, the big transformer model "
        "outperforms the best previously reported models by more than 2.0 BLEU, "
        "establishing a new state-of-the-art BLEU score of 28.4.",
    )

    assert judgment.label == Label.SUPPORTED


def test_supported_value_can_appear_in_multi_value_evidence() -> None:
    judgment = adjudicate_evidence(
        "Qwen2.5 increased pre-training data to 18 trillion tokens.",
        "The pre-training data increased from 7 trillion tokens to 18 trillion tokens, "
        "with focus on knowledge, coding, math, multilinguality, and long-context data.",
    )

    assert judgment.label == Label.SUPPORTED


def test_metric_point_delta_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "SimpleTOD improves inform rate by 8.1 points and success rate by 19.7 points.",
        "SimpleTOD improves the main metrics used to evaluate action decisions and response "
        "generation in an end-to-end setting: inform rate by 8.1 points, success rate by "
        "9.7 points, and combined score.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_reproducibility_challenge_count_passage_is_supported() -> None:
    judgment = adjudicate_evidence(
        "The NeurIPS 2019 Reproducibility Challenge had 173 papers claimed for reproduction.",
        "The NeurIPS 2019 Reproducibility Challenge used OpenReview to enable communication "
        "between authors and challenge participants. A total of 173 papers were claimed for "
        "reproduction.",
    )

    assert judgment.label == Label.SUPPORTED


def test_reproducibility_challenge_count_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The NeurIPS 2019 Reproducibility Challenge had 74 papers claimed for reproduction.",
        "The NeurIPS 2019 Reproducibility Challenge used OpenReview to enable communication "
        "between authors and challenge participants. A total of 173 papers were claimed for "
        "reproduction.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_multiplier_improvement_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "Models quantized by VPTQ result in 3 times improvement in inference throughput.",
        "The models quantized by VPTQ result in 1.6 to 1.8 times improvement in inference "
        "throughput compared to SOTA.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_open_domain_chatbot_skill_passage_is_supported() -> None:
    judgment = adjudicate_evidence(
        "Good open-domain conversation requires displaying knowledge, empathy, and personality.",
        "Good conversation requires a number of skills that an expert conversationalist blends "
        "in a seamless way: providing engaging talking points and listening to their partners, "
        "and displaying knowledge, empathy and personality appropriately.",
    )

    assert judgment.label == Label.SUPPORTED
