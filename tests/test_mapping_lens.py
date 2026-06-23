from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label


def test_label_mapping_swap_is_contradicted() -> None:
    judgment = adjudicate_evidence(
        "In Predict-then-Decide, Y = 0 means the agent replies immediately and "
        "Y = 1 means the agent waits for the next user message.",
        "The goal is to predict a label Y where Y = 0 means the agent will wait "
        "for the user for the next message, and Y = 1 means the agent will reply immediately.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_matching_label_mapping_remains_clean() -> None:
    result = inspect_facts(
        "Y = 0 means the agent waits and Y = 1 means the agent replies immediately.",
        "Y = 0 means the agent will wait for the next message, and Y = 1 means "
        "the agent will reply immediately.",
    )

    assert result.label is None
