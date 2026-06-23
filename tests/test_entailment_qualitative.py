import pytest

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import FailureMode, Label


@pytest.mark.parametrize(
    ("claim", "evidence", "label"),
    [
        (
            "Method X is the only method evaluated on sparse-reward tasks.",
            "Method X is one of three methods evaluated on sparse-reward tasks.",
            Label.CONTRADICTED,
        ),
        (
            "Method X improves performance on all evaluated tasks.",
            "Method X improves performance on most evaluated tasks.",
            Label.PARTIALLY_SUPPORTED,
        ),
        (
            "Method X achieves state-of-the-art accuracy on GLUE.",
            "Method X does not achieve state-of-the-art accuracy on GLUE.",
            Label.CONTRADICTED,
        ),
        (
            "Method X requires no labeled data.",
            "Method X requires labeled data for training.",
            Label.CONTRADICTED,
        ),
        (
            "The policy uses a transformer architecture.",
            "The policy uses a convolutional architecture.",
            Label.CONTRADICTED,
        ),
        (
            "The method uses offline reinforcement learning.",
            "The method uses online reinforcement learning.",
            Label.CONTRADICTED,
        ),
        (
            "Method X significantly improves accuracy.",
            "Method X improves accuracy, but the improvement is not statistically significant.",
            Label.CONTRADICTED,
        ),
        (
            "Perplexity is a good indicator of long-text understanding ability.",
            "Perplexity can not be a good indicator for long text understanding ability.",
            Label.CONTRADICTED,
        ),
        (
            "The long-text perplexity paper concludes that perplexity is a good "
            "indicator of long-text understanding ability.",
            "Considering PPL can not be a good indicator for long text understanding "
            "ability, we call for more diversified evaluation metrics.",
            Label.CONTRADICTED,
        ),
        (
            "The system solves exact policy learning tractably.",
            "Exact policy learning for POMDPs is intractable, hence efficient "
            "approximation techniques must be used.",
            Label.CONTRADICTED,
        ),
        (
            "The simple two-step retrieval solution is sufficient because suggestions "
            "are guaranteed to be relevant to the original query.",
            "However, we will show that the simple solution does not work. For one "
            "thing, the suggestion is not guaranteed to be relevant to the query.",
            Label.CONTRADICTED,
        ),
    ],
)
def test_judge_evidence_uses_qualitative_lens(
    claim: str,
    evidence: str,
    label: Label,
) -> None:
    judgment = judge_evidence(claim, evidence)

    assert judgment.label == label


@pytest.mark.parametrize(
    ("claim", "evidence", "failure_mode"),
    [
        (
            "Method X is the only method evaluated on sparse-reward tasks.",
            "Method X is one of three methods evaluated on sparse-reward tasks.",
            FailureMode.SCOPE_OVERSTATEMENT,
        ),
        (
            "Method X improves performance on all evaluated tasks.",
            "Method X improves performance on most evaluated tasks.",
            FailureMode.SCOPE_OVERSTATEMENT,
        ),
        (
            "Method X achieves state-of-the-art accuracy on GLUE.",
            "Method X does not achieve state-of-the-art accuracy on GLUE.",
            FailureMode.NEGATION_CONFLICT,
        ),
        (
            "Method X requires no labeled data.",
            "Method X requires labeled data for training.",
            FailureMode.NEGATION_CONFLICT,
        ),
        (
            "The policy uses a transformer architecture.",
            "The policy uses a convolutional architecture.",
            FailureMode.NEGATION_CONFLICT,
        ),
        (
            "Method X significantly improves accuracy.",
            "Method X improves accuracy, but the improvement is not statistically significant.",
            FailureMode.NEGATION_CONFLICT,
        ),
        (
            "Perplexity is a good indicator of long-text understanding ability.",
            "Perplexity can not be a good indicator for long text understanding ability.",
            FailureMode.NEGATION_CONFLICT,
        ),
        (
            "The long-text perplexity paper concludes that perplexity is a good "
            "indicator of long-text understanding ability.",
            "Considering PPL can not be a good indicator for long text understanding "
            "ability, we call for more diversified evaluation metrics.",
            FailureMode.NEGATION_CONFLICT,
        ),
        (
            "The system solves exact policy learning tractably.",
            "Exact policy learning for POMDPs is intractable, hence efficient "
            "approximation techniques must be used.",
            FailureMode.NEGATION_CONFLICT,
        ),
        (
            "The simple two-step retrieval solution is sufficient because suggestions "
            "are guaranteed to be relevant to the original query.",
            "However, we will show that the simple solution does not work. For one "
            "thing, the suggestion is not guaranteed to be relevant to the query.",
            FailureMode.NEGATION_CONFLICT,
        ),
    ],
)
def test_adjudicator_maps_qualitative_failure_modes(
    claim: str,
    evidence: str,
    failure_mode: FailureMode,
) -> None:
    judgment = adjudicate_evidence(claim, evidence)

    assert judgment.failure_mode == failure_mode
