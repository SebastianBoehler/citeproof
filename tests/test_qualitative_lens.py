from citeproof.qualitative_lens import (
    inspect_qualitative_conflicts,
    inspect_qualitative_tensions,
)


def test_detects_exclusivity_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "Method X is the only method evaluated on sparse-reward tasks.",
        "Method X is one of three methods evaluated on sparse-reward tasks.",
    )

    assert any("Exclusivity conflict" in finding for finding in findings)


def test_detects_significance_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "Method X significantly improves accuracy.",
        "Method X improves accuracy, but the improvement is not statistically significant.",
    )

    assert any("Significance conflict" in finding for finding in findings)


def test_detects_sota_negation_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "Method X achieves state-of-the-art accuracy on GLUE.",
        "Method X does not achieve state-of-the-art accuracy on GLUE.",
    )

    assert any("State-of-the-art conflict" in finding for finding in findings)


def test_detects_requirement_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "Method X requires no labeled data.",
        "Method X requires labeled data for training.",
    )

    assert any("Requirement conflict" in finding for finding in findings)


def test_detects_descriptor_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "The policy uses a transformer architecture.",
        "The policy uses a convolutional architecture.",
    )

    assert any("Descriptor conflict" in finding for finding in findings)


def test_detects_offline_online_conflict() -> None:
    findings = inspect_qualitative_conflicts(
        "The method uses offline reinforcement learning.",
        "The method uses online reinforcement learning.",
    )

    assert any("Descriptor conflict" in finding for finding in findings)


def test_detects_universal_scope_tension() -> None:
    findings = inspect_qualitative_tensions(
        "Method X improves performance on all evaluated tasks.",
        "Method X improves performance on most evaluated tasks.",
    )

    assert any("Scope tension" in finding for finding in findings)


def test_ignores_descriptor_terms_in_different_contexts() -> None:
    findings = inspect_qualitative_conflicts(
        "The transformer policy improves accuracy.",
        "The convolutional baseline is included for comparison.",
    )

    assert findings == ()


def test_ignores_offline_online_terms_in_different_contexts() -> None:
    findings = inspect_qualitative_conflicts(
        "The offline dataset is public.",
        "The online RL method uses the dataset.",
    )

    assert findings == ()
