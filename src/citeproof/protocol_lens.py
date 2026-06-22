"""Academic protocol and measurement-slot checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class ProtocolGroup:
    label: str
    values: tuple[tuple[str, tuple[str, ...]], ...]


CONFLICT_GROUPS = (
    ProtocolGroup(
        "Correction method",
        (
            ("Bonferroni", (r"\bbonferroni\b",)),
            ("Benjamini-Hochberg", (r"\bbenjamini[- ]hochberg\b", r"\bfdr\b")),
            ("Holm", (r"\bholm\b",)),
        ),
    ),
    ProtocolGroup(
        "Blinding",
        (
            ("blinded", (r"\bblinded\b", r"\bmasked\b")),
            ("unblinded", (r"\bunblinded\b", r"\bnot\s+blinded\b", r"\bopen[- ]label\b")),
        ),
    ),
    ProtocolGroup(
        "Study temporality",
        (
            ("prospective", (r"\bprospective\b",)),
            ("retrospective", (r"\bretrospective\b",)),
        ),
    ),
    ProtocolGroup(
        "Architecture",
        (
            ("encoder-only", (r"\bencoder[- ]only\b",)),
            ("decoder-only", (r"\bdecoder[- ]only\b",)),
            ("encoder-decoder", (r"\bencoder[- ]decoder\b", r"\bseq2seq\b")),
        ),
    ),
    ProtocolGroup(
        "Train-test relation",
        (
            ("disjoint", (r"\bdisjoint\b", r"\bheld[- ]out\b", r"\bno\s+overlap\b")),
            ("overlapping", (r"\bsame\s+(?:patients?|examples?|samples?)\b", r"\boverlap(?:ping)?\b")),
        ),
    ),
    ProtocolGroup(
        "Duplicate preprocessing",
        (
            ("removes duplicates", (r"\bremov(?:e|es|ed)\s+duplicate", r"\bdeduplicat(?:e|es|ed)")),
            ("retains duplicates", (r"\bretain(?:s|ed)?\s+duplicate", r"\bkeep(?:s|ing)?\s+duplicate")),
        ),
    ),
    ProtocolGroup(
        "Commercial availability",
        (
            ("commercial use", (r"\bcommercial\s+use\b", r"\bcommercially\s+usable\b")),
            ("non-commercial only", (r"\bnon[- ]commercial\b", r"\bresearch\s+use\s+only\b")),
        ),
    ),
    ProtocolGroup(
        "Correlation sign",
        (
            ("positive", (r"\bpositively\s+correlated\b", r"\bpositive\s+correlation\b")),
            ("negative", (r"\bnegatively\s+correlated\b", r"\bnegative\s+correlation\b")),
        ),
    ),
    ProtocolGroup(
        "Comparator/control",
        (
            ("placebo", (r"\bplacebo(?:\s+control(?:\s+group)?)?\b",)),
            (
                "usual care",
                (
                    r"\busual\s+care\b",
                    r"\bstandard\s+care\b",
                    r"\btreatment\s+as\s+usual\b",
                ),
            ),
            ("active control", (r"\bactive\s+control(?:\s+group)?\b",)),
            ("sham", (r"\bsham(?:\s+control)?\b",)),
            ("waitlist", (r"\bwait[- ]list(?:\s+control)?\b",)),
        ),
    ),
    ProtocolGroup(
        "Dosing frequency",
        (
            ("twice daily", (r"\btwice\s+daily\b", r"\btwo\s+times\s+(?:per|a)\s+day\b", r"\bbid\b")),
            ("daily", (r"\bdaily\b", r"\bonce\s+daily\b", r"\bevery\s+day\b", r"\bqd\b")),
            ("weekly", (r"\bweekly\b", r"\bonce\s+a\s+week\b", r"\bevery\s+week\b")),
            ("monthly", (r"\bmonthly\b", r"\bonce\s+a\s+month\b", r"\bevery\s+month\b")),
        ),
    ),
)
TENSION_GROUPS = (
    ProtocolGroup(
        "Endpoint",
        (
            ("primary endpoint", (r"\bprimary\s+endpoint\b",)),
            ("secondary endpoint", (r"\bsecondary\s+endpoint\b",)),
        ),
    ),
    ProtocolGroup(
        "Evaluation target",
        (
            ("calibration", (r"\bcalibration\b",)),
            ("discrimination", (r"\bdiscrimination\b",)),
        ),
    ),
)
VALUE_TERMS_RE = re.compile(
    r"\b("
    r"benjamini[- ]hochberg|blinded|bonferroni|calibration|commercial|decoder[- ]only|"
    r"active|bid|control|daily|deduplicat(?:e|es|ed)|discrimination|disjoint|"
    r"encoder[- ]decoder|encoder[- ]only|every|fdr|held[- ]out|holm|masked|monthly|"
    r"negative|non[- ]commercial|once|open[- ]label|overlap(?:ping)?|placebo|positive|"
    r"primary|prospective|qd|remov(?:e|es|ed)|research|retain(?:s|ed)?|retrospective|"
    r"secondary|seq2seq|sham|standard|twice|unblinded|usual|wait[- ]list|weekly"
    r")\b",
    re.IGNORECASE,
)
TRAINING_CODE_RELEASE_RE = re.compile(
    r"\breleas(?:e|es|ed|ing)\s+(?:open[- ]source\s+)?training\s+code\b",
    re.IGNORECASE,
)
TRAINING_CODE_NOT_RELEASED_RE = re.compile(
    r"\b(?:do|does|did)\s+not\s+release\s+training\s+code\b|"
    r"\btraining\s+code\s+(?:is|was|were|remains?|remained)?\s*(?:not\s+released|private)\b",
    re.IGNORECASE,
)


def inspect_protocol_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts for controlled academic protocol slots."""

    findings: list[str] = []
    findings.extend(_release_conflicts(claim, evidence))
    for group in CONFLICT_GROUPS:
        claim_values = set(_mentioned_values(group, claim))
        evidence_values = set(_mentioned_values(group, evidence))
        if not claim_values or not evidence_values or claim_values & evidence_values:
            continue
        if _context_overlaps(claim, evidence):
            findings.extend(
                f"Protocol conflict: {group.label} claim says {claim_value} while evidence says {evidence_value}."
                for claim_value in sorted(claim_values)
                for evidence_value in sorted(evidence_values)
            )
    return tuple(dict.fromkeys(findings))


