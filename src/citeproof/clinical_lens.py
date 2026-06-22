"""Clinical and effect-estimate slot conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from citeproof.text import tokenize


@dataclass(frozen=True)
class RatioValue:
    metric: str
    value: Decimal
    text: str


@dataclass(frozen=True)
class EndpointWindow:
    endpoint: str
    unit: str
    value: Decimal
    text: str


RATIO_METRIC = r"(?:hazard\s+ratio|odds\s+ratio|risk\s+ratio|relative\s+risk)"
RATIO_VALUE_RE = re.compile(
    rf"\b(?P<metric>{RATIO_METRIC})\b[^.;\n]{{0,40}}?"
    r"\b(?:was|is|=|of)?\s*(?P<value>\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
ADJUSTED_RE = re.compile(r"\badjusted\b", re.IGNORECASE)
UNADJUSTED_RE = re.compile(r"\bunadjusted\b|\bcrude\b", re.IGNORECASE)
POPULATION_GROUPS = (
    ("adult", (r"\badults?\b",)),
    ("child", (r"\bchildren\b", r"\bchild\b", r"\bpediatric\b", r"\bpaediatric\b")),
)
ENDPOINT_RE = re.compile(
    r"\b(?P<value>\d+(?:\.\d+)?)[-\s]+"
    r"(?P<unit>days?|weeks?|months?|years?)[-\s]+"
    r"(?P<endpoint>mortality|readmissions?|survival|response|remission)\b",
    re.IGNORECASE,
)
TRIAL_DESIGN_GROUPS = (
    ("randomized", (r"\brandomi[sz]ed\b", r"\brandomi[sz]ed\s+controlled\b")),
    ("controlled", (r"\bcontrolled\b", r"\bcontrol\s+arm\b")),
    ("single-arm", (r"\bsingle[- ]arm\b",)),
)
SLOT_TERMS_RE = re.compile(
    r"\b("
    r"adjusted|adults?|children|child|controlled|crude|days?|hazard|"
    r"mortality|odds|paediatric|patients?|pediatric|randomi[sz]ed|ratio|rats?|"
    r"readmissions?|relative|remission|response|risk|single|survival|unadjusted|"
    r"weeks?|months?|years?"
    r")\b",
    re.IGNORECASE,
)
MIN_CONTEXT_OVERLAP = 0.5


def inspect_clinical_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts for controlled clinical/effect slots."""

    findings: list[str] = []
    if not _context_overlaps(claim, evidence):
        return ()
    findings.extend(_ratio_value_conflicts(claim, evidence))
    findings.extend(_adjustment_conflicts(claim, evidence))
    findings.extend(_population_conflicts(claim, evidence))
    findings.extend(_endpoint_window_conflicts(claim, evidence))
    findings.extend(_trial_design_conflicts(claim, evidence))
    return tuple(dict.fromkeys(findings))


def _ratio_value_conflicts(claim: str, evidence: str) -> list[str]:
    findings: list[str] = []
    for claim_value in _ratio_values(claim):
        for evidence_value in _ratio_values(evidence):
            if claim_value.metric == evidence_value.metric and claim_value.value != evidence_value.value:
                findings.append(
                    "Exact effect value conflict: claim says "
                    f"{claim_value.text} while evidence says {evidence_value.text}."
                )
    return findings


def _adjustment_conflicts(claim: str, evidence: str) -> list[str]:
    claim_status = _adjustment_status(claim)
    evidence_status = _adjustment_status(evidence)
    if claim_status and evidence_status and claim_status != evidence_status:
        return [
            "Adjustment status conflict: claim and evidence use different adjusted/unadjusted estimates."
        ]
    return []


def _population_conflicts(claim: str, evidence: str) -> list[str]:
    claim_groups = _population_values(claim)
    evidence_groups = _population_values(evidence)
    if claim_groups and evidence_groups and not claim_groups & evidence_groups:
        return ["Population group conflict: claim and evidence describe different populations."]
    return []


def _endpoint_window_conflicts(claim: str, evidence: str) -> list[str]:
    findings: list[str] = []
    for claim_window in _endpoint_windows(claim):
        for evidence_window in _endpoint_windows(evidence):
            if (
                claim_window.endpoint == evidence_window.endpoint
                and claim_window.unit == evidence_window.unit
                and claim_window.value != evidence_window.value
            ):
                findings.append(
                    "Endpoint window conflict: claim says "
                    f"{claim_window.text} while evidence says {evidence_window.text}."
                )
    return findings


def _trial_design_conflicts(claim: str, evidence: str) -> list[str]:
    claim_values = _trial_design_values(claim)
    evidence_values = _trial_design_values(evidence)
    if claim_values and evidence_values and not claim_values & evidence_values:
        return ["Trial design conflict: claim and evidence describe different trial designs."]
    return []


def _ratio_values(text: str) -> tuple[RatioValue, ...]:
    return tuple(
        RatioValue(
            re.sub(r"\s+", " ", match.group("metric").casefold()),
            Decimal(match.group("value")),
            match.group(0).strip(),
        )
        for match in RATIO_VALUE_RE.finditer(text)
    )


def _adjustment_status(text: str) -> str | None:
    if UNADJUSTED_RE.search(text):
        return "unadjusted"
    if ADJUSTED_RE.search(text):
        return "adjusted"
    return None


def _population_values(text: str) -> set[str]:
    return {
        value
        for value, patterns in POPULATION_GROUPS
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    }


def _endpoint_windows(text: str) -> tuple[EndpointWindow, ...]:
    return tuple(
        EndpointWindow(
            match.group("endpoint").casefold().rstrip("s"),
            match.group("unit").casefold().rstrip("s"),
            Decimal(match.group("value")),
            match.group(0).strip(),
        )
        for match in ENDPOINT_RE.finditer(text)
    )


def _trial_design_values(text: str) -> set[str]:
    values = {
        value
        for value, patterns in TRIAL_DESIGN_GROUPS
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    }
    if "single-arm" in values:
        values -= {"controlled"}
    return values


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = set(tokenize(SLOT_TERMS_RE.sub(" ", claim)))
    evidence_tokens = set(tokenize(SLOT_TERMS_RE.sub(" ", evidence)))
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= (
        MIN_CONTEXT_OVERLAP
    )
