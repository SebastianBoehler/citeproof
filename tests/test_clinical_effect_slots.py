from citeproof.adjudicator import adjudicate_evidence
from citeproof.fact_lenses import inspect_facts
from citeproof.models import FailureMode, Label


def test_exact_hazard_ratio_conflict_is_numeric() -> None:
    judgment = adjudicate_evidence(
        "Treatment reduced mortality with a hazard ratio of 0.72.",
        "Treatment reduced mortality with a hazard ratio of 0.95.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_adjusted_unadjusted_estimate_conflict() -> None:
    judgment = adjudicate_evidence(
        "The study reports an adjusted odds ratio for mortality.",
        "The study reports an unadjusted odds ratio for mortality.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_population_group_conflict() -> None:
    judgment = adjudicate_evidence(
        "The cohort included adults with sepsis.",
        "The cohort included children with sepsis.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_endpoint_window_conflict_is_numeric() -> None:
    judgment = adjudicate_evidence(
        "The trial reduced 30-day mortality.",
        "The trial reduced 90-day mortality.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.NUMERIC_CONFLICT


def test_trial_design_conflict() -> None:
    judgment = adjudicate_evidence(
        "The study was a randomized phase II trial of DrugX.",
        "The study was a single-arm phase II trial of DrugX.",
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_trainable_scope_conflict() -> None:
    judgment = adjudicate_evidence(
        "LoRA updates all model weights during fine-tuning.",
        (
            "LoRA keeps pretrained model weights frozen and updates low-rank "
            "adapter weights during fine-tuning."
        ),
    )

    assert judgment.label == Label.CONTRADICTED
    assert judgment.failure_mode == FailureMode.ENTITY_CONFLICT


def test_matching_clinical_slots_remain_clean() -> None:
    result = inspect_facts(
        "The study reports an adjusted odds ratio for mortality.",
        "The study reports an adjusted odds ratio for mortality.",
    )

    assert result.label is None
