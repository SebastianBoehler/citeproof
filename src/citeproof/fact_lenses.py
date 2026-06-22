"""Deterministic checks for high-risk factual conflicts."""

from __future__ import annotations

import re

from citeproof.assertion_lens import inspect_assertion_status_tensions
from citeproof.attribute_lens import inspect_attribute_conflicts
from citeproof.clinical_lens import inspect_clinical_conflicts
from citeproof.comparison_lens import inspect_comparison_direction
from citeproof.context_lens import (
    inspect_component_exclusion_conflicts,
    inspect_context_tensions,
)
from citeproof.contrast_lens import inspect_contrast_exclusion_conflicts
from citeproof.measurement_lens import inspect_measurement_conflicts
from citeproof.models import FactInspection, Label
from citeproof.negation_lens import (
    inspect_negation_and_comparator_conflicts,
    inspect_negation_and_comparator_tensions,
)
from citeproof.outcome_lens import inspect_outcome_conflicts, inspect_outcome_tensions
from citeproof.protocol_lens import inspect_protocol_conflicts, inspect_protocol_tensions
from citeproof.qualitative_lens import (
    inspect_qualitative_conflicts,
    inspect_qualitative_tensions,
)
from citeproof.quantities import QuantityMention, numbers_to_units, quantity_mentions
from citeproof.role_lens import inspect_role_conflicts
from citeproof.statistical_lens import inspect_statistical_conflicts
from citeproof.strength_lens import inspect_strength_conflicts, inspect_strength_tensions
from citeproof.technical_property_lens import inspect_technical_property_conflicts
from citeproof.text import token_overlap_ratio
from citeproof.training_config_lens import inspect_training_config_conflicts

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
QUANTITY_LOWER_BOUND_RE = re.compile(
    r"\b(over|more\s+than|greater\s+than|at\s+least|no\s+less\s+than)\b",
    re.IGNORECASE,
)
QUANTITY_UPPER_BOUND_RE = re.compile(
    r"\b(up\s+to|at\s+most|no\s+more\s+than|under|less\s+than)\b",
    re.IGNORECASE,
)
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


def inspect_facts(claim: str, evidence: str) -> FactInspection:
    """Return deterministic conflicts or partial-support signals."""

    comparison_inspection = inspect_comparison_direction(
        claim, evidence, _material_anchors, _normalize_anchor
    )
    negation_findings = list(inspect_negation_and_comparator_conflicts(claim, evidence))
    if comparison_inspection.label == Label.PARTIALLY_SUPPORTED:
        negation_findings = [
            finding for finding in negation_findings if not finding.startswith("Direction conflict:")
        ]
    hard_findings = (
        _number_conflicts(claim, evidence)
        + _unit_conflicts(claim, evidence)
        + _year_conflicts(claim, evidence)
        + negation_findings
        + list(inspect_qualitative_conflicts(claim, evidence))
        + list(inspect_attribute_conflicts(claim, evidence))
        + list(inspect_technical_property_conflicts(claim, evidence))
        + list(inspect_statistical_conflicts(claim, evidence))
        + list(inspect_strength_conflicts(claim, evidence))
        + list(inspect_outcome_conflicts(claim, evidence))
        + list(inspect_protocol_conflicts(claim, evidence))
        + list(inspect_role_conflicts(claim, evidence))
        + list(inspect_component_exclusion_conflicts(claim, evidence))
        + list(inspect_contrast_exclusion_conflicts(claim, evidence))
        + list(inspect_clinical_conflicts(claim, evidence))
        + list(inspect_measurement_conflicts(claim, evidence))
        + list(inspect_training_config_conflicts(claim, evidence))
    )
    hard_findings += (
        list(comparison_inspection.findings)
        if comparison_inspection.label == Label.CONTRADICTED
        else []
    )
    if hard_findings:
        return FactInspection(Label.CONTRADICTED, tuple(hard_findings))
    tension_findings = (
        inspect_negation_and_comparator_tensions(claim, evidence)
        + inspect_qualitative_tensions(claim, evidence)
        + inspect_strength_tensions(claim, evidence)
        + inspect_assertion_status_tensions(claim, evidence)
        + inspect_outcome_tensions(claim, evidence)
        + inspect_protocol_tensions(claim, evidence)
        + inspect_context_tensions(claim, evidence)
    )
    if tension_findings:
        return FactInspection(Label.PARTIALLY_SUPPORTED, tension_findings)
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
    claim_mentions = _quantity_mentions_by_unit(claim)
    evidence_mentions = _quantity_mentions_by_unit(evidence)
    findings: list[str] = []
    for unit, claim_items in claim_mentions.items():
        evidence_items = evidence_mentions.get(unit, ())
        if not evidence_items:
            continue
        claim_numbers = {item.number for item in claim_items}
        evidence_numbers = {item.number for item in evidence_items}
        if claim_numbers != evidence_numbers:
            if compatible_bounded_quantity(claim_items, evidence_items, claim, evidence):
                continue
            claim_text = ", ".join(item.text for item in claim_items)
            evidence_text = ", ".join(item.text for item in evidence_items)
            findings.append(f"Numeric conflict for {unit}: claim {claim_text} vs evidence {evidence_text}")
    return findings


def _unit_conflicts(claim: str, evidence: str) -> list[str]:
    claim_numbers = numbers_to_units(claim)
    evidence_numbers = numbers_to_units(evidence)
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


def _quantity_mentions_by_unit(text: str) -> dict[str, tuple[QuantityMention, ...]]:
    mentions: dict[str, list[QuantityMention]] = {}
    for mention in quantity_mentions(text):
        mentions.setdefault(mention.unit, []).append(mention)
    return {unit: tuple(items) for unit, items in mentions.items()}


def compatible_bounded_quantity(
    claim_items: tuple[QuantityMention, ...],
    evidence_items: tuple[QuantityMention, ...],
    claim: str,
    evidence: str,
) -> bool:
    if len(claim_items) != 1 or len(evidence_items) != 1:
        return False
    claim_bound = _quantity_bound(claim, claim_items[0])
    evidence_bound = _quantity_bound(evidence, evidence_items[0])
    if evidence_bound != "exact":
        return False
    if claim_bound == "lower":
        return evidence_items[0].number >= claim_items[0].number
    if claim_bound == "upper":
        return evidence_items[0].number <= claim_items[0].number
    return False


def _quantity_bound(text: str, mention: QuantityMention) -> str:
    start = text.find(mention.text)
    prefix = text[max(0, start - 32) : start] if start >= 0 else ""
    if QUANTITY_LOWER_BOUND_RE.search(prefix):
        return "lower"
    if QUANTITY_UPPER_BOUND_RE.search(prefix):
        return "upper"
    return "exact"
