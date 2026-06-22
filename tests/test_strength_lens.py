from citeproof.strength_lens import inspect_strength_conflicts, inspect_strength_tensions


def test_detects_large_small_conflict() -> None:
    findings = inspect_strength_conflicts(
        "The method yields a large improvement.",
        "The method yields a small improvement.",
    )

    assert any("Magnitude conflict" in finding for finding in findings)


def test_detects_substantial_modest_conflict() -> None:
    findings = inspect_strength_conflicts(
        "The method yields substantial gains.",
        "The method yields modest gains.",
    )

    assert any("Magnitude conflict" in finding for finding in findings)


def test_detects_no_overhead_conflict() -> None:
    findings = inspect_strength_conflicts(
        "The method adds no computational overhead.",
        "The method adds small computational overhead.",
    )

    assert any("Overhead conflict" in finding for finding in findings)


def test_detects_causal_association_tension() -> None:
    findings = inspect_strength_tensions(
        "The intervention causes improved accuracy.",
        "The intervention is associated with improved accuracy.",
    )

    assert any("Causal overstatement" in finding for finding in findings)


def test_detects_best_competitive_tension() -> None:
    findings = inspect_strength_tensions(
        "The method achieves the best accuracy.",
        "The method achieves competitive accuracy.",
    )

    assert any("Ranking overstatement" in finding for finding in findings)


def test_detects_full_partial_tension() -> None:
    findings = inspect_strength_tensions(
        "The method fully recovers the signal.",
        "The method partially recovers the signal.",
    )

    assert any("Completeness overstatement" in finding for finding in findings)


def test_ignores_strength_terms_in_different_contexts() -> None:
    assert inspect_strength_conflicts(
        "The large model improves accuracy.",
        "The small baseline improves latency.",
    ) == ()
