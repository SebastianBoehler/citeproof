"""Measurement value and benchmark-version conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from citeproof.text import tokenize


@dataclass(frozen=True)
class MetricValue:
    metric: str
    value: Decimal
    text: str


METRIC_NAME = (
    r"accuracy|auprc|auroc|auc|bleu|chrf|f1(?:\s+score)?|loss|perplexity|rouge(?:-\w+)?"
)
METRIC_FORWARD_VALUE_RE = re.compile(
    rf"\b(?P<metric>{METRIC_NAME})\b"
    r"(?:\s+score)?\s*(?:of|=|was|is|achieved|reached|:)\s*"
    r"(?P<value>\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
METRIC_BACKWARD_VALUE_RE = re.compile(
    rf"\b(?P<value>\d+(?:\.\d+)?)\s+(?P<metric>{METRIC_NAME})\b",
    re.IGNORECASE,
)
VERSIONED_BENCHMARK_RE = re.compile(
    r"\b(?P<base>[A-Z][A-Z0-9]{2,})(?:-(?P<variant>[A-Za-z0-9]+))?\b"
)
SLOT_TERMS_RE = re.compile(
    rf"\b(?:{METRIC_NAME}|achieved|benchmark|evaluation|score|set|test|uses?)\b",
    re.IGNORECASE,
)
MIN_CONTEXT_OVERLAP = 0.5


def inspect_measurement_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return conflicts for controlled measurement slots."""

    findings: list[str] = []
    if _context_overlaps(claim, evidence):
        findings.extend(_metric_value_conflicts(claim, evidence))
        findings.extend(_benchmark_version_conflicts(claim, evidence))
    return tuple(dict.fromkeys(findings))


def _metric_value_conflicts(claim: str, evidence: str) -> list[str]:
    findings: list[str] = []
    for claim_value in _metric_values(claim):
        for evidence_value in _metric_values(evidence):
            if claim_value.metric == evidence_value.metric and claim_value.value != evidence_value.value:
                findings.append(
                    "Metric value conflict: claim says "
                    f"{claim_value.text} while evidence says {evidence_value.text}."
                )
    return findings


def _benchmark_version_conflicts(claim: str, evidence: str) -> list[str]:
    findings: list[str] = []
    claim_versions = _benchmark_versions(claim)
    evidence_versions = _benchmark_versions(evidence)
    for base, claim_variant in claim_versions.items():
        if base not in evidence_versions:
            continue
        evidence_variant = evidence_versions[base]
        if claim_variant != evidence_variant:
            claim_name = _benchmark_name(base, claim_variant)
            evidence_name = _benchmark_name(base, evidence_variant)
            findings.append(
                "Benchmark version conflict: claim says "
                f"{claim_name} while evidence says {evidence_name}."
            )
    return findings


def _metric_values(text: str) -> tuple[MetricValue, ...]:
    values: list[MetricValue] = []
    for match in METRIC_FORWARD_VALUE_RE.finditer(text):
        values.append(
            MetricValue(
                _normalize_metric(match.group("metric")),
                Decimal(match.group("value")),
                match.group(0).strip(),
            )
        )
    for match in METRIC_BACKWARD_VALUE_RE.finditer(text):
        if _is_delta_metric(text, match.start()):
            continue
        values.append(
            MetricValue(
                _normalize_metric(match.group("metric")),
                Decimal(match.group("value")),
                match.group(0).strip(),
            )
        )
    return tuple(values)


def _is_delta_metric(text: str, start: int) -> bool:
    prefix = text[max(0, start - 32) : start]
    return bool(re.search(r"\b(?:by|over|more\s+than|less\s+than|at\s+least)\s*$", prefix, re.IGNORECASE))


def _normalize_metric(metric: str) -> str:
    normalized = metric.casefold().replace(" ", "")
    if normalized == "auc":
        return "auroc"
    if normalized.startswith("f1"):
        return "f1"
    return normalized


def _benchmark_versions(text: str) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for match in VERSIONED_BENCHMARK_RE.finditer(text):
        base = match.group("base")
        variant = match.group("variant")
        if base in _metric_bases():
            continue
        versions[base] = variant.casefold() if variant else None
    return versions


def _metric_bases() -> set[str]:
    return {"AUC", "AUROC", "AUPRC", "BLEU", "CHRF", "F1", "ROUGE"}


def _benchmark_name(base: str, variant: str | None) -> str:
    return base if variant is None else f"{base}-{variant}"


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = set(tokenize(SLOT_TERMS_RE.sub(" ", claim)))
    evidence_tokens = set(tokenize(SLOT_TERMS_RE.sub(" ", evidence)))
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= (
        MIN_CONTEXT_OVERLAP
    )
