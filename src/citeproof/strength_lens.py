"""Deterministic checks for claim-strength overstatements."""

from __future__ import annotations

import re
from collections.abc import Iterable
from re import Match

from citeproof.text import tokenize

MAGNITUDE_NOUNS = (
    "benefits?",
    "decreases?",
    "effects?",
    "gains?",
    "improvements?",
    "increases?",
    "reductions?",
)
MAGNITUDE_OBJECT = rf"(?:\w+\s+){{0,3}}(?:{'|'.join(MAGNITUDE_NOUNS)})"
STRONG_MAGNITUDE_RE = re.compile(
    rf"\b(?P<value>large|substantial)\s+{MAGNITUDE_OBJECT}\b",
    re.IGNORECASE,
)
WEAK_MAGNITUDE_RE = re.compile(
    rf"\b(?P<value>small|modest)\s+{MAGNITUDE_OBJECT}\b",
    re.IGNORECASE,
)
NO_OVERHEAD_RE = re.compile(
    r"\bno(?P<context>(?:\s+\w+){0,5})\s+overheads?\b",
    re.IGNORECASE,
)
WEAK_OVERHEAD_RE = re.compile(
    r"\b(?P<value>small|some|non[- ]?zero)(?P<context>(?:\s+\w+){0,5})"
    r"\s+overheads?\b",
    re.IGNORECASE,
)
CAUSAL_CLAIM_RE = re.compile(
    r"\b(?P<value>causes|caused|causal|causally|proves|demonstrates)\b",
    re.IGNORECASE,
)
WEAK_CAUSAL_RE = re.compile(
    r"\b(?P<value>associations?|associated|correlations?|correlated|suggests?|suggested|may)\b",
    re.IGNORECASE,
)
RANKING_CLAIM_RE = re.compile(
    r"\b(?P<value>best|top[- ]performing|highest)\b",
    re.IGNORECASE,
)
WEAK_RANKING_RE = re.compile(r"\b(?P<value>competitive|comparable)\b", re.IGNORECASE)
COMPLETE_RE = re.compile(r"\b(?P<value>full|fully|complete|completely)\b", re.IGNORECASE)
RECOVERY_RE = re.compile(
    r"\b(recover(?:y|ies|s|ed)?|reconstruct(?:ion|s|ed)?|restor(?:ation|es|ed)?)\b",
    re.IGNORECASE,
)
PARTIAL_RE = re.compile(r"\b(?P<value>partial|partially)\b", re.IGNORECASE)
TRIGGER_WORDS_RE = re.compile(
    r"\b("
    r"associations?|associated|best|causal|causally|caused|causes|comparable|"
    r"competitive|complete|completely|correlations?|correlated|demonstrates|full|fully|"
    r"highest|large|may|modest|no|nonzero|overheads?|partial|partially|proves|"
    r"recover(?:y|ies|s|ed)?|reconstruct(?:ion|s|ed)?|restor(?:ation|es|ed)?|small|"
    r"some|substantial|suggested|suggests?|top|performing|zero"
    r")\b",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")
CLAUSE_BOUNDARY_WORDS = {"and", "but", "whereas", "while"}
CONTEXT_THRESHOLD = 0.67


def inspect_strength_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts where evidence directly weakens claim strength."""

    findings: list[str] = []
    for claim_magnitude in STRONG_MAGNITUDE_RE.finditer(claim):
        if _has_matching_magnitude_evidence(claim, claim_magnitude, evidence):
            continue
        for evidence_magnitude in WEAK_MAGNITUDE_RE.finditer(evidence):
            if _scoped_context_overlaps(claim, claim_magnitude, evidence, evidence_magnitude):
                findings.append(
                    "Magnitude conflict: claim says "
                    f"{claim_magnitude.group('value').lower()} while evidence says "
                    f"{evidence_magnitude.group('value').lower()}."
                )

    for claim_overhead in NO_OVERHEAD_RE.finditer(claim):
        for evidence_overhead in WEAK_OVERHEAD_RE.finditer(evidence):
            if not _overhead_dimensions_compatible(claim_overhead, evidence_overhead):
                continue
            if _scoped_context_overlaps(claim, claim_overhead, evidence, evidence_overhead):
                findings.append(
                    "Overhead conflict: claim says no overhead while evidence says "
                    f"{evidence_overhead.group('value').lower()} overhead."
                )

    return tuple(dict.fromkeys(findings))


def inspect_strength_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return softer strength tensions that should block full support."""

    findings: list[str] = []
    for claim_causal in CAUSAL_CLAIM_RE.finditer(claim):
        for evidence_causal in WEAK_CAUSAL_RE.finditer(evidence):
            if _scoped_context_overlaps(claim, claim_causal, evidence, evidence_causal):
                findings.append(
                    "Causal overstatement tension: claim asserts causality while evidence is weaker."
                )

    for claim_ranking in RANKING_CLAIM_RE.finditer(claim):
        for evidence_ranking in WEAK_RANKING_RE.finditer(evidence):
            if not _ranking_targets_match(claim, claim_ranking, evidence, evidence_ranking):
                continue
            if _scoped_context_overlaps(claim, claim_ranking, evidence, evidence_ranking):
                findings.append(
                    "Ranking overstatement tension: claim asserts top rank while evidence is weaker."
                )

    for claim_complete in COMPLETE_RE.finditer(claim):
        if not _has_local_recovery(claim, claim_complete):
            continue
        for evidence_partial in PARTIAL_RE.finditer(evidence):
            if not _has_local_recovery(evidence, evidence_partial):
                continue
            if _scoped_context_overlaps(claim, claim_complete, evidence, evidence_partial):
                findings.append(
                    "Completeness overstatement tension: "
                    "claim asserts full recovery while evidence is partial."
                )

    return tuple(dict.fromkeys(findings))


def _has_matching_magnitude_evidence(claim: str, match: Match[str], evidence: str) -> bool:
    return any(
        _scoped_context_overlaps(claim, match, evidence, evidence_match)
        for evidence_match in STRONG_MAGNITUDE_RE.finditer(evidence)
    )


def _overhead_dimensions_compatible(left: Match[str], right: Match[str]) -> bool:
    left_tokens = _overhead_dimension_tokens(left)
    right_tokens = _overhead_dimension_tokens(right)
    return not left_tokens or not right_tokens or bool(left_tokens & right_tokens)


def _overhead_dimension_tokens(match: Match[str]) -> set[str]:
    return set(tokenize(match.group("context")))


def _ranking_targets_match(
    claim: str,
    claim_match: Match[str],
    evidence: str,
    evidence_match: Match[str],
) -> bool:
    claim_target = _next_context_token(claim, claim_match)
    evidence_target = _next_context_token(evidence, evidence_match)
    return not claim_target or not evidence_target or claim_target == evidence_target


def _next_context_token(text: str, match: Match[str]) -> str | None:
    for token in TOKEN_RE.finditer(text, match.end()):
        value = token.group(0).lower()
        if value in CLAUSE_BOUNDARY_WORDS:
            return None
        between = text[match.end() : token.start()]
        if re.search(r"[.,;:]", between):
            return None
        if tokenize(value):
            return tokenize(value)[0]
    return None


def _has_local_recovery(text: str, match: Match[str]) -> bool:
    return bool(RECOVERY_RE.search(_local_text(text, match)))


def _scoped_context_overlaps(
    claim: str,
    claim_match: Match[str],
    evidence: str,
    evidence_match: Match[str],
) -> bool:
    claim_tokens = _local_context_tokens(claim, claim_match)
    evidence_tokens = _local_context_tokens(evidence, evidence_match)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= (
        CONTEXT_THRESHOLD
    )


def _local_context_tokens(text: str, match: Match[str]) -> set[str]:
    return _context_tokens(_local_text(text, match))


def _context_tokens(text: str) -> set[str]:
    normalized = re.sub(r"\bnon[- ]?zero\b", " ", text, flags=re.IGNORECASE)
    return set(tokenize(TRIGGER_WORDS_RE.sub(" ", normalized)))


def _local_text(text: str, match: Match[str]) -> str:
    tokens = tuple(TOKEN_RE.finditer(text))
    token_index = _match_token_index(tokens, match)
    if token_index is None:
        return text
    start = token_index
    while start > 0 and not _is_boundary(text, tokens[start - 1], tokens[start]):
        start -= 1
    end = token_index + 1
    while end < len(tokens) and not _is_boundary(text, tokens[end - 1], tokens[end]):
        end += 1
    window = tokens[max(start, token_index - 5) : min(end, token_index + 6)]
    return text[window[0].start() : window[-1].end()]


def _match_token_index(tokens: Iterable[Match[str]], match: Match[str]) -> int | None:
    for index, token in enumerate(tokens):
        if token.start() <= match.start() < token.end() or match.start() <= token.start() < match.end():
            return index
    return None


def _is_boundary(text: str, left: Match[str], right: Match[str]) -> bool:
    if left.group(0).lower() in CLAUSE_BOUNDARY_WORDS or right.group(0).lower() in CLAUSE_BOUNDARY_WORDS:
        return True
    return bool(re.search(r"[.;:]|,\s*$", text[left.end() : right.start()]))
