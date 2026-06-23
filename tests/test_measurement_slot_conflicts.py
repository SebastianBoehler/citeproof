from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label


def test_metric_scalar_conflicts_are_numeric() -> None:
    cases = (
        (
            "The model achieved an accuracy of 0.92 on the test set.",
            "The model achieved an accuracy of 0.84 on the test set.",
        ),
        (
            "The model achieved an AUROC of 0.91 on the test set.",
            "The model achieved an AUROC of 0.82 on the test set.",
        ),
        (
            "The system achieved a BLEU score of 31.2 on WMT14.",
            "The system achieved a BLEU score of 27.4 on WMT14.",
        ),
    )

    for claim, evidence in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_compact_quantity_conflicts_are_numeric() -> None:
    cases = (
        ("The model has 7B parameters.", "The model has 13B parameters."),
        ("The context window is 32k tokens.", "The context window is 128k tokens."),
    )

    for claim, evidence in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_benchmark_version_conflict_is_entity_conflict() -> None:
    judgment = adjudicate_evidence(
        "The evaluation uses MMLU-Pro.",
        "The evaluation uses MMLU.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_adjectival_generated_marker_is_not_benchmark_version() -> None:
    result = inspect_facts(
        "Distilling step-by-step uses LLM-generated rationales as additional supervision.",
        "The method extracts LLM rationales as additional supervision for training small models.",
    )

    assert result.label is None


def test_matching_measurement_slots_remain_clean() -> None:
    result = inspect_facts(
        "The model achieved an AUROC of 0.91 on the test set.",
        "The model achieved an AUROC of 0.91 on the test set.",
    )

    assert result.label is None
