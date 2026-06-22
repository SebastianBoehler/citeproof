"""Deterministic quantity parsing for local citation checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class QuantityMention:
    number: Decimal
    unit: str
    text: str


_DIGIT_NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"
_ONES = {
    "one": Decimal("1"),
    "two": Decimal("2"),
    "three": Decimal("3"),
    "four": Decimal("4"),
    "five": Decimal("5"),
    "six": Decimal("6"),
    "seven": Decimal("7"),
    "eight": Decimal("8"),
    "nine": Decimal("9"),
    "ten": Decimal("10"),
}
_TENS = {
    "twenty": Decimal("20"),
    "thirty": Decimal("30"),
    "forty": Decimal("40"),
    "fifty": Decimal("50"),
}
_WORD_NUMBER = (
    r"(?:twenty|thirty|forty|fifty)(?:\s+(?:one|two|three|four|five|six|seven|eight|nine))?"
    r"|one|two|three|four|five|six|seven|eight|nine|ten"
)
_UNIT = (
    r"%|percent|examples?|samples?|gpus?|turns?|conversations?|dialogues?|domains?|languages?"
)
_SCALE = {"thousand": Decimal("1000"), "million": Decimal("1000000")}
_COMPACT_SCALE = {
    "k": Decimal("1000"),
    "m": Decimal("1000000"),
}
_BRIDGE_STOPWORDS = {
    "and",
    "as",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "than",
    "to",
    "with",
    "without",
}

_QUANTITY_RE = re.compile(
    rf"(?<![A-Za-z0-9])"
    rf"(?P<value>"
    rf"(?P<scale_number>{_DIGIT_NUMBER})\s+(?P<scale>thousand|million)"
    rf"|(?P<compact_number>{_DIGIT_NUMBER})(?P<compact>[kKmM])"
    rf"|(?P<plain_number>{_DIGIT_NUMBER})"
    rf"|(?P<word_number>{_WORD_NUMBER})"
    rf")"
    rf"(?:\s*(?P<symbol_unit>%)|(?P<bridge>(?:\s+[A-Za-z][A-Za-z-]*){{0,3}}?)\s+"
    rf"(?P<word_unit>{_UNIT}))",
    re.IGNORECASE,
)


def quantity_mentions(text: str) -> tuple[QuantityMention, ...]:
    """Return normalized quantity mentions in source order."""

    candidates: list[tuple[int, int, QuantityMention]] = []
    for match in _QUANTITY_RE.finditer(text):
        bridge = match.group("bridge") or ""
        if not _bridge_is_valid(bridge):
            continue
        unit = _normalize_unit(match.group("symbol_unit") or match.group("word_unit"))
        number = _parse_number(match)
        candidates.append((match.start(), match.end(), QuantityMention(number, unit, match.group(0))))

    selected: list[tuple[int, int, QuantityMention]] = []
    for start, end, mention in sorted(candidates, key=lambda item: (item[0], item[0] - item[1])):
        if not any(start < selected_end and end > selected_start for selected_start, selected_end, _ in selected):
            selected.append((start, end, mention))
    return tuple(mention for _, _, mention in sorted(selected, key=lambda item: item[0]))


def quantity_units(text: str) -> dict[str, tuple[Decimal, ...]]:
    """Map normalized units to unique numbers in source order."""

    numbers_by_unit: dict[str, list[Decimal]] = {}
    seen_by_unit: dict[str, set[Decimal]] = {}
    for mention in quantity_mentions(text):
        seen = seen_by_unit.setdefault(mention.unit, set())
        if mention.number in seen:
            continue
        numbers_by_unit.setdefault(mention.unit, []).append(mention.number)
        seen.add(mention.number)
    return {unit: tuple(numbers) for unit, numbers in numbers_by_unit.items()}


def numbers_to_units(text: str) -> dict[Decimal, set[str]]:
    """Map normalized numbers to the units they modify."""

    units_by_number: dict[Decimal, set[str]] = {}
    for unit, numbers in quantity_units(text).items():
        for number in numbers:
            units_by_number.setdefault(number, set()).add(unit)
    return units_by_number


def _parse_number(match: re.Match[str]) -> Decimal:
    if match.group("scale_number"):
        return _decimal(match.group("scale_number")) * _SCALE[match.group("scale").casefold()]
    if match.group("compact_number"):
        return _decimal(match.group("compact_number")) * _COMPACT_SCALE[
            match.group("compact").casefold()
        ]
    if match.group("plain_number"):
        return _decimal(match.group("plain_number"))
    return _parse_word_number(match.group("word_number"))


def _decimal(number: str) -> Decimal:
    return Decimal(number.replace(",", ""))


def _parse_word_number(number: str) -> Decimal:
    words = number.casefold().split()
    if len(words) == 1:
        if words[0] in _ONES:
            return _ONES[words[0]]
        return _TENS[words[0]]
    return _TENS[words[0]] + _ONES[words[1]]


def _normalize_unit(unit: str) -> str:
    normalized = unit.casefold()
    if normalized in {"%", "percent"}:
        return "%"
    return normalized.rstrip("s")


def _bridge_is_valid(bridge: str) -> bool:
    words = [word.casefold() for word in re.findall(r"[A-Za-z]+", bridge)]
    return not any(word in _BRIDGE_STOPWORDS for word in words)
