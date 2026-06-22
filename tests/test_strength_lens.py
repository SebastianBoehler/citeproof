import pytest

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


@pytest.mark.parametrize("value", ["some", "nonzero", "non-zero"])
def test_detects_other_weak_overhead_conflicts(value: str) -> None:
    findings = inspect_strength_conflicts(
        "The method adds no computational overhead.",
        f"The method adds {value} computational overhead.",
    )

    assert any("Overhead conflict" in finding for finding in findings)


def test_detects_causal_association_tension() -> None:
    findings = inspect_strength_tensions(
        "The intervention causes improved accuracy.",
        "The intervention is associated with improved accuracy.",
    )

    assert any("Causal overstatement" in finding for finding in findings)


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        (
            "The treatment has a causal effect on recovery.",
            "The treatment has an association with recovery.",
        ),
        (
            "The variable causes higher mortality.",
            "The variable has a correlation with higher mortality.",
        ),
        (
            "The intervention causes improved accuracy.",
            "The intervention suggests improved accuracy.",
        ),
    ],
)
def test_detects_causal_tension_word_forms(claim: str, evidence: str) -> None:
    findings = inspect_strength_tensions(claim, evidence)

    assert any("Causal overstatement" in finding for finding in findings)


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        (
            "Higher temperature leads to increased failure rates.",
            "Higher temperature is correlated with increased failure rates.",
        ),
        (
            "The policy resulted in lower dropout rates.",
            "The policy was studied in an observational cohort with lower dropout rates.",
        ),
    ],
)
def test_detects_broader_causal_overstatement_forms(claim: str, evidence: str) -> None:
    findings = inspect_strength_tensions(claim, evidence)

    assert any("Causal overstatement" in finding for finding in findings)


def test_detects_best_competitive_tension() -> None:
    findings = inspect_strength_tensions(
        "The method achieves the best accuracy.",
        "The method achieves competitive accuracy.",
    )

    assert any("Ranking overstatement" in finding for finding in findings)


def test_detects_best_comparable_tension() -> None:
    findings = inspect_strength_tensions(
        "The method achieves the highest accuracy.",
        "The method achieves comparable accuracy.",
    )

    assert any("Ranking overstatement" in finding for finding in findings)


def test_detects_full_partial_tension() -> None:
    findings = inspect_strength_tensions(
        "The method fully recovers the signal.",
        "The method partially recovers the signal.",
    )

    assert any("Completeness overstatement" in finding for finding in findings)


def test_detects_full_recovery_word_form() -> None:
    findings = inspect_strength_tensions(
        "The method provides full recovery of the signal.",
        "The method provides partial recovery of the signal.",
    )

    assert any("Completeness overstatement" in finding for finding in findings)


def test_ignores_strength_terms_in_different_contexts() -> None:
    assert inspect_strength_conflicts(
        "The large model improves accuracy.",
        "The small baseline improves latency.",
    ) == ()


def test_ignores_causal_tension_in_unrelated_clause() -> None:
    assert inspect_strength_tensions(
        "The treatment causes recovery, and dosage is recorded.",
        "The treatment improves recovery, and dosage is associated with toxicity.",
    ) == ()


def test_ignores_ranking_terms_for_different_targets() -> None:
    assert inspect_strength_tensions(
        "The best baseline improves GLUE accuracy.",
        "The competitive method improves GLUE accuracy.",
    ) == ()


def test_ignores_mixed_magnitude_evidence() -> None:
    assert inspect_strength_conflicts(
        "The method yields a large improvement.",
        "The method yields a large improvement on A and a small improvement on B.",
    ) == ()


def test_ignores_different_overhead_dimensions() -> None:
    assert inspect_strength_conflicts(
        "The method adds no computational overhead.",
        "The method adds no computational overhead but small memory overhead.",
    ) == ()
