"""Assertion-status checks for result overclaims."""

from __future__ import annotations

import re
from re import Match

from citeproof.text import tokenize

ASSERTIVE_RESULT_RE = re.compile(
    r"\b(improves?|improved|reduces?|reduced|outperforms?|shows?|demonstrates?)\b",
    re.IGNORECASE,
)
WEAK_STATUS_RE = re.compile(
    r"\b("
    r"future\s+work|hypothesi[sz]e[sd]?|hypothesis|designed\s+to|intended\s+to|"
    r"aims?\s+to|will\s+test|proposed\s+to"
    r")\b",
    re.IGNORECASE,
)
CONFIRMED_STATUS_RE = re.compile(
    r"\b(confirmed|validated|supported|verified|demonstrated)\b",
    re.IGNORECASE,
)
TRIGGER_RE = re.compile(
    r"\b("
    r"aims?|confirmed|designed|demonstrated|demonstrates?|future|hypothesi[sz]e[sd]?|"
    r"hypothesis|improved|improves?|intended|outperforms?|proposed|reduced|reduces?|"
    r"shows?|supported|test|validated|verified|will|work"
    r")\b",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")


def inspect_assertion_status_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return tensions where evidence frames a result as unestablished."""

    if not ASSERTIVE_RESULT_RE.search(claim):
        return ()
    findings: list[str] = []
    for status in WEAK_STATUS_RE.finditer(evidence):
        window = _local_text(evidence, status)
        if CONFIRMED_STATUS_RE.search(window):
            continue
        if ASSERTIVE_RESULT_RE.search(window) and _context_overlaps(claim, window):
            findings.append(
                "Assertion status tension: evidence frames the claimed result as "
                "future, hypothetical, or intended rather than established."
            )
    return tuple(dict.fromkeys(findings))


def _context_overlaps(claim: str, evidence_window: str) -> bool:
    claim_tokens = _content_tokens(claim)
    evidence_tokens = _content_tokens(evidence_window)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.67


def _content_tokens(text: str) -> set[str]:
    return set(tokenize(TRIGGER_RE.sub(" ", text)))


def _local_text(text: str, match: Match[str]) -> str:
    sentence_start = max(text.rfind(".", 0, match.start()), text.rfind("!", 0, match.start()))
    sentence_start = max(sentence_start, text.rfind("?", 0, match.start())) + 1
    sentence_end_candidates = [
        index for index in (text.find(".", match.end()), text.find("!", match.end()), text.find("?", match.end())) if index != -1
    ]
    sentence_end = min(sentence_end_candidates) if sentence_end_candidates else len(text)
    sentence = text[sentence_start:sentence_end]
    offset = sentence_start
    local_start = match.start() - offset
    tokens = tuple(TOKEN_RE.finditer(sentence))
    target = next(
        (index for index, token in enumerate(tokens) if token.start() <= local_start < token.end()),
        None,
    )
    if target is None:
        return sentence
    window = tokens[max(0, target - 6) : min(len(tokens), target + 9)]
    return sentence[window[0].start() : window[-1].end()]
