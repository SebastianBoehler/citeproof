"""Outcome status and mixed-effect checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class OutcomeTerm:
    name: str
    patterns: tuple[str, ...]
    lower_is_better: bool = False


OUTCOMES = (
    OutcomeTerm("accuracy", (r"\baccuracy\b",)),
    OutcomeTerm("calibration", (r"\bcalibration\b",)),
    OutcomeTerm("discrimination", (r"\bdiscrimination\b",)),
    OutcomeTerm("factuality", (r"\bfactuality\b",)),
    OutcomeTerm("hallucinations", (r"\bhallucinations?\b",), lower_is_better=True),
    OutcomeTerm("latency", (r"\blatency\b",), lower_is_better=True),
    OutcomeTerm("mean absolute error", (r"\bmean\s+absolute\s+error\b", r"\bmae\b"), True),
    OutcomeTerm("loss", (r"\bloss\b",), True),
    OutcomeTerm("perplexity", (r"\bperplexity\b",), True),
    OutcomeTerm("mortality", (r"\bmortality\b",), True),
    OutcomeTerm("readmissions", (r"\breadmissions?\b",), True),
)
RESULT_RE = re.compile(
    r"\b(improves?|improved|reduces?|reduced|decreases?|decreased|lowers?|lowered)\b",
    re.IGNORECASE,
)
NO_CHANGE_RE = re.compile(
    r"\b("
    r"unchanged|no\s+change|shows?\s+no\s+change|no\s+difference|"
    r"no\s+(?:statistically\s+significant\s+)?(?:improvement|reduction)|"
    r"does\s+not\s+(?:improve|reduce|decrease)|did\s+not\s+(?:improve|reduce|decrease)"
    r")\b",
    re.IGNORECASE,
)
IMPROVE_RE = re.compile(
    r"\b(improves?|improved|increases?|increased|higher|better)\b",
    re.IGNORECASE,
)
WORSEN_RE = re.compile(
    r"\b(worsens?|worse|reduces?|reduced|decreases?|decreased|lowers?|lowered)\b",
    re.IGNORECASE,
)
HIGHER_RE = re.compile(r"\b(higher|increased|larger|greater)\b", re.IGNORECASE)
MIXED_CUE_RE = re.compile(r"\b(but|whereas|while|although|however)\b", re.IGNORECASE)
VALUE_TERMS_RE = re.compile(
    r"\b("
    r"accuracy|calibration|decreas(?:e|es|ed)|discrimination|factuality|greater|"
    r"hallucinations?|higher|improv(?:e|es|ed)|increas(?:e|es|ed)|larger|latency|"
    r"loss|lowers?|lowered|mae|mean\s+absolute\s+error|mortality|perplexity|"
    r"readmissions?|reduc(?:e|es|ed)|unchanged|worse|worsens?"
    r")\b",
    re.IGNORECASE,
)


def inspect_outcome_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts for outcome status or direction."""

    if not RESULT_RE.search(claim):
        return ()
    findings: list[str] = []
    shared = _mentioned_outcomes(claim) & _mentioned_outcomes(evidence)
    for outcome in sorted(shared):
        if _outcome_has_no_change(outcome, evidence):
            findings.append(
                "Outcome status conflict: claim asserts a result for "
                f"{outcome} while evidence says it is unchanged."
            )
        if _lower_is_better(outcome) and _outcome_has_higher_direction(outcome, evidence):
            findings.append(
                "Lower-is-better outcome conflict: evidence reports higher "
                f"{outcome} against an improvement claim."
            )
    return tuple(dict.fromkeys(finding for finding in findings if _context_overlaps(claim, evidence)))


def inspect_outcome_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return partial-support findings for mixed effects on the claimed outcome."""

    if not RESULT_RE.search(claim) or not MIXED_CUE_RE.search(evidence):
        return ()
    findings: list[str] = []
    shared = _mentioned_outcomes(claim) & _mentioned_outcomes(evidence)
    for outcome in sorted(shared):
        if _has_mixed_effect(outcome, evidence):
            findings.append(
                "Mixed outcome effect: evidence supports "
                f"{outcome} in one setting but reports the opposite in another."
            )
    return tuple(dict.fromkeys(finding for finding in findings if _context_overlaps(claim, evidence)))


def _mentioned_outcomes(text: str) -> set[str]:
    outcomes: set[str] = set()
    for outcome in OUTCOMES:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in outcome.patterns):
            outcomes.add(outcome.name)
    return outcomes


def _outcome_has_no_change(outcome: str, text: str) -> bool:
    patterns = next(item.patterns for item in OUTCOMES if item.name == outcome)
    return any(_no_change_binds_to_pattern(pattern, text) for pattern in patterns)


def _outcome_has_higher_direction(outcome: str, text: str) -> bool:
    return any(HIGHER_RE.search(window) for window in _outcome_windows(outcome, text))


def _has_mixed_effect(outcome: str, text: str) -> bool:
    windows = _outcome_windows(outcome, text)
    return any(IMPROVE_RE.search(window) for window in windows) and any(
        WORSEN_RE.search(window) for window in windows
    )


def _outcome_windows(outcome: str, text: str) -> tuple[str, ...]:
    outcome_patterns = next(item.patterns for item in OUTCOMES if item.name == outcome)
    windows: list[str] = []
    for pattern in outcome_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 72)
            end = min(len(text), match.end() + 72)
            windows.append(text[start:end])
    return tuple(windows)


def _no_change_binds_to_pattern(pattern: str, text: str) -> bool:
    term = f"(?:{pattern})"
    direct_patterns = (
        rf"{term}.{{0,40}}\b(?:is|was|were|shows?|showed|remains?|remained)?\s*"
        r"(?:unchanged|no\s+change|no\s+difference)\b",
        rf"\bno\s+(?:statistically\s+significant\s+)?(?:improvement|reduction|change|difference)"
        rf"\s+(?:in|for)\s+{term}",
        rf"\bno\s+{term}\s+(?:improvement|reduction|change|difference)\b",
        rf"\b(?:does|did)\s+not\s+(?:improve|reduce|decrease)\s+{term}",
    )
    return any(re.search(item, text, re.IGNORECASE) for item in direct_patterns)


def _lower_is_better(outcome: str) -> bool:
    return next(item.lower_is_better for item in OUTCOMES if item.name == outcome)


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.5


def _context_tokens(text: str) -> set[str]:
    return set(tokenize(VALUE_TERMS_RE.sub(" ", text)))
