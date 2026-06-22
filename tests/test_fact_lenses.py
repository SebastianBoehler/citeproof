from citeproof.fact_lenses import inspect_facts
from citeproof.models import Label


def test_detects_multi_number_conflict_with_units() -> None:
    result = inspect_facts(
        "The model was trained on 6000 examples with 4 GPUs.",
        "The model was trained on 6000 examples with 1 GPU.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("4 GPUs" in finding for finding in result.findings)


def test_detects_unit_conflict_for_same_number() -> None:
    result = inspect_facts(
        "The evaluation used 42 percent of the dataset.",
        "The evaluation used 42 examples from the dataset.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Unit conflict" in finding for finding in result.findings)


def test_does_not_flag_unit_overlap_as_conflict() -> None:
    result = inspect_facts(
        "The evaluation used 42 percent of the dataset.",
        "The evaluation used 42 percent of the dataset, corresponding to 42 examples.",
    )

    assert result.label != Label.CONTRADICTED
    assert not any("Unit conflict" in finding for finding in result.findings)


def test_detects_year_conflict() -> None:
    result = inspect_facts(
        "Qwen2.5 Technical Report was published in 2025.",
        "Qwen2.5 Technical Report was released in 2024.",
    )

    assert result.label == Label.CONTRADICTED


def test_detects_hedged_partial_support() -> None:
    result = inspect_facts(
        "The adapter improves transfer to unseen domains.",
        "The adapter may improve transfer to unseen domains, but the study was inconclusive.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED


def test_detects_scope_gap_partial_support() -> None:
    result = inspect_facts(
        "All evaluated models generalize to unseen domains.",
        "Only two evaluated models generalized to the unseen hotel domain.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED


def test_detects_missing_material_anchor() -> None:
    result = inspect_facts(
        "LoRA improves accuracy over full fine-tuning on GLUE.",
        "Prefix Tuning improves accuracy over full fine-tuning on GLUE.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Entity conflict" in finding for finding in result.findings)
    assert any("LoRA" in finding for finding in result.findings)
    assert any("Prefix Tuning" in finding for finding in result.findings)


def test_detects_dataset_anchor_swap() -> None:
    result = inspect_facts(
        "LoRA improves accuracy on GLUE.",
        "LoRA improves accuracy on SQuAD.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("GLUE" in finding for finding in result.findings)
    assert any("SQuAD" in finding for finding in result.findings)


def test_ignores_single_letter_placeholders_as_anchors() -> None:
    result = inspect_facts(
        "Method X improves accuracy over the baseline.",
        "Method X improves accuracy over the baseline.",
    )

    assert result.label is None
    assert result.findings == ()


def test_ignores_acronym_expansion_without_competing_anchor() -> None:
    result = inspect_facts(
        "USA models improve accuracy over the baseline.",
        "United States models improve accuracy over the baseline.",
    )

    assert result.label is None
    assert result.findings == ()


def test_ignores_lowercase_method_expansion_without_competing_anchor() -> None:
    result = inspect_facts(
        "CNN improves accuracy over the baseline.",
        "A convolutional neural network improves accuracy over the baseline.",
    )

    assert result.label is None
    assert result.findings == ()


def test_partial_anchor_coverage_is_not_entity_conflict() -> None:
    result = inspect_facts(
        "LoRA improves accuracy on GLUE and SQuAD.",
        "LoRA improves accuracy on GLUE.",
    )

    assert result.label is None
    assert result.findings == ()


def test_gpt4_anchor_does_not_match_gpt4o() -> None:
    result = inspect_facts(
        "GPT-4 improves accuracy on GLUE.",
        "GPT-4o improves accuracy on GLUE.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("GPT-4" in finding for finding in result.findings)
    assert any("GPT-4o" in finding for finding in result.findings)


def test_detects_reversed_outperforms_comparison() -> None:
    result = inspect_facts(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "Prefix Tuning outperforms LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Comparison direction conflict" in finding for finding in result.findings)


def test_detects_reversed_higher_than_comparison() -> None:
    result = inspect_facts(
        "AlphaModel has higher accuracy than BetaModel.",
        "BetaModel has higher accuracy than AlphaModel.",
    )

    assert result.label == Label.CONTRADICTED


def test_matching_comparison_direction_is_not_conflict() -> None:
    result = inspect_facts(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "LoRA outperforms Prefix Tuning on GLUE.",
    )

    assert result.label is None


def test_different_comparison_context_is_partial_support() -> None:
    result = inspect_facts(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "Prefix Tuning outperforms LoRA in low-resource settings.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Comparison context mismatch" in finding for finding in result.findings)


def test_different_comparison_dimension_is_partial_support() -> None:
    result = inspect_facts(
        "AlphaModel is better than BetaModel in latency.",
        "BetaModel has higher accuracy than AlphaModel.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Comparison dimension mismatch" in finding for finding in result.findings)


def test_detects_reversed_comparison_with_leading_context() -> None:
    result = inspect_facts(
        "On GLUE, LoRA outperforms Prefix Tuning.",
        "On GLUE, Prefix Tuning outperforms LoRA.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Comparison direction conflict" in finding for finding in result.findings)


def test_detects_reversed_comparison_with_benchmark_framing() -> None:
    result = inspect_facts(
        "The GLUE benchmark shows LoRA outperforms Prefix Tuning.",
        "The GLUE benchmark shows Prefix Tuning outperforms LoRA.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Comparison direction conflict" in finding for finding in result.findings)
