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


def test_detects_metric_negation_as_contradiction() -> None:
    judgment = judge_evidence(
        "Method X improves F1 score over the baseline.",
        "Method X improves accuracy over the baseline, with no F1 score improvement.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_metric_negation_does_not_contradict_different_supported_metric() -> None:
    judgment = judge_evidence(
        "Method X improves accuracy over the baseline.",
        "Method X improves accuracy over the baseline, with no F1 score improvement.",
    )

    assert judgment.label == Label.SUPPORTED


def test_metric_cross_support_with_no_improvement_in_f1() -> None:
    judgment = judge_evidence(
        "Method X improves accuracy over the baseline.",
        "Method X improves accuracy over the baseline, with no improvement in F1.",
    )

    assert judgment.label == Label.SUPPORTED


def test_metric_cross_contradicts_matching_metric() -> None:
    judgment = judge_evidence(
        "Method X improves F1 score over the baseline.",
        "Method X improves accuracy over the baseline, with no improvement in F1.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_accuracy_negation_does_not_contradict_supported_f1_metric() -> None:
    judgment = judge_evidence(
        "Method X improves F1 score over the baseline.",
        "Method X improves F1 score over the baseline, with no improvement in accuracy.",
    )

    assert judgment.label == Label.SUPPORTED


def test_detects_accuracy_metric_negation_as_contradiction() -> None:
    judgment = judge_evidence(
        "Method X improves accuracy over the baseline.",
        "Method X improves F1 score over the baseline, with no accuracy improvement.",
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


def test_method_anchor_swap_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA improves accuracy over full fine-tuning on GLUE.",
        "Prefix Tuning improves accuracy over full fine-tuning on GLUE.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_dataset_anchor_swap_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA improves accuracy on GLUE.",
        "LoRA improves accuracy on SQuAD.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_reversed_comparison_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "Prefix Tuning outperforms LoRA on GLUE.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_reversed_comparison_with_leading_context_is_not_supported() -> None:
    judgment = judge_evidence(
        "On GLUE, LoRA outperforms Prefix Tuning.",
        "On GLUE, Prefix Tuning outperforms LoRA.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_reversed_comparison_with_different_context_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "Prefix Tuning outperforms LoRA in low-resource settings.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED


def test_reversed_comparison_with_qualified_context_is_not_contradicted() -> None:
    judgment = judge_evidence(
        "LoRA outperforms Prefix Tuning on low-resource GLUE.",
        "Prefix Tuning outperforms LoRA on high-resource GLUE.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
    assert "Comparison context mismatch" in judgment.reason
    assert "Comparison direction conflict" not in judgment.reason


def test_reversed_comparison_context_mismatch_outranks_entity_conflict() -> None:
    judgment = judge_evidence(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "Prefix Tuning outperforms LoRA on SQuAD.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
    assert "Comparison context mismatch" in judgment.reason


def test_reversed_comparison_with_different_dimension_is_not_supported() -> None:
    judgment = judge_evidence(
        "AlphaModel is better than BetaModel in latency.",
        "BetaModel has higher accuracy than AlphaModel.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED


def test_reversed_comparison_with_for_dimensions_is_not_supported() -> None:
    judgment = judge_evidence(
        "AlphaModel is better than BetaModel for latency.",
        "BetaModel is better than AlphaModel for accuracy.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
    assert "Comparison context mismatch" in judgment.reason


def test_reversed_comparison_with_benchmark_framing_is_not_supported() -> None:
    judgment = judge_evidence(
        "The GLUE benchmark shows LoRA outperforms Prefix Tuning.",
        "The GLUE benchmark shows Prefix Tuning outperforms LoRA.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_negation_contradiction_outranks_partial_fact_inspection() -> None:
    judgment = judge_evidence(
        "Method X improves accuracy.",
        "Preliminary results show Method X does not improve accuracy.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_reversed_beats_comparison_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA beats Prefix Tuning on GLUE.",
        "Prefix Tuning beats LoRA on GLUE.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_lower_error_context_mismatch_is_not_supported() -> None:
    judgment = judge_evidence(
        "LoRA has lower error than Prefix Tuning on GLUE.",
        "Prefix Tuning has lower error than LoRA on SQuAD.",
    )

    assert judgment.label == Label.PARTIALLY_SUPPORTED
