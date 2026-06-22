"""Controlled statistical reporting conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.confidence_interval_lens import inspect_confidence_interval_conflicts
from citeproof.pvalue_lens import inspect_p_value_conflicts
from citeproof.ratio_effect_lens import inspect_ratio_effect_conflicts

CONTEXT_STOPWORDS = {
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "has",
    "not",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "with",
}


@dataclass(frozen=True)
class StatisticalGroup:
    label: str
    values: tuple[tuple[str, tuple[str, ...]], ...]


GROUPS = (
    StatisticalGroup(
        "Confidence interval",
        (
            ("includes zero", (r"\bincludes?\s+zero\b",)),
            ("excludes zero", (r"\bexcludes?\s+zero\b",)),
        ),
    ),
    StatisticalGroup(
        "F1 averaging",
        (
            ("macro-F1", (r"\bmacro[- ]?f1\b",)),
            ("micro-F1", (r"\bmicro[- ]?f1\b",)),
        ),
    ),
    StatisticalGroup(
        "Summary statistic",
        (
            ("mean", (r"\bmean\b",)),
            ("median", (r"\bmedian\b",)),
        ),
    ),
    StatisticalGroup(
        "Uncertainty statistic",
        (
            ("standard deviation", (r"\bstandard\s+deviation\b",)),
            ("standard error", (r"\bstandard\s+error\b",)),
        ),
    ),
    StatisticalGroup(
        "Pairedness",
        (
            ("paired", (r"\bpaired\b",)),
            ("unpaired", (r"\bunpaired\b",)),
        ),
    ),
    StatisticalGroup(
        "Tail count",
        (
            ("one-tailed", (r"\bone[- ]tailed\b",)),
            ("two-tailed", (r"\btwo[- ]tailed\b",)),
        ),
    ),
    StatisticalGroup(
        "Test family",
        (
            ("parametric", (r"\bparametric\b",)),
            ("nonparametric", (r"\bnon[- ]?parametric\b",)),
        ),
    ),
)

VALUE_TERMS_RE = re.compile(
    r"\b("
    r"excludes?|includes?|macro[- ]?f1|mean|median|micro[- ]?f1|non[- ]?parametric|"
    r"one[- ]tailed|paired|parametric|standard\s+deviation|standard\s+error|"
    r"p[- ]?value|p|significant|statistically|two[- ]tailed|unpaired|zero"
    r")\b",
    re.IGNORECASE,
)

def inspect_statistical_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return deterministic hard conflicts for controlled statistical reporting."""

    context_overlaps = _context_overlaps(claim, evidence)
    findings: list[str] = []
    findings.extend(inspect_p_value_conflicts(claim, evidence, context_overlaps))
    findings.extend(inspect_confidence_interval_conflicts(claim, evidence, context_overlaps))
    findings.extend(inspect_ratio_effect_conflicts(claim, evidence, context_overlaps))
    for group in GROUPS:
        claim_values = set(_mentioned_values(group, claim))
        evidence_values = set(_mentioned_values(group, evidence))
        if not claim_values or not evidence_values or claim_values & evidence_values:
            continue
        for claim_value in claim_values:
            for evidence_value in evidence_values:
                if context_overlaps:
                    findings.append(
                        f"{group.label} conflict: claim says {claim_value} "
                        f"while evidence says {evidence_value}."
                    )
    return tuple(dict.fromkeys(findings))


def _mentioned_values(group: StatisticalGroup, text: str) -> tuple[str, ...]:
    values: list[str] = []
    for value, patterns in group.values:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            values.append(value)
    if group.label == "Test family" and "nonparametric" in values:
        values = [value for value in values if value != "parametric"]
    return tuple(values)


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.67


def _context_tokens(text: str) -> set[str]:
    terms = re.findall(r"[a-z0-9]+", VALUE_TERMS_RE.sub(" ", text).lower())
    return {term for term in terms if term not in CONTEXT_STOPWORDS and not term.isdigit()}
