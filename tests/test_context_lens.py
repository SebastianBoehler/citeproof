import pytest

from citeproof.context_lens import (
    inspect_component_exclusion_conflicts,
    inspect_context_tensions,
)


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        (
            "The method improves accuracy.",
            "The method improves accuracy only when oracle labels are available.",
        ),
        (
            "The method reduces latency.",
            "The method reduces latency in the simulated setting but not on hardware.",
        ),
        (
            "The model improves performance on ImageNet.",
            "The model improves performance on a 1% ImageNet subset.",
        ),
        (
            "The drug reduces inflammation in humans.",
            "The drug reduces inflammation in mice.",
        ),
        (
            "The drug reduces tumor size in patients.",
            "The drug reduces tumor size in vitro.",
        ),
        (
            "The tool improves productivity.",
            "In one case study, the tool improves productivity.",
        ),
        (
            "The intervention reduces hospital readmissions.",
            "The intervention reduces hospital readmissions among low-risk patients only.",
        ),
        (
            "The detector improves robustness to adversarial prompts.",
            "The detector improves robustness to adversarial prompts "
            "when inputs are pre-filtered by a human moderator.",
        ),
        (
            "The model generalizes to deployment data.",
            "The model generalizes to deployment data when the deployment distribution "
            "matches the training distribution.",
        ),
    ],
)
def test_detects_context_limitations(claim: str, evidence: str) -> None:
    findings = inspect_context_tensions(claim, evidence)

    assert any("Context limitation" in finding for finding in findings)


def test_ignores_matching_simulation_scope() -> None:
    assert inspect_context_tensions(
        "The method reduces latency in simulation.",
        "The method reduces latency in simulation.",
    ) == ()


def test_ignores_matching_case_study_scope() -> None:
    assert inspect_context_tensions(
        "The tool improves productivity in one case study.",
        "In one case study, the tool improves productivity.",
    ) == ()


def test_detects_component_exclusion_conflict() -> None:
    findings = inspect_component_exclusion_conflicts(
        "Retrieval improves factuality.",
        "The no-retrieval ablation improves factuality over the baseline.",
    )

    assert any("Component exclusion conflict" in finding for finding in findings)


def test_ignores_matching_component_exclusion() -> None:
    assert inspect_component_exclusion_conflicts(
        "The no-retrieval ablation improves factuality.",
        "The no-retrieval ablation improves factuality over the baseline.",
    ) == ()
