"""Evaluation metrics for claim-support labels."""

from __future__ import annotations

import json
from dataclasses import dataclass

from citeproof.models import Label


@dataclass(frozen=True)
class EvalSummary:
    """Aggregate eval metrics."""

    total: int
    accuracy: float
    macro_f1: float
    false_supported_rate: float
    supported_precision: float
    supported_recall: float
    unsupported_recall: float
    contradiction_recall: float
    manual_review_rate: float
    confusion: dict[str, dict[str, int]]

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "accuracy": self.accuracy,
            "macro_f1": self.macro_f1,
            "false_supported_rate": self.false_supported_rate,
            "supported_precision": self.supported_precision,
            "supported_recall": self.supported_recall,
            "unsupported_recall": self.unsupported_recall,
            "contradiction_recall": self.contradiction_recall,
            "manual_review_rate": self.manual_review_rate,
            "confusion": self.confusion,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def summarize(expected: list[Label], predicted: list[Label]) -> EvalSummary:
    """Compute label accuracy, macro-F1, and false-supported rate."""

    if len(expected) != len(predicted):
        raise ValueError("Expected and predicted label counts differ.")
    total = len(expected)
    labels = list(Label)
    confusion = {
        label.value: {inner.value: 0 for inner in labels}
        for label in labels
    }
    for exp, pred in zip(expected, predicted, strict=True):
        confusion[exp.value][pred.value] += 1

    accuracy = _safe_div(sum(exp == pred for exp, pred in zip(expected, predicted, strict=True)), total)
    macro_f1 = sum(_f1(label, confusion) for label in labels) / len(labels)
    false_supported = sum(
        exp != Label.SUPPORTED and pred == Label.SUPPORTED
        for exp, pred in zip(expected, predicted, strict=True)
    )
    manual_review = sum(
        pred in {Label.PARTIALLY_SUPPORTED, Label.UNCERTAIN}
        for pred in predicted
    )
    return EvalSummary(
        total=total,
        accuracy=round(accuracy, 4),
        macro_f1=round(macro_f1, 4),
        false_supported_rate=round(_safe_div(false_supported, total), 4),
        supported_precision=round(_precision(Label.SUPPORTED, confusion), 4),
        supported_recall=round(_recall(Label.SUPPORTED, confusion), 4),
        unsupported_recall=round(_recall(Label.UNSUPPORTED, confusion), 4),
        contradiction_recall=round(_recall(Label.CONTRADICTED, confusion), 4),
        manual_review_rate=round(_safe_div(manual_review, total), 4),
        confusion=confusion,
    )


def _f1(label: Label, confusion: dict[str, dict[str, int]]) -> float:
    precision = _precision(label, confusion)
    recall = _recall(label, confusion)
    return _safe_div(2 * precision * recall, precision + recall)


def _precision(label: Label, confusion: dict[str, dict[str, int]]) -> float:
    tp = confusion[label.value][label.value]
    fp = sum(confusion[other.value][label.value] for other in Label if other != label)
    return _safe_div(tp, tp + fp)


def _recall(label: Label, confusion: dict[str, dict[str, int]]) -> float:
    tp = confusion[label.value][label.value]
    fn = sum(confusion[label.value][other.value] for other in Label if other != label)
    return _safe_div(tp, tp + fn)


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
