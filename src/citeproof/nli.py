"""Optional transformer NLI verifier."""

from __future__ import annotations

import os
from typing import Any

from citeproof.models import EvidenceJudgment, Label

DEFAULT_NLI_MODEL = os.getenv("NLI_MODEL_ID", "cross-encoder/nli-deberta-v3-small")


class TransformersNliJudge:
    """Judge evidence-claim pairs with a local transformers NLI model."""

    def __init__(self, model_name: str = DEFAULT_NLI_MODEL, min_confidence: float = 0.55) -> None:
        self.model_name = model_name
        self.min_confidence = min_confidence
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._labels: dict[int, str] | None = None

    def __call__(self, claim: str, evidence: str) -> EvidenceJudgment:
        scores = self._score_pair(evidence, claim)
        if not scores:
            return EvidenceJudgment(Label.UNCERTAIN, 0.2, "NLI model returned no usable labels.")

        kind, score = max(scores.items(), key=lambda item: item[1])
        confidence = round(float(score), 3)
        if confidence < self.min_confidence:
            return EvidenceJudgment(
                Label.UNCERTAIN,
                confidence,
                f"NLI score was below the confidence floor for {kind}.",
            )
        if kind == "entailment":
            return EvidenceJudgment(Label.SUPPORTED, confidence, "NLI model predicts entailment.")
        if kind == "contradiction":
            return EvidenceJudgment(
                Label.CONTRADICTED,
                confidence,
                "NLI model predicts contradiction.",
            )
        return EvidenceJudgment(Label.UNSUPPORTED, confidence, "NLI model predicts neutral evidence.")

    def _score_pair(self, evidence: str, claim: str) -> dict[str, float]:
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "NLI verification requires the optional dependency group: uv sync --extra nli"
            ) from exc

        tokenizer, model, labels = self._load_model()
        batch = tokenizer(evidence, claim, return_tensors="pt", truncation=True, max_length=512)
        device = next(model.parameters()).device
        batch = {key: value.to(device) for key, value in batch.items()}
        with torch.inference_mode():
            probabilities = torch.softmax(model(**batch).logits[0], dim=-1).tolist()
        return {_label_kind(labels[index]): float(probabilities[index]) for index in labels}

    def _load_model(self) -> tuple[Any, Any, dict[int, str]]:
        if self._tokenizer is None or self._model is None or self._labels is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "NLI verification requires the optional dependency group: uv sync --extra nli"
                ) from exc
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self._labels = clean_label_map(self._model.config.id2label)
            self._model.to(_preferred_device())
            self._model.eval()
        return self._tokenizer, self._model, self._labels


def build_nli_judge(model_name: str | None = None) -> TransformersNliJudge:
    """Create a lazy-loading NLI judge."""

    return TransformersNliJudge(model_name or DEFAULT_NLI_MODEL)


def clean_label_map(labels: dict[int, str]) -> dict[int, str]:
    """Normalize and validate NLI label names."""

    normalized = {key: _label_kind(value) for key, value in labels.items()}
    expected = {"contradiction", "entailment", "neutral"}
    if expected - set(normalized.values()):
        raise ValueError(f"NLI model labels must include {sorted(expected)}.")
    return normalized


def _label_kind(label: str) -> str:
    label = label.lower()
    if "entail" in label:
        return "entailment"
    if "contrad" in label:
        return "contradiction"
    if "neutral" in label:
        return "neutral"
    return label


def _preferred_device() -> str:
    override = os.getenv("CITEPROOF_DEVICE") or os.getenv("TOKEN_UV_DEVICE")
    if override in {"cpu", "cuda", "mps"}:
        return override
    try:
        import torch
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"
