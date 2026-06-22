"""Deterministic checks for high-risk factual conflicts."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.models import FactInspection, Label

NUMBER_UNIT_RE = re.compile(
    r"(?P<number>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(?P<unit>%|percent|examples?|samples?|gpus?|turns?|conversations?|dialogues?|domains?|languages?)",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
HEDGE_RE = re.compile(r"\b(may|might|could|inconclusive|suggests|preliminary)\b", re.IGNORECASE)
UNIVERSAL_RE = re.compile(r"\b(all|always|every|universally)\b", re.IGNORECASE)
NARROW_RE = re.compile(r"\b(only|some|subset|two|few|limited)\b", re.IGNORECASE)


@dataclass(frozen=True)
class _NumberMention:
    number: str
    unit: str
    text: str


def inspect_facts(claim: str, evidence: str) -> FactInspection:
    """Return deterministic conflicts or partial-support signals."""

    findings = _number_conflicts(claim, evidence) + _year_conflicts(claim, evidence)
    if findings:
        return FactInspection(Label.CONTRADICTED, tuple(findings))
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


def _year_conflicts(claim: str, evidence: str) -> list[str]:
    claim_years = set(YEAR_RE.findall(claim))
    evidence_years = set(YEAR_RE.findall(evidence))
    if claim_years and evidence_years and claim_years != evidence_years:
        return [f"Year conflict: claim {sorted(claim_years)} vs evidence {sorted(evidence_years)}"]
    return []


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
