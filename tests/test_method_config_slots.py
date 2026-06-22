from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label


def test_method_config_slot_conflicts_are_not_supported() -> None:
    cases = (
        (
            "GPT-3 uses a mixture-of-experts transformer architecture.",
            "GPT-3 uses a dense transformer architecture.",
        ),
        (
            "BERT uses a causal language modeling objective.",
            "BERT uses a masked language modeling objective.",
        ),
        (
            "The model is evaluated in a zero-shot setting.",
            "The model is evaluated in a few-shot setting.",
        ),
        (
            "The system decodes with greedy search.",
            "The system decodes with beam search.",
        ),
    )

    for claim, evidence in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_architecture_count_conflicts_are_numeric() -> None:
    cases = (
        ("The model has 12 layers.", "The model has 24 layers."),
        ("The model uses 16 attention heads.", "The model uses 32 attention heads."),
    )

    for claim, evidence in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_matching_method_config_slots_remain_clean() -> None:
    result = inspect_facts(
        "The system decodes with beam search.",
        "The system decodes with beam search.",
    )

    assert result.label is None
