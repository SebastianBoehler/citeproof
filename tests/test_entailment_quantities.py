from citeproof.entailment import judge_evidence
from citeproof.models import Label


def test_judge_evidence_contradicts_compact_quantity_conflict() -> None:
    judgment = judge_evidence(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues.",
        "Schema-Guided Dialogue contains 15,000 task-oriented dialogues.",
    )

    assert judgment.label == Label.CONTRADICTED


def test_judge_evidence_avoids_unrelated_quantity_contradiction() -> None:
    judgment = judge_evidence(
        "We train on 6000 samples from WildChat.",
        "WildChat contains 1M ChatGPT interaction logs in the wild.",
    )

    assert judgment.label != Label.CONTRADICTED
