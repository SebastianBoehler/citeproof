from citeproof.fact_lenses import inspect_facts
from citeproof.models import Label


def test_detects_compact_quantity_conflict() -> None:
    result = inspect_facts(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 15,000 task-oriented dialogues.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Numeric conflict" in finding for finding in result.findings)


def test_does_not_contradict_matching_compact_and_scale_word_quantities() -> None:
    result = inspect_facts(
        "WildChat contains 1M conversations.",
        "WildChat contains 1 million conversations.",
    )

    assert result.label != Label.CONTRADICTED


def test_does_not_contradict_matching_spelled_and_digit_quantities() -> None:
    result = inspect_facts(
        "The model was trained on four GPUs.",
        "The model was trained on 4 GPUs.",
    )

    assert result.label != Label.CONTRADICTED


def test_detects_spelled_quantity_conflict() -> None:
    result = inspect_facts(
        "The model was trained on four GPUs.",
        "The model was trained on three GPUs.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Numeric conflict" in finding for finding in result.findings)


def test_does_not_flag_extra_same_number_unit_as_conflict() -> None:
    result = inspect_facts(
        "The model was trained on four GPUs.",
        "The model was trained on four GPUs and four samples.",
    )

    assert result.label != Label.CONTRADICTED
    assert not any("Unit conflict" in finding for finding in result.findings)


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


def test_detects_qualitative_exclusivity_conflict() -> None:
    result = inspect_facts(
        "Method X is the only method evaluated on sparse-reward tasks.",
        "Method X is one of three methods evaluated on sparse-reward tasks.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Exclusivity conflict" in finding for finding in result.findings)


def test_detects_qualitative_scope_tension() -> None:
    result = inspect_facts(
        "Method X improves performance on all evaluated tasks.",
        "Method X improves performance on most evaluated tasks.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Scope tension" in finding for finding in result.findings)


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


def test_detects_use_negation_fact_conflict() -> None:
    result = inspect_facts(
        "The method uses LoRA adapters.",
        "The method does not use LoRA adapters.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Negation conflict" in finding for finding in result.findings)


def test_detects_direction_fact_conflict() -> None:
    result = inspect_facts(
        "Error decreased by 5 percent.",
        "Error increased by 5 percent.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Direction conflict" in finding for finding in result.findings)


def test_detects_numeric_bound_fact_conflict() -> None:
    result = inspect_facts(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains up to 16,000 task-oriented dialogues.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Numeric bound conflict" in finding for finding in result.findings)


def test_detects_numeric_bound_fact_tension() -> None:
    result = inspect_facts(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 16,000 task-oriented dialogues.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Numeric bound tension" in finding for finding in result.findings)


def test_does_not_contradict_compatible_lower_bound_quantity() -> None:
    result = inspect_facts(
        "Schema-Guided Dialogue contains at least 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 20,000 task-oriented dialogues.",
    )

    assert result.label != Label.CONTRADICTED
    assert not any("Numeric conflict" in finding for finding in result.findings)
