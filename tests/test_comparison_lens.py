from citeproof.fact_lenses import inspect_facts
from citeproof.models import Label


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


def test_qualified_comparison_context_is_partial_support() -> None:
    result = inspect_facts(
        "LoRA outperforms Prefix Tuning on low-resource GLUE.",
        "Prefix Tuning outperforms LoRA on high-resource GLUE.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Comparison context mismatch" in finding for finding in result.findings)
    assert not any("Comparison direction conflict" in finding for finding in result.findings)


def test_comparison_context_mismatch_outranks_entity_conflict() -> None:
    result = inspect_facts(
        "LoRA outperforms Prefix Tuning on GLUE.",
        "Prefix Tuning outperforms LoRA on SQuAD.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Comparison context mismatch" in finding for finding in result.findings)
    assert not any("Entity conflict" in finding for finding in result.findings)


def test_numeric_conflict_outranks_comparison_context_mismatch() -> None:
    result = inspect_facts(
        "LoRA outperforms Prefix Tuning by 5% on GLUE.",
        "Prefix Tuning outperforms LoRA by 7% on SQuAD.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Numeric conflict" in finding for finding in result.findings)


def test_for_comparison_context_is_partial_support() -> None:
    result = inspect_facts(
        "AlphaModel is better than BetaModel for latency.",
        "BetaModel is better than AlphaModel for accuracy.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Comparison context mismatch" in finding for finding in result.findings)


def test_for_metric_comparison_context_is_partial_support() -> None:
    result = inspect_facts(
        "AlphaModel is better than BetaModel for F1.",
        "BetaModel is better than AlphaModel for accuracy.",
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


def test_detects_reversed_beats_comparison() -> None:
    result = inspect_facts(
        "LoRA beats Prefix Tuning on GLUE.",
        "Prefix Tuning beats LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Comparison direction conflict" in finding for finding in result.findings)


def test_detects_reversed_exceeds_comparison() -> None:
    result = inspect_facts(
        "LoRA exceeds Prefix Tuning on GLUE.",
        "Prefix Tuning exceeds LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED


def test_detects_reversed_outperformed_comparison() -> None:
    result = inspect_facts(
        "LoRA outperformed Prefix Tuning on GLUE.",
        "Prefix Tuning outperformed LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED


def test_passive_outperformed_matches_active_equivalent() -> None:
    result = inspect_facts(
        "LoRA was outperformed by Prefix Tuning on GLUE.",
        "Prefix Tuning outperformed LoRA on GLUE.",
    )

    assert result.label is None


def test_passive_outperformed_contradicts_reversed_active() -> None:
    result = inspect_facts(
        "LoRA was outperformed by Prefix Tuning on GLUE.",
        "LoRA outperformed Prefix Tuning on GLUE.",
    )

    assert result.label == Label.CONTRADICTED


def test_detects_reversed_achieves_higher_accuracy_comparison() -> None:
    result = inspect_facts(
        "LoRA achieves higher accuracy than Prefix Tuning on GLUE.",
        "Prefix Tuning achieves higher accuracy than LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED


def test_detects_reversed_lower_error_comparison() -> None:
    result = inspect_facts(
        "LoRA has lower error than Prefix Tuning on GLUE.",
        "Prefix Tuning has lower error than LoRA on GLUE.",
    )

    assert result.label == Label.CONTRADICTED


def test_lower_error_context_mismatch_is_partial_support() -> None:
    result = inspect_facts(
        "LoRA has lower error than Prefix Tuning on GLUE.",
        "Prefix Tuning has lower error than LoRA on SQuAD.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Comparison context mismatch" in finding for finding in result.findings)


def test_lower_error_vs_higher_accuracy_dimension_is_partial_support() -> None:
    result = inspect_facts(
        "AlphaModel has lower error than BetaModel on GLUE.",
        "BetaModel achieves higher accuracy than AlphaModel on GLUE.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Comparison dimension mismatch" in finding for finding in result.findings)


def test_tie_does_not_support_outperform_claim() -> None:
    result = inspect_facts(
        "Method X outperforms Method Y.",
        "Method X ties Method Y.",
    )

    assert result.label == Label.PARTIALLY_SUPPORTED
    assert any("Comparison strength mismatch" in finding for finding in result.findings)
