"""Training and decoding configuration value conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from citeproof.text import tokenize


@dataclass(frozen=True)
class ConfigSlot:
    label: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class ConfigValue:
    slot: str
    value: Decimal
    text: str


NUMBER = r"\d+(?:\.\d+)?(?:e[-+]?\d+)?"
SLOTS = (
    ConfigSlot("learning rate", (r"learning\s+rate", r"\blr\b")),
    ConfigSlot("batch size", (r"batch\s+size",)),
    ConfigSlot("epoch count", (r"epochs?",)),
    ConfigSlot("dropout", (r"dropout(?:\s+rate)?",)),
    ConfigSlot("temperature", (r"temperature",)),
    ConfigSlot("top-p", (r"top[-\s]?p",)),
    ConfigSlot("weight decay", (r"weight\s+decay",)),
    ConfigSlot("beam size", (r"beam\s+size",)),
)
SLOT_WORDS_RE = re.compile(
    r"\b("
    r"batch|beam|decay|decoder|dropout|epoch|epochs|learning|lr|rate|temperature|"
    r"top|p|trained|training|used|uses|weight"
    r")\b",
    re.IGNORECASE,
)


def inspect_training_config_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return hard conflicts for controlled training/configuration numeric slots."""

    findings: list[str] = []
    if not _context_overlaps(claim, evidence):
        return ()
    claim_values = _config_values(claim)
    evidence_values = _config_values(evidence)
    for claim_value in claim_values:
        for evidence_value in evidence_values:
            if claim_value.slot == evidence_value.slot and claim_value.value != evidence_value.value:
                findings.append(
                    "Training configuration value conflict: claim says "
                    f"{claim_value.text} while evidence says {evidence_value.text}."
                )
    return tuple(dict.fromkeys(findings))


def _config_values(text: str) -> tuple[ConfigValue, ...]:
    values: list[ConfigValue] = []
    for slot in SLOTS:
        for pattern in slot.patterns:
            values.extend(_forward_values(slot.label, pattern, text))
            values.extend(_backward_values(slot.label, pattern, text))
    return tuple(dict.fromkeys(values))


def _forward_values(slot: str, pattern: str, text: str) -> list[ConfigValue]:
    values: list[ConfigValue] = []
    regex = re.compile(
        rf"\b(?P<slot>{pattern})\b"
        rf"\s*(?:(?:=|:)\s*|(?:of|was|is|to|at|with|used)\s+)?"
        rf"(?P<value>{NUMBER})\b",
        re.IGNORECASE,
    )
    for match in regex.finditer(text):
        values.append(ConfigValue(slot, Decimal(match.group("value")), match.group(0)))
    return values


def _backward_values(slot: str, pattern: str, text: str) -> list[ConfigValue]:
    values: list[ConfigValue] = []
    regex = re.compile(
        rf"\b(?P<value>{NUMBER})\s+(?P<slot>{pattern})\b",
        re.IGNORECASE,
    )
    for match in regex.finditer(text):
        values.append(ConfigValue(slot, Decimal(match.group("value")), match.group(0)))
    return values


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens and not evidence_tokens:
        return True
    if not claim_tokens or not evidence_tokens:
        return False
    return len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.67


def _context_tokens(text: str) -> set[str]:
    stripped = re.sub(NUMBER, " ", SLOT_WORDS_RE.sub(" ", text), flags=re.IGNORECASE)
    return set(tokenize(stripped))
