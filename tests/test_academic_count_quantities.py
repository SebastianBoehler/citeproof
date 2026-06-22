from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label


def test_patient_count_conflict_is_numeric_conflict() -> None:
    result = inspect_facts(
        "The study enrolled 100 patients.",
        "The study enrolled 120 patients.",
    )

    assert result.label == Label.CONTRADICTED
    assert any("Numeric conflict" in finding for finding in result.findings)


def test_patient_count_conflict_is_not_supported() -> None:
    judgment = adjudicate_evidence(
        "The study enrolled 100 patients.",
        "The study enrolled 120 patients.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_matching_academic_count_is_not_conflict() -> None:
    result = inspect_facts(
        "The trial included 240 participants.",
        "The trial included 240 participants.",
    )

    assert result.label is None
