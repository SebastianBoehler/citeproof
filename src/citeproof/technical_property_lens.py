"""Controlled technical property conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class TechnicalPropertyGroup:
    label: str
    values: tuple[tuple[str, tuple[str, ...]], ...]


GROUPS = (
    TechnicalPropertyGroup(
        "Complexity",
        (
            ("constant", (r"\bconstant\s+time\b", r"\bo\s*\(\s*1\s*\)",)),
            ("logarithmic", (r"\blogarithmic\b", r"\bo\s*\(\s*log\s*n\s*\)",)),
            ("linear", (r"\blinear\s+(?:time|complexity)\b", r"\bo\s*\(\s*n\s*\)",)),
            (
                "quadratic",
                (r"\bquadratic\s+(?:time|complexity)\b", r"\bo\s*\(\s*n\s*\^?\s*2\s*\)"),
            ),
            (
                "cubic",
                (r"\bcubic\s+(?:time|complexity)\b", r"\bo\s*\(\s*n\s*\^?\s*3\s*\)"),
            ),
            ("exponential", (r"\bexponential\s+(?:time|complexity)\b", r"\bo\s*\(\s*2\^n\s*\)")),
        ),
    ),
    TechnicalPropertyGroup(
        "Inference fidelity",
        (
            ("exact", (r"\bexact\s+inference\b",)),
            ("approximate", (r"\bapproximate\s+inference\b", r"\bapproximation\b")),
        ),
    ),
    TechnicalPropertyGroup(
        "Trainability",
        (
            ("frozen", (r"\bfrozen\b", r"\bkept\s+fixed\b")),
            ("fine-tuned", (r"\bfine[- ]tuned\b", r"\bfine[- ]tuning\b")),
        ),
    ),
    TechnicalPropertyGroup(
        "Reward density",
        (
            ("dense", (r"\bdense\s+rewards?\b",)),
            ("sparse", (r"\bsparse\s+rewards?\b",)),
        ),
    ),
    TechnicalPropertyGroup(
        "Evaluation domain",
        (
            ("in-domain", (r"\bin[- ]domain\b",)),
            ("out-of-domain", (r"\bout[- ]of[- ]domain\b",)),
        ),
    ),
    TechnicalPropertyGroup(
        "Data sensitivity",
        (
            ("private", (r"\bprivate\s+(?:medical\s+)?records?\b", r"\bprivate\s+data\b")),
            ("public", (r"\bpublic\s+(?:medical\s+)?records?\b", r"\bpublic\s+data\b")),
        ),
    ),
    TechnicalPropertyGroup(
        "Trainable scope",
        (
            ("all model weights", (r"\ball\s+(?:model\s+)?weights\b", r"\ball\s+parameters\b")),
            ("adapter weights", (r"\badapter\s+weights\b", r"\blow[- ]rank\s+adapter\s+weights\b")),
            (
                "frozen base weights",
                (
                    r"\b(?:base|model|pretrained)\s+weights\s+(?:are\s+)?frozen\b",
                    r"\bkeeps?\s+(?:base|model|pretrained)\s+weights\s+frozen\b",
                ),
            ),
        ),
    ),
)

TRIGGER_WORDS_RE = re.compile(
    r"\b("
    r"adapter|all|approximate|approximation|base|constant|cubic|data|dense|domain|exact|"
    r"exponential|fine|fixed|frozen|inference|keeps?|kept|linear|logarithmic|"
    r"low|medical|model|out|parameters|pretrained|private|public|quadratic|rank|"
    r"records?|rewards?|sparse|time|tuned|tuning|weights?"
    r")\b",
    re.IGNORECASE,
)


def inspect_technical_property_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return deterministic hard conflicts for controlled technical properties."""

    findings: list[str] = []
    for group in GROUPS:
        claim_values = set(_mentioned_values(group, claim))
        evidence_values = set(_mentioned_values(group, evidence))
        if not claim_values or not evidence_values or claim_values & evidence_values:
            continue
        for claim_value in claim_values:
            for evidence_value in evidence_values:
                if _context_overlaps(claim, evidence):
                    findings.append(
                        f"{group.label} conflict: claim says {claim_value} "
                        f"while evidence says {evidence_value}."
                    )
    return tuple(dict.fromkeys(findings))


def _mentioned_values(group: TechnicalPropertyGroup, text: str) -> tuple[str, ...]:
    values: list[str] = []
    for value, patterns in group.values:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            values.append(value)
    return tuple(values)


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.67


def _context_tokens(text: str) -> set[str]:
    return set(tokenize(TRIGGER_WORDS_RE.sub(" ", text)))
