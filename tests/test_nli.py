from citeproof.models import Label
from citeproof.nli import TransformersNliJudge


def test_transformers_nli_judge_maps_entailment() -> None:
    judge = TransformersNliJudge()
    judge._classifier = lambda *_args, **_kwargs: [
        {"label": "ENTAILMENT", "score": 0.91},
        {"label": "NEUTRAL", "score": 0.05},
        {"label": "CONTRADICTION", "score": 0.04},
    ]

    result = judge("Method X improves accuracy.", "Method X improves accuracy by 8%.")

    assert result.label == Label.SUPPORTED
    assert result.confidence == 0.91


def test_transformers_nli_judge_maps_contradiction() -> None:
    judge = TransformersNliJudge()
    judge._classifier = lambda *_args, **_kwargs: [
        {"label": "CONTRADICTION", "score": 0.88},
        {"label": "NEUTRAL", "score": 0.08},
        {"label": "ENTAILMENT", "score": 0.04},
    ]

    result = judge("Method X improves accuracy.", "Method X does not improve accuracy.")

    assert result.label == Label.CONTRADICTED
