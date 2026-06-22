"""Optional transformer NLI verifier."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from citeproof.models import EvidenceJudgment, Label

DEFAULT_NLI_MODEL = "facebook/bart-large-mnli"


class TransformersNliJudge:
    """Judge evidence-claim pairs with a Hugging Face NLI model."""

    def __init__(self, model_name: str = DEFAULT_NLI_MODEL, min_confidence: float = 0.55) -> None:
        self.model_name = model_name
        self.min_confidence = min_confidence
        self._classifier: Any | None = None

    def __call__(self, claim: str, evidence: str) -> EvidenceJudgment:
        scores = _scores_by_kind(self._run(evidence, claim))
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

    def _run(self, evidence: str, claim: str) -> Any:
        return self._pipeline()({"text": evidence, "text_pair": claim}, truncation=True)

    def _pipeline(self) -> Any:
        if self._classifier is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "NLI verification requires the optional dependency group: "
                    "uv sync --extra nli"
                ) from exc
            self._classifier = pipeline("text-classification", model=self.model_name, top_k=None)
        return self._classifier


def build_nli_judge(model_name: str | None = None) -> TransformersNliJudge:
    """Create a lazy-loading NLI judge."""

    return TransformersNliJudge(model_name or DEFAULT_NLI_MODEL)


def _scores_by_kind(output: Any) -> dict[str, float]:
    rows = _flatten_output(output)
    scores: dict[str, float] = {}
    for row in rows:
        label = str(row.get("label", "")).lower()
        kind = _label_kind(label)
        if kind is None:
            continue
        scores[kind] = max(scores.get(kind, 0.0), float(row.get("score", 0.0)))
    return scores


def _flatten_output(output: Any) -> list[dict[str, Any]]:
    if isinstance(output, dict):
        return [output]
    if isinstance(output, Sequence) and not isinstance(output, (str, bytes)):
        if output and isinstance(output[0], Sequence) and not isinstance(output[0], dict):
            return [item for group in output for item in group]
        return [item for item in output if isinstance(item, dict)]
    return []


def _label_kind(label: str) -> str | None:
    if "entail" in label:
        return "entailment"
    if "contrad" in label:
        return "contradiction"
    if "neutral" in label:
        return "neutral"
    return None
