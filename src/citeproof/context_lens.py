"""Context limitation and component exclusion checks."""

from __future__ import annotations

import re

from citeproof.text import tokenize

RESULT_RE = re.compile(
    r"\b(generali[sz]es?|improves?|improved|reduces?|reduced|increases?|increased|outperforms?)\b",
    re.IGNORECASE,
)
CONDITION_LIMIT_RE = re.compile(
    r"\b(only\s+(?:when|if)|when|if|assuming|provided\s+that|under\s+oracle|with\s+oracle)\b",
    re.IGNORECASE,
)
SUBGROUP_LIMIT_RE = re.compile(r"\bamong\s+[A-Za-z0-9 -]{1,80}\s+only\b", re.IGNORECASE)
SUBSET_LIMIT_RE = re.compile(
    r"\b(?:\d+(?:\.\d+)?%|one\s+percent|small|limited)\s+"
    r"(?:[A-Za-z0-9-]+\s+){0,2}subset\b|"
    r"\bsubset\b|"
    r"\b(?:one|single)\s+case\s+study\b|"
    r"\bsingle[- ]site\b",
    re.IGNORECASE,
)
CASE_STUDY_RE = re.compile(r"\b(?:one|single)\s+case\s+study\b|\bcase\s+study\b", re.IGNORECASE)
SIMULATION_RE = re.compile(r"\bsimulat(?:ed|ion)\b", re.IGNORECASE)
HARDWARE_RE = re.compile(r"\bhardware\b|\breal[- ]world\b", re.IGNORECASE)
IN_VITRO_RE = re.compile(r"\bin\s+vitro\b|\bex\s+vivo\b", re.IGNORECASE)
HUMAN_RE = re.compile(r"\bhumans?\b|\bpatients?\b|\badults?\b", re.IGNORECASE)
ANIMAL_RE = re.compile(r"\bmice\b|\bmouse\b|\brats?\b", re.IGNORECASE)
CHILD_RE = re.compile(r"\bchildren\b|\bpediatric\b", re.IGNORECASE)
COMPONENT_RESULT_RE = re.compile(
    r"\b(?P<component>retrieval|reranking|attention|adapter|pretraining)\s+"
    r"(?:improves?|improved|reduces?|reduced|increases?|increased|outperforms?)\b",
    re.IGNORECASE,
)
EXCLUSION_TEMPLATE = (
    r"\bno[- ]{component}\b|"
    r"\bwithout\s+{component}\b|"
    r"\b{component}\s+(?:removed|excluded|disabled|ablated)\b"
)
TRIGGER_RE = re.compile(
    r"\b("
    r"ablation|adults?|case|children|ex|hardware|humans?|if|in|mice|mouse|only|"
    r"oracle|patients?|pediatric|rats?|real|simulated|simulation|single|site|study|"
    r"subset|under|vitro|when|with|without"
    r")\b",
    re.IGNORECASE,
)


def inspect_context_tensions(claim: str, evidence: str) -> tuple[str, ...]:
    """Return partial-support findings for evidence narrower than the claim."""

    if not RESULT_RE.search(claim) or not RESULT_RE.search(evidence):
        return ()
    findings: list[str] = []
    if _evidence_is_limited_beyond_claim(claim, evidence):
        findings.append("Context limitation: evidence supports a narrower setting than the claim.")
    if _setting_mismatch(claim, evidence):
        findings.append("Context limitation: evidence is from a different population or setting.")
    if findings and not _context_overlaps(claim, evidence):
        return ()
    return tuple(dict.fromkeys(findings))


def inspect_component_exclusion_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts where evidence excludes the claimed component."""

    findings: list[str] = []
    for component in _claimed_result_components(claim):
        if _claim_excludes_component(claim, component):
            continue
        if _component_excluded(component, evidence) and _context_overlaps(claim, evidence, {component}):
            findings.append(
                "Component exclusion conflict: evidence excludes the component credited by the claim."
            )
    return tuple(dict.fromkeys(findings))


def _evidence_is_limited_beyond_claim(claim: str, evidence: str) -> bool:
    return (
        _has_new_limiter(CONDITION_LIMIT_RE, claim, evidence)
        or _has_new_limiter(SUBGROUP_LIMIT_RE, claim, evidence)
        or _has_new_limiter(SUBSET_LIMIT_RE, claim, evidence)
        or _has_new_limiter(CASE_STUDY_RE, claim, evidence)
        or (SIMULATION_RE.search(evidence) and not SIMULATION_RE.search(claim))
        or (IN_VITRO_RE.search(evidence) and not IN_VITRO_RE.search(claim))
    )


def _setting_mismatch(claim: str, evidence: str) -> bool:
    if HUMAN_RE.search(claim) and (ANIMAL_RE.search(evidence) or IN_VITRO_RE.search(evidence)):
        return True
    if re.search(r"\badults?\b", claim, re.IGNORECASE) and CHILD_RE.search(evidence):
        return True
    if HARDWARE_RE.search(claim) and SIMULATION_RE.search(evidence):
        return True
    if SIMULATION_RE.search(evidence) and HARDWARE_RE.search(evidence) and not HARDWARE_RE.search(claim):
        return True
    return False


def _has_new_limiter(pattern: re.Pattern[str], claim: str, evidence: str) -> bool:
    return bool(pattern.search(evidence) and not pattern.search(claim))


def _claimed_result_components(claim: str) -> tuple[str, ...]:
    return tuple({match.group("component").lower() for match in COMPONENT_RESULT_RE.finditer(claim)})


def _claim_excludes_component(text: str, component: str) -> bool:
    return _component_excluded(component, text)


def _component_excluded(component: str, text: str) -> bool:
    pattern = re.compile(EXCLUSION_TEMPLATE.format(component=re.escape(component)), re.IGNORECASE)
    return bool(pattern.search(text))


def _context_overlaps(claim: str, evidence: str, excluded_tokens: set[str] | None = None) -> bool:
    claim_tokens = _content_tokens(claim, excluded_tokens)
    evidence_tokens = _content_tokens(evidence, excluded_tokens)
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.67


def _content_tokens(text: str, excluded_tokens: set[str] | None = None) -> set[str]:
    tokens = set(tokenize(TRIGGER_RE.sub(" ", text)))
    if excluded_tokens:
        tokens -= excluded_tokens
    return tokens
