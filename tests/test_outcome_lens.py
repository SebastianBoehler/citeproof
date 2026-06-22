from citeproof.outcome_lens import inspect_outcome_conflicts, inspect_outcome_tensions


def test_specific_outcome_unchanged_blocks_support() -> None:
    findings = inspect_outcome_conflicts(
        "The method improves calibration.",
        "The method improves accuracy, but calibration is unchanged.",
    )

    assert any("Outcome status conflict" in finding for finding in findings)


def test_no_change_for_different_metric_does_not_conflict() -> None:
    findings = inspect_outcome_conflicts(
        "Method X improves accuracy over the baseline.",
        "Method X improves accuracy over the baseline, with no improvement in F1.",
    )

    assert findings == ()


def test_no_change_for_resource_outcome_blocks_support() -> None:
    findings = inspect_outcome_conflicts(
        "The system reduces latency.",
        "The system reduces memory use, but latency shows no change.",
    )

    assert any("Outcome status conflict" in finding for finding in findings)


def test_lower_is_better_metric_direction_blocks_support() -> None:
    findings = inspect_outcome_conflicts(
        "DenoiseNet improves mean absolute error over Baseline.",
        "DenoiseNet reports a higher mean absolute error than Baseline.",
    )

    assert any("Lower-is-better outcome conflict" in finding for finding in findings)


def test_mixed_effects_are_partial_not_hard_conflicts() -> None:
    conflicts = inspect_outcome_conflicts(
        "The method reduces hallucinations.",
        "The method reduces hallucinations on short answers but increases hallucinations on long answers.",
    )
    tensions = inspect_outcome_tensions(
        "The method reduces hallucinations.",
        "The method reduces hallucinations on short answers but increases hallucinations on long answers.",
    )

    assert conflicts == ()
    assert any("Mixed outcome effect" in finding for finding in tensions)
