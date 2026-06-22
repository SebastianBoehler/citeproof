"""Controlled role and provenance binding checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class Binding:
    role: str
    value: str
    context: str


ROLE_RE = re.compile(
    r"\b(?:was|were|is|are|been|be)?\s*"
    r"(?P<role>trained|training|pretrained|fine[- ]tuned|evaluated|tested)\s+on\s+"
    r"(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
GENERATION_RE = re.compile(
    r"\b(?P<actor>[A-Z][A-Za-z0-9.-]*(?:\s+[A-Z][A-Za-z0-9.-]*)?|Human annotators?)\s+"
    r"(?P<role>generated|annotated)\s+(?P<object>[A-Za-z0-9][A-Za-z0-9 .-]{1,80})",
    re.IGNORECASE,
)
AUDIT_RE = re.compile(
    r"\b(?P<actor>[A-Z][A-Za-z0-9.-]*(?:\s+[A-Z][A-Za-z0-9.-]*)?)\s+"
    r"(?:was|were)?\s*(?:used\s+to\s+)?(?P<role>audit|audited|review|reviewed|evaluate|evaluated)\b",
    re.IGNORECASE,
)
FILTER_RE = re.compile(
    r"\bfilters?\s+(?P<object>toxic\s+prompts|prompts|outputs?)\s+"
    r"(?P<timing>before|after)\s+evaluation\b",
    re.IGNORECASE,
)
DATASET_LICENSE_RE = re.compile(
    r"\bdataset\s+(?:is\s+)?(?:released|available)\s+under\s+(?:a\s+|an\s+)?"
    r"(?P<license>permissive\s+mit|mit|non[- ]commercial)\s+license\b",
    re.IGNORECASE,
)
LABEL_SOURCE_RE = re.compile(
    r"\blearns?\s+from\s+(?P<source>gold\s+human\s+labels|pseudo[- ]labels?)\b",
    re.IGNORECASE,
)
RETRIEVAL_SOURCE_RE = re.compile(
    r"\b(?:retrieves?\s+passages\s+from|passages\s+retrieved\s+from)\s+"
    r"(?P<source>[A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*)?)\b",
    re.IGNORECASE,
)
STOP_RE = re.compile(
    r"\b(?:and|but|while|whereas|with|during|for|from|than|using)\b",
    re.IGNORECASE,
)


def inspect_role_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts for controlled role/provenance swaps."""

    findings: list[str] = []
    findings.extend(_training_evaluation_conflicts(claim, evidence))
    findings.extend(_generation_audit_conflicts(claim, evidence))
    findings.extend(_filter_stage_conflicts(claim, evidence))
    findings.extend(_license_conflicts(claim, evidence))
    findings.extend(_label_source_conflicts(claim, evidence))
    findings.extend(_retrieval_source_conflicts(claim, evidence))
    return tuple(dict.fromkeys(findings))


def _training_evaluation_conflicts(claim: str, evidence: str) -> list[str]:
    findings: list[str] = []
    for claim_binding in _role_bindings(claim):
        for evidence_binding in _role_bindings(evidence):
            if _role_family(claim_binding.role) == _role_family(evidence_binding.role):
                continue
            if _objects_overlap(claim_binding.value, evidence_binding.value):
                findings.append(
                    "Role conflict: claim assigns data to "
                    f"{claim_binding.role} while evidence assigns it to {evidence_binding.role}."
                )
    return findings


def _generation_audit_conflicts(claim: str, evidence: str) -> list[str]:
    findings: list[str] = []
    for claim_binding in _generation_bindings(claim):
        if not any(_same_value(claim_binding.context, item.context) for item in _generation_bindings(evidence)):
            continue
        audit_actors = {_normalize(match.group("actor")) for match in AUDIT_RE.finditer(evidence)}
        if _normalize(claim_binding.value) in audit_actors:
            findings.append(
                "Role conflict: claim says an actor generated the artifact while evidence "
                "assigns that actor an audit role."
            )
    return findings


def _filter_stage_conflicts(claim: str, evidence: str) -> list[str]:
    claim_filter = FILTER_RE.search(claim)
    evidence_filter = FILTER_RE.search(evidence)
    if not claim_filter or not evidence_filter:
        return []
    claim_object = _normalize(claim_filter.group("object"))
    evidence_object = _normalize(evidence_filter.group("object"))
    if (
        claim_object != evidence_object
        or claim_filter.group("timing").lower() != evidence_filter.group("timing").lower()
    ):
        return [
            "Role conflict: claim and evidence assign filtering to different "
            "objects or evaluation stages."
        ]
    return []


def _license_conflicts(claim: str, evidence: str) -> list[str]:
    claim_license = _dataset_license(claim)
    evidence_license = _dataset_license(evidence)
    if claim_license and evidence_license and claim_license != evidence_license:
        return ["Role conflict: claim and evidence assign different licenses to the dataset."]
    return []


def _label_source_conflicts(claim: str, evidence: str) -> list[str]:
    claim_source = _label_source(claim)
    evidence_source = _label_source(evidence)
    if claim_source and evidence_source and claim_source != evidence_source:
        return ["Role conflict: claim and evidence assign different learning label sources."]
    return []


def _retrieval_source_conflicts(claim: str, evidence: str) -> list[str]:
    claim_source = _retrieval_source(claim)
    evidence_source = _retrieval_source(evidence)
    if claim_source and evidence_source and claim_source != evidence_source:
        return ["Role conflict: claim and evidence assign different retrieval sources."]
    return []


def _role_bindings(text: str) -> tuple[Binding, ...]:
    bindings: list[Binding] = []
    for match in ROLE_RE.finditer(text):
        bindings.append(
            Binding(
                _normalize_role(match.group("role")),
                _clean_object(match.group("object")),
                "",
            )
        )
    return tuple(bindings)


def _generation_bindings(text: str) -> tuple[Binding, ...]:
    bindings: list[Binding] = []
    for match in GENERATION_RE.finditer(text):
        bindings.append(
            Binding(
                _normalize_role(match.group("role")),
                match.group("actor"),
                _clean_object(match.group("object")),
            )
        )
    return tuple(bindings)


def _normalize_role(role: str) -> str:
    normalized = role.lower().replace("-", " ")
    if normalized in {"training", "trained"}:
        return "trained"
    if normalized == "tested":
        return "evaluated"
    return normalized


def _role_family(role: str) -> str:
    if role in {"trained", "pretrained", "fine tuned"}:
        return "training"
    return "evaluation"


def _dataset_license(text: str) -> str | None:
    match = DATASET_LICENSE_RE.search(text)
    if not match:
        return None
    value = match.group("license").lower().replace("-", " ")
    return "mit" if "mit" in value else value


def _label_source(text: str) -> str | None:
    match = LABEL_SOURCE_RE.search(text)
    if not match:
        return None
    source = match.group("source").lower().replace("-", " ")
    return "pseudo labels" if source.startswith("pseudo") else source


def _retrieval_source(text: str) -> str | None:
    match = RETRIEVAL_SOURCE_RE.search(text)
    return _normalize(match.group("source")) if match else None


def _clean_object(text: str) -> str:
    clipped = STOP_RE.split(text, maxsplit=1)[0]
    return clipped.strip(" .,:;()[]{}")


def _objects_overlap(left: str, right: str) -> bool:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    return bool(left_tokens and right_tokens and left_tokens & right_tokens)


def _same_value(left: str, right: str) -> bool:
    return _objects_overlap(left, right)


def _normalize(text: str) -> str:
    return " ".join(tokenize(text))
