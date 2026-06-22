from citeproof.models import Label
from citeproof.nli import DEFAULT_NLI_MODEL, TransformersNliJudge, clean_label_map


def test_default_nli_model_matches_attribution_lab_model() -> None:
    assert DEFAULT_NLI_MODEL == "cross-encoder/nli-deberta-v3-small"


def test_transformers_nli_judge_maps_entailment() -> None:
    judge = TransformersNliJudge()
    judge._score_pair = lambda *_args: {
        "entailment": 0.91,
        "neutral": 0.05,
        "contradiction": 0.04,
    }

    result = judge("Method X improves accuracy.", "Method X improves accuracy by 8%.")

    assert result.label == Label.SUPPORTED
    assert result.confidence == 0.91


def test_transformers_nli_judge_maps_contradiction() -> None:
    judge = TransformersNliJudge()
    judge._score_pair = lambda *_args: {
        "contradiction": 0.88,
        "neutral": 0.08,
        "entailment": 0.04,
    }

    result = judge("Method X improves accuracy.", "Method X does not improve accuracy.")

    assert result.label == Label.CONTRADICTED


def test_clean_label_map_accepts_cross_encoder_labels() -> None:
    labels = clean_label_map({0: "contradiction", 1: "entailment", 2: "neutral"})

    assert labels == {0: "contradiction", 1: "entailment", 2: "neutral"}