def inspect_protocol_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return partial-support findings for target swaps that share broader context."""

    findings: list[str] = []
    for group in TENSION_GROUPS:
        claim_values = set(_mentioned_values(group, claim))
        evidence_values = set(_mentioned_values(group, evidence))
        if not claim_values or not evidence_values or claim_values & evidence_values:
            continue
        if _context_overlaps(claim, evidence):
            findings.extend(
                f"Measurement target tension: {group.label} claim says {claim_value} while evidence says {evidence_value}."
                for claim_value in sorted(claim_values)
                for evidence_value in sorted(evidence_values)
            )
    return tuple(dict.fromkeys(findings))


def _mentioned_values(group: ProtocolGroup, text: str) -> tuple[str, ...]:
    values: list[str] = []
    for value, patterns in group.values:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            values.append(value)
    if "non-commercial only" in values:
        values = [value for value in values if value != "commercial use"]
    if "unblinded" in values:
        values = [value for value in values if value != "blinded"]
    if group.label == "Dosing frequency" and "twice daily" in values:
        values = [value for value in values if value != "daily"]
    return tuple(values)


def _release_conflicts(claim: str, evidence: str) -> list[str]:
    if not TRAINING_CODE_RELEASE_RE.search(claim):
        return []
    if not TRAINING_CODE_NOT_RELEASED_RE.search(evidence):
        return []
    if not _context_overlaps(claim, evidence):
        return []
    return [
        "Release conflict: claim says training code is released while evidence says it is not released."
    ]


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.5


def _context_tokens(text: str) -> set[str]:
    return set(tokenize(VALUE_TERMS_RE.sub(" ", text)))
