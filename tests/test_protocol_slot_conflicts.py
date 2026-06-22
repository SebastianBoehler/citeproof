from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label


def test_comparator_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The trial compared the intervention with placebo.",
        "The trial compared the intervention with usual care.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_control_group_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The study used an active control group.",
        "The study used a placebo control group.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_dosing_frequency_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "Patients received the drug daily.",
        "Patients received the drug weekly.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_duration_and_dose_quantity_conflicts_are_numeric() -> None:
    cases = (
        (
            "The study measured mortality at 30 days.",
            "The study measured mortality at 90 days.",
        ),
        (
            "Patients received 10 mg of the drug.",
            "Patients received 20 mg of the drug.",
        ),
    )

    for claim, evidence in cases:
        judgment = adjudicate_evidence(claim, evidence)
        assert judgment.label == Label.CONTRADICTED
        assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_matching_protocol_slots_remain_clean() -> None:
    result = inspect_facts(
        "The trial compared the intervention with placebo.",
        "The trial compared the intervention with placebo.",
    )

    assert result.label is None


def test_usual_care_and_standard_care_match() -> None:
    result = inspect_facts(
        "The trial compared the intervention with usual care.",
        "The trial compared the intervention with standard care.",
    )

    assert result.label is None
