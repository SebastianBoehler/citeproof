from citeproof.protocol_lens import (
    inspect_protocol_conflicts,
    inspect_protocol_tensions,
)


def test_multiple_comparison_correction_conflict() -> None:
    findings = inspect_protocol_conflicts(
        "The analysis used Bonferroni correction as the multiple-comparison adjustment.",
        "The analysis used Benjamini-Hochberg correction as the multiple-comparison adjustment.",
    )

    assert any("Protocol conflict" in finding for finding in findings)


def test_train_test_leakage_conflict() -> None:
    findings = inspect_protocol_conflicts(
        "Benchmark-Z uses disjoint train and test patients.",
        "Benchmark-Z uses the same patients in the train and test sets.",
    )

    assert any("Protocol conflict" in finding for finding in findings)


def test_commercial_use_availability_conflict() -> None:
    findings = inspect_protocol_conflicts(
        "The dataset permits commercial use.",
        "The dataset is restricted to non-commercial research use.",
    )

    assert any("Protocol conflict" in finding for finding in findings)


def test_training_code_release_conflict() -> None:
    findings = inspect_protocol_conflicts(
        "The authors release open-source training code.",
        "The authors release model weights but do not release training code.",
    )

    assert any("Release conflict" in finding for finding in findings)


def test_endpoint_swap_is_partial_support() -> None:
    conflicts = inspect_protocol_conflicts(
        "Drug A improves the primary endpoint.",
        "Drug A improves the secondary endpoint.",
    )
    tensions = inspect_protocol_tensions(
        "Drug A improves the primary endpoint.",
        "Drug A improves the secondary endpoint.",
    )

    assert conflicts == ()
    assert any("Measurement target tension" in finding for finding in tensions)
