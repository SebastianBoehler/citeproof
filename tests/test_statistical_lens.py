from citeproof.statistical_lens import inspect_statistical_conflicts


def test_detects_confidence_interval_relation_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The confidence interval excludes zero.",
        "The 95% confidence interval includes zero.",
    )

    assert any("Confidence interval conflict" in finding for finding in findings)


def test_detects_f1_averaging_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The system improves macro-F1.",
        "The system improves micro-F1.",
    )

    assert any("F1 averaging conflict" in finding for finding in findings)


def test_detects_summary_statistic_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The paper reports median latency.",
        "The paper reports mean latency.",
    )

    assert any("Summary statistic conflict" in finding for finding in findings)


def test_detects_uncertainty_statistic_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The error bars show standard deviation.",
        "The error bars show standard error.",
    )

    assert any("Uncertainty statistic conflict" in finding for finding in findings)


def test_detects_pairedness_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The test uses a paired bootstrap.",
        "The test uses an unpaired bootstrap.",
    )

    assert any("Pairedness conflict" in finding for finding in findings)


def test_detects_tail_count_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The analysis uses a one-tailed test.",
        "The analysis uses a two-tailed test.",
    )

    assert any("Tail count conflict" in finding for finding in findings)


def test_detects_test_family_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The method uses a parametric test.",
        "The method uses a nonparametric test.",
    )

    assert any("Test family conflict" in finding for finding in findings)


def test_detects_hyphenated_test_family_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The method uses a parametric test.",
        "The method uses a non-parametric test.",
    )

    assert any("Test family conflict" in finding for finding in findings)


def test_detects_spaced_test_family_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The method uses a parametric test.",
        "The method uses a non parametric test.",
    )

    assert any("Test family conflict" in finding for finding in findings)


def test_detects_explicit_p_value_threshold_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The model improvement has p < 0.05.",
        "The model improvement has p = 0.08.",
    )

    assert any("P-value conflict" in finding for finding in findings)


def test_detects_significance_wording_p_value_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The model improvement is statistically significant.",
        "The model improvement has p = 0.08.",
    )

    assert any("P-value conflict" in finding for finding in findings)


def test_detects_not_significant_wording_p_value_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The model improvement is not statistically significant.",
        "The model improvement has p = 0.01.",
    )

    assert any("P-value conflict" in finding for finding in findings)


def test_ignores_matching_significant_p_value() -> None:
    findings = inspect_statistical_conflicts(
        "The model improvement is statistically significant.",
        "The model improvement has p = 0.01.",
    )

    assert not any("P-value conflict" in finding for finding in findings)


def test_ignores_matching_explicit_p_value_relation() -> None:
    findings = inspect_statistical_conflicts(
        "The model improvement has p < 0.05.",
        "The model improvement has p = 0.01.",
    )

    assert not any("P-value conflict" in finding for finding in findings)


def test_detects_numeric_ci_includes_zero_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The treatment effect confidence interval excludes zero.",
        "The treatment effect 95% confidence interval was [-0.10, 0.30].",
    )

    assert any("Confidence interval conflict" in finding for finding in findings)


def test_detects_numeric_ci_excludes_zero_conflict() -> None:
    findings = inspect_statistical_conflicts(
        "The treatment effect confidence interval includes zero.",
        "The treatment effect 95% confidence interval was [0.10, 0.30].",
    )

    assert any("Confidence interval conflict" in finding for finding in findings)


def test_significance_conflicts_with_ci_including_zero() -> None:
    findings = inspect_statistical_conflicts(
        "The treatment effect is statistically significant.",
        "The treatment effect 95% confidence interval was [-0.10, 0.30].",
    )

    assert any("Confidence interval conflict" in finding for finding in findings)


def test_not_significant_conflicts_with_ci_excluding_zero() -> None:
    findings = inspect_statistical_conflicts(
        "The treatment effect is not statistically significant.",
        "The treatment effect 95% confidence interval was [0.10, 0.30].",
    )

    assert any("Confidence interval conflict" in finding for finding in findings)


def test_ignores_matching_numeric_ci_relation() -> None:
    findings = inspect_statistical_conflicts(
        "The treatment effect confidence interval excludes zero.",
        "The treatment effect 95% confidence interval was [0.10, 0.30].",
    )

    assert not any("Confidence interval conflict" in finding for finding in findings)


def test_ignores_evidence_with_claim_value_plus_extra_value() -> None:
    findings = inspect_statistical_conflicts(
        "The paper reports median latency.",
        "The paper reports median latency and mean latency.",
    )

    assert findings == ()


def test_ignores_f1_averaging_in_different_cohorts() -> None:
    findings = inspect_statistical_conflicts(
        "Macro-F1 improves for cohort A.",
        "Micro-F1 improves for cohort B.",
    )

    assert findings == ()


def test_ignores_statistical_terms_in_different_contexts() -> None:
    findings = inspect_statistical_conflicts(
        "The macro scheduler improves throughput.",
        "The system improves micro-F1.",
    )

    assert findings == ()
