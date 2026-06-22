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
