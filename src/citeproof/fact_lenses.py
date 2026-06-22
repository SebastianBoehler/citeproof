"""Deterministic checks for high-risk factual conflicts."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.comparison_lens import inspect_comparison_direction
from citeproof.models import FactInspection, Label
from citeproof.text import token_overlap_ratio

NUMBER_UNIT_RE = re.compile(
    r"(?P<number>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(?P<unit>%|percent|examples?|samples?|gpus?|turns?|conversations?|dialogues?|domains?|languages?)",
    re.IGNORECASE,
)
MATERIAL_ANCHOR_RE = re.compile(
    r"\b(?:[A-Z]+[A-Za-z0-9.-]*\d+[A-Za-z0-9.-]*|[A-Z][A-Za-z]*[A-Z][A-Za-z0-9.]*|"
    r"[A-Z][a-z]+[A-Z][A-Za-z0-9.]*|[A-Z]{2,}[A-Za-z0-9.-]*)\b"
)
MATERIAL_ANCHOR_PHRASE_RE = re.compile(
    r"\b[A-Z][a-z]+\s+"
    r"(?:[Aa]dapter|[Aa]daptation|[Ff]ine-[Tt]uning|[Ll]earning|[Mm]ethod|[Mm]odel|"
    r"[Nn]etwork|[Rr]eplay|[Rr]etrieval|[Tt]raining|[Tt]uning)\b"
)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
HEDGE_RE = re.compile(r"\b(may|might|could|inconclusive|suggests|preliminary)\b", re.IGNORECASE)
UNIVERSAL_RE = re.compile(r"\b(all|always|every|universally)\b", re.IGNORECASE)
NARROW_RE = re.compile(r"\b(only|some|subset|two|few|limited)\b", re.IGNORECASE)
GENERIC_ANCHORS = {
    "Ablation",
    "Appendix",
    "Baseline",
    "Claim",
    "Dataset",
    "Evidence",
    "Experiment",
    "Figure",
    "Method",
    "Model",
    "Result",
    "Table",
    "Task",
    "The",
}
ENTITY_CONFLICT_MIN_OVERLAP = 0.45


@dataclass(frozen=True)
class _NumberMention:
    number: str
    unit: str
    text: str


def inspect_facts(claim: str, evidence: str) -> FactInspection:
    """Return deterministic conflicts or partial-support signals."""

    comparison_inspection = inspect_comparison_direction(
        claim, evidence, _material_anchors, _normalize_anchor
    )
    hard_findings = (
        _number_conflicts(claim, evidence)
        + _unit_conflicts(claim, evidence)
        + _year_conflicts(claim, evidence)
    )
    hard_findings += (
        list(comparison_inspection.findings)
        if comparison_inspection.label == Label.CONTRADICTED
        else []
    )
    if hard_findings:
        return FactInspection(Label.CONTRADICTED, tuple(hard_findings))
    if comparison_inspection.label == Label.PARTIALLY_SUPPORTED:
        return FactInspection(Label.PARTIALLY_SUPPORTED, comparison_inspection.findings)
    entity_findings = _entity_conflicts(claim, evidence)
    if entity_findings:
        return FactInspection(Label.CONTRADICTED, tuple(entity_findings))
    if HEDGE_RE.search(evidence) and not HEDGE_RE.search(claim):
        return FactInspection(Label.PARTIALLY_SUPPORTED, ("Evidence is hedged or inconclusive.",))
    if UNIVERSAL_RE.search(claim) and NARROW_RE.search(evidence):
        return FactInspection(Label.PARTIALLY_SUPPORTED, ("Evidence is narrower than the claim.",))
    return FactInspection(None, ())


def _number_conflicts(claim: str, evidence: str) -> list[str]:
    claim_mentions = _number_units(claim)
    evidence_mentions = _number_units(evidence)
    findings: list[str] = []
    for unit, claim_items in claim_mentions.items():
        evidence_items = evidence_mentions.get(unit, ())
        if not evidence_items:
            continue
        claim_numbers = {item.number for item in claim_items}
        evidence_numbers = {item.number for item in evidence_items}
        if claim_numbers != evidence_numbers:
            claim_text = ", ".join(item.text for item in claim_items)
            evidence_text = ", ".join(item.text for item in evidence_items)
            findings.append(f"Numeric conflict for {unit}: claim {claim_text} vs evidence {evidence_text}")
    return findings


def _unit_conflicts(claim: str, evidence: str) -> list[str]:
    claim_numbers = _numbers_to_units(claim)
    evidence_numbers = _numbers_to_units(evidence)
    findings: list[str] = []
    for number, claim_units in claim_numbers.items():
        evidence_units = evidence_numbers.get(number, set())
        if evidence_units and not claim_units & evidence_units:
            findings.append(
                f"Unit conflict for {number}: claim {sorted(claim_units)} vs evidence {sorted(evidence_units)}"
            )
    return findings


def _year_conflicts(claim: str, evidence: str) -> list[str]:
    claim_years = set(YEAR_RE.findall(claim))
    evidence_years = set(YEAR_RE.findall(evidence))
    if claim_years and evidence_years and claim_years != evidence_years:
        return [f"Year conflict: claim {sorted(claim_years)} vs evidence {sorted(evidence_years)}"]
    return []


def _entity_conflicts(claim: str, evidence: str) -> list[str]:
    if token_overlap_ratio(claim, evidence) < ENTITY_CONFLICT_MIN_OVERLAP:
        return []
    claim_anchors = _material_anchors(claim)
    evidence_anchors = _material_anchors(evidence)
    if not claim_anchors or not evidence_anchors:
        return []
    claim_keys = {_normalize_anchor(anchor) for anchor in claim_anchors}
    evidence_keys = {_normalize_anchor(anchor) for anchor in evidence_anchors}
    missing = tuple(anchor for anchor in claim_anchors if _normalize_anchor(anchor) not in evidence_keys)
    competing = tuple(anchor for anchor in evidence_anchors if _normalize_anchor(anchor) not in claim_keys)
    if not missing or not competing:
        return []
    return [
        "Entity conflict: evidence is missing claim anchor(s) "
        f"{', '.join(missing)} and contains competing anchor(s) {', '.join(competing)}"
    ]


def _material_anchors(text: str) -> tuple[str, ...]:
    anchors: list[str] = []
    seen: set[str] = set()
    candidates = [(match.start(), match.group(0)) for match in MATERIAL_ANCHOR_RE.finditer(text)]
    candidates += [
        (match.start(), match.group(0))
        for match in MATERIAL_ANCHOR_PHRASE_RE.finditer(text)
        if not _starts_inside_capitalized_phrase(text, match.start())
    ]
    for _, candidate in sorted(candidates):
        anchor = candidate.strip(".,;:()[]{}")
        key = _normalize_anchor(anchor)
        if _is_material_anchor(anchor) and key not in seen:
            anchors.append(anchor)
            seen.add(key)
    return tuple(anchors)


def _is_material_anchor(anchor: str) -> bool:
    if len(anchor) <= 1:
        return False
    if anchor in GENERIC_ANCHORS:
        return False
    if " " in anchor:
        return anchor.split()[0] not in GENERIC_ANCHORS
    if len(anchor) == 2 and anchor.isupper():
        return False
    return any(character.isupper() for character in anchor) and (
        any(character.islower() for character in anchor)
        or any(character.isdigit() for character in anchor)
        or anchor.isupper()
    )


def _normalize_anchor(anchor: str) -> str:
    return re.sub(r"\s+", " ", anchor.casefold())


def _starts_inside_capitalized_phrase(text: str, start: int) -> bool:
    prefix = text[:start].rstrip()
    previous = re.search(r"([A-Za-z]+)$", prefix)
    return bool(previous and previous.group(1)[0].isupper())


def _numbers_to_units(text: str) -> dict[str, set[str]]:
    numbers: dict[str, set[str]] = {}
    for unit, mentions in _number_units(text).items():
        for mention in mentions:
            numbers.setdefault(mention.number, set()).add(unit)
    return numbers


def _number_units(text: str) -> dict[str, tuple[_NumberMention, ...]]:
    mentions: dict[str, list[_NumberMention]] = {}
    for match in NUMBER_UNIT_RE.finditer(text):
        unit = _normalize_unit(match.group("unit"))
        mention = _NumberMention(_normalize_number(match.group("number")), unit, match.group(0))
        mentions.setdefault(unit, []).append(mention)
    return {unit: tuple(items) for unit, items in mentions.items()}


def _normalize_unit(unit: str) -> str:
    normalized = unit.lower()
    if normalized == "percent":
        return "%"
    return normalized.rstrip("s")


def _normalize_number(number: str) -> str:
    return number.replace(",", "")
