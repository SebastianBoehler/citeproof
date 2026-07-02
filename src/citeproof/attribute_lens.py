"""Controlled academic attribute conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class AttributeGroup:
    label: str
    values: tuple[tuple[str, tuple[str, ...]], ...]


GROUPS = (
    AttributeGroup(
        "Modality",
        (
            ("images", (r"\bimages?\b", r"\bvisual\b")),
            ("text", (r"\btexts?\b", r"\btextual\b")),
            ("audio", (r"\baudio\b", r"\bspeech\b")),
            ("video", (r"\bvideos?\b",)),
            ("tabular", (r"\btabular\b", r"\btable\s+data\b")),
        ),
    ),
    AttributeGroup(
        "Task",
        (
            ("summarization", (r"\bsummari[sz]ation\b", r"\bsummari[sz]e\b")),
            ("translation", (r"\btranslation\b", r"\btranslate\b")),
            ("classification", (r"\bclassification\b", r"\bclassify\b")),
            ("segmentation", (r"\bsegmentation\b", r"\bsegment\b")),
            ("retrieval", (r"\bretrieval\b", r"\bretrieve\b")),
        ),
    ),
    AttributeGroup(
        "Split",
        (
            ("train", (r"\btrain(?:ing)?\s+set\b", r"\btrain(?:ing)?\s+split\b")),
            (
                "validation",
                (r"\bvalidation\s+set\b", r"\bvalidation\s+split\b", r"\bdev\s+set\b"),
            ),
            ("test", (r"\btest\s+set\b", r"\btest\s+split\b")),
        ),
    ),
    AttributeGroup(
        "Language",
        (
            ("English", (r"\bEnglish\b",)),
            ("German", (r"\bGerman\b",)),
            ("French", (r"\bFrench\b",)),
            ("Spanish", (r"\bSpanish\b",)),
            ("Chinese", (r"\bChinese\b",)),
        ),
    ),
    AttributeGroup(
        "Optimizer",
        (
            ("AdamW", (r"\bAdamW\b",)),
            ("Adam", (r"\bAdam\b",)),
            ("SGD", (r"\bSGD\b", r"\bstochastic gradient descent\b")),
            ("RMSProp", (r"\bRMSProp\b",)),
        ),
    ),
    AttributeGroup(
        "Availability",
        (
            (
                "public",
                (
                    r"\bpublicly\s+available\b",
                    r"\bopen\s+source\b",
                    r"\bopen\s+(?:model\s+)?weights?\b",
                ),
            ),
            (
                "private",
                (
                    r"\bnot(?:\s+\w+){0,3}\s+publicly\s+available\b",
                    r"\bclosed\s+(?:model\s+)?weights?\b",
                    r"\bunavailable\b",
                    r"\bprivate\b",
                    r"\bproprietary\b",
                ),
            ),
        ),
    ),
    AttributeGroup(
        "Supervision",
        (
            ("supervised", (r"\bsupervised\b", r"\blabeled\s+(?:data|examples|labels)\b")),
            ("unsupervised", (r"\bunsupervised\b", r"\bwithout\s+labels\b")),
        ),
    ),
    AttributeGroup(
        "Study design",
        (
            ("randomized", (r"\brandomi[sz]ed\b", r"\brandomi[sz]ed\s+controlled\b")),
            ("observational", (r"\bobservational\b", r"\bnot\s+randomi[sz]ed\b")),
        ),
    ),
    AttributeGroup(
        "Summarization style",
        (
            ("abstractive", (r"\babstractive\b",)),
            ("extractive", (r"\bextractive\b",)),
        ),
    ),
    AttributeGroup(
        "Agent setting",
        (
            ("single-agent", (r"\bsingle[- ]agent\b",)),
            ("multi-agent", (r"\bmulti[- ]agent\b",)),
        ),
    ),
)

TRIGGER_WORDS_RE = re.compile(
    r"\b("
    r"abstractive|adamw?|audio|available|chinese|classification|classify|"
    r"closed|dev|english|extractive|french|german|gradient|images?|labeled|labels|"
    r"multi-agent|not|observational|open|optimization|private|proprietary|"
    r"publicly|randomi[sz]ed|retrieval|retrieve|rmsprop|segmentation|segment|"
    r"sgd|single-agent|source|spanish|speech|stochastic|summari[sz]ation|"
    r"summari[sz]e|supervised|tabular|tables?|test|text|texts?|textual|"
    r"train(?:ing)?|translate|translation|unsupervised|validation|videos?|visual"
    r")\b",
    re.IGNORECASE,
)


def inspect_attribute_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return deterministic hard conflicts for controlled academic attributes."""

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


def _mentioned_values(group: AttributeGroup, text: str) -> tuple[str, ...]:
    values: list[str] = []
    for value, patterns in group.values:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            values.append(value)
    if group.label == "Availability" and "private" in values:
        values = [value for value in values if value != "public"]
    if group.label == "Study design" and "observational" in values:
        if re.search(r"\bnot\s+randomi[sz]ed\b", text, re.IGNORECASE):
            values = [value for value in values if value != "randomized"]
    return tuple(values)


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.67


def _context_tokens(text: str) -> set[str]:
    return set(tokenize(TRIGGER_WORDS_RE.sub(" ", text)))
