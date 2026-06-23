"""Detect conflicts in explicit label-to-meaning mappings."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize

MAPPING_RE = re.compile(
    r"\b(?P<key>[A-Za-z][A-Za-z0-9_-]{0,20})\s*=\s*(?P<value>-?\d+|[A-Za-z])\s+"
    r"(?:means?|denotes?|indicates?|corresponds?\s+to)\s+"
    r"(?P<meaning>.+?)(?=,\s*(?:and\s+)?[A-Za-z][A-Za-z0-9_-]{0,20}\s*=|"
    r"\s+and\s+[A-Za-z][A-Za-z0-9_-]{0,20}\s*=|[.;]|$)",
    re.IGNORECASE,
)
MEANING_STOP = {
    "a",
    "an",
    "and",
    "agent",
    "for",
    "immediately",
    "message",
    "next",
    "the",
    "to",
    "user",
    "will",
}


@dataclass(frozen=True)
class Mapping:
    key: str
    value: str
    meaning: str
    tokens: frozenset[str]


def inspect_mapping_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return findings for contradictory explicit label mappings."""

    claim_mappings = _mappings(claim)
    evidence_mappings = _mappings(evidence)
    findings: list[str] = []
    for claim_mapping in claim_mappings:
        for evidence_mapping in evidence_mappings:
            if claim_mapping.key != evidence_mapping.key:
                continue
            if claim_mapping.value == evidence_mapping.value and _meanings_conflict(
                claim_mapping,
                evidence_mapping,
            ):
                findings.append(
                    "Mapping conflict: "
                    f"claim {claim_mapping.key}={claim_mapping.value} means "
                    f"{claim_mapping.meaning} but evidence maps it to {evidence_mapping.meaning}"
                )
            if claim_mapping.value != evidence_mapping.value and _meanings_match(
                claim_mapping,
                evidence_mapping,
            ):
                findings.append(
                    "Mapping conflict: "
                    f"claim maps {claim_mapping.meaning} to {claim_mapping.key}="
                    f"{claim_mapping.value} but evidence maps it to {evidence_mapping.key}="
                    f"{evidence_mapping.value}"
                )
    return tuple(dict.fromkeys(findings))


def _mappings(text: str) -> tuple[Mapping, ...]:
    mappings = []
    for match in MAPPING_RE.finditer(text):
        meaning = _clean_meaning(match.group("meaning"))
        tokens = frozenset(
            _normalize_token(token) for token in tokenize(meaning) if token not in MEANING_STOP
        )
        if tokens:
            mappings.append(
                Mapping(
                    key=match.group("key").casefold(),
                    value=match.group("value").casefold(),
                    meaning=meaning,
                    tokens=tokens,
                )
            )
    return tuple(mappings)


def _clean_meaning(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" ,.;:")


def _meanings_conflict(claim: Mapping, evidence: Mapping) -> bool:
    return not _meanings_match(claim, evidence) and (
        _has_action_polarity_swap(claim.tokens, evidence.tokens)
        or claim.tokens.isdisjoint(evidence.tokens)
    )


def _meanings_match(claim: Mapping, evidence: Mapping) -> bool:
    overlap = claim.tokens & evidence.tokens
    return bool(overlap) and len(overlap) / min(len(claim.tokens), len(evidence.tokens)) >= 0.5


def _has_action_polarity_swap(left: frozenset[str], right: frozenset[str]) -> bool:
    wait_terms = {"wait"}
    reply_terms = {"answer", "reply", "respond", "response"}
    return bool(left & wait_terms and right & reply_terms) or bool(
        left & reply_terms and right & wait_terms
    )


def _normalize_token(token: str) -> str:
    aliases = {
        "answers": "answer",
        "replies": "reply",
        "responds": "respond",
        "waiting": "wait",
        "waits": "wait",
    }
    return aliases.get(token, token)
