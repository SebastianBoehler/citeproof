from citeproof.assertion_lens import inspect_assertion_status_tensions


def test_detects_future_work_as_status_tension() -> None:
    findings = inspect_assertion_status_tensions(
        "The method improves calibration.",
        "Future work will test whether the method improves calibration.",
    )

    assert any("Assertion status tension" in finding for finding in findings)


def test_detects_hypothesis_as_status_tension() -> None:
    findings = inspect_assertion_status_tensions(
        "Dropout improves robustness.",
        "We hypothesize that dropout improves robustness.",
    )

    assert any("Assertion status tension" in finding for finding in findings)


def test_detects_design_intent_as_status_tension() -> None:
    findings = inspect_assertion_status_tensions(
        "The method reduces hallucinations.",
        "The method is designed to reduce hallucinations.",
    )

    assert any("Assertion status tension" in finding for finding in findings)


def test_ignores_future_work_in_different_context() -> None:
    assert inspect_assertion_status_tensions(
        "The method improves calibration.",
        "The method improves calibration. Future work will test robustness.",
    ) == ()


def test_ignores_confirmed_hypothesis() -> None:
    assert inspect_assertion_status_tensions(
        "Dropout improves robustness.",
        "The hypothesis that dropout improves robustness was confirmed.",
    ) == ()
