"""BibTeX and LaTeX citation verification."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from citeproof.parser import extract_citation_keys

ENTRY_START_RE = re.compile(r"@(?P<type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s]+)\s*,", re.MULTILINE)
FIELD_RE = re.compile(r"(?P<name>[A-Za-z][\w-]*)\s*=")

REQUIRED_FIELDS = {
    "article": {"author", "title", "journal", "year"},
    "book": {"author", "title", "publisher", "year"},
    "incollection": {"author", "title", "booktitle", "publisher", "year"},
    "inproceedings": {"author", "title", "booktitle", "year"},
    "phdthesis": {"author", "title", "school", "year"},
    "techreport": {"author", "title", "institution", "year"},
    "misc": {"title", "year"},
}


@dataclass(frozen=True)
class BibEntry:
    """Parsed BibTeX entry."""

    key: str
    entry_type: str
    fields: dict[str, str]


@dataclass(frozen=True)
class BibliographyReport:
    """Bibliography verification output."""

    tex_path: str
    bib_path: str
    citation_count: int
    cited_key_count: int
    bib_entry_count: int
    missing_bib_entries: list[str]
    unused_bib_entries: list[str]
    incomplete_entries: dict[str, list[str]]

    @property
    def error_count(self) -> int:
        return len(self.missing_bib_entries) + len(self.incomplete_entries)

    @property
    def warning_count(self) -> int:
        return len(self.unused_bib_entries)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["error_count"] = self.error_count
        data["warning_count"] = self.warning_count
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def verify_bibliography(tex_path: str | Path, bib_path: str | Path) -> BibliographyReport:
    """Compare used LaTeX citation keys with BibTeX entries and required fields."""

    tex = Path(tex_path)
    bib = Path(bib_path)
    citation_keys = _extract_tex_citation_keys(tex.read_text(encoding="utf-8"))
    entries = parse_bibtex(bib.read_text(encoding="utf-8"))
    cited_unique = sorted(set(citation_keys))
    missing = [key for key in cited_unique if key not in entries]
    unused = sorted(key for key in entries if key not in set(cited_unique))
    incomplete = _find_incomplete_entries(entries)
    return BibliographyReport(
        tex_path=str(tex),
        bib_path=str(bib),
        citation_count=len(citation_keys),
        cited_key_count=len(cited_unique),
        bib_entry_count=len(entries),
        missing_bib_entries=missing,
        unused_bib_entries=unused,
        incomplete_entries=incomplete,
    )


def parse_bibtex(text: str) -> dict[str, BibEntry]:
    """Parse a practical subset of BibTeX without adding a runtime dependency."""

    entries: dict[str, BibEntry] = {}
    position = 0
    while match := ENTRY_START_RE.search(text, position):
        body_start = match.end()
        body_end = _find_entry_end(text, match.start())
        if body_end == -1:
            raise ValueError(f"Unclosed BibTeX entry: {match.group('key')}")
        body = text[body_start:body_end]
        key = match.group("key").strip()
        entries[key] = BibEntry(
            key=key,
            entry_type=match.group("type").lower(),
            fields=_parse_fields(body),
        )
        position = body_end + 1
    return entries


def render_bibliography_report(report: BibliographyReport) -> str:
    """Render a bibliography report as Markdown."""

    lines = [
        "# CiteProof Bibliography Report",
        "",
        f"- LaTeX file: `{report.tex_path}`",
        f"- BibTeX file: `{report.bib_path}`",
        f"- Citation occurrences: {report.citation_count}",
        f"- Unique cited keys: {report.cited_key_count}",
        f"- BibTeX entries: {report.bib_entry_count}",
        f"- Errors: {report.error_count}",
        f"- Warnings: {report.warning_count}",
        "",
    ]
    lines.extend(_section("Missing BibTeX Entries", report.missing_bib_entries))
    lines.extend(_section("Unused BibTeX Entries", report.unused_bib_entries))
    if report.incomplete_entries:
        lines.extend(["## Incomplete Entries", ""])
        for key, fields in sorted(report.incomplete_entries.items()):
            lines.append(f"- `{key}` missing: {', '.join(fields)}")
        lines.append("")
    else:
        lines.extend(["## Incomplete Entries", "", "None.", ""])
    return "\n".join(lines).rstrip() + "\n"


def _extract_tex_citation_keys(tex: str) -> list[str]:
    keys: list[str] = []
    for line in tex.splitlines():
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        keys.extend(extract_citation_keys(line))
    return keys


def _find_entry_end(text: str, start: int) -> int:
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    matches = list(FIELD_RE.finditer(body))
    for index, match in enumerate(matches):
        value_start = match.end()
        value_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        raw_value = body[value_start:value_end].rstrip(" \n\t,")
        fields[match.group("name").lower()] = _clean_value(raw_value)
    return fields


def _clean_value(raw_value: str) -> str:
    value = raw_value.strip()
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1]
    elif value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return re.sub(r"\s+", " ", value).strip()


def _find_incomplete_entries(entries: dict[str, BibEntry]) -> dict[str, list[str]]:
    incomplete: dict[str, list[str]] = {}
    for key, entry in entries.items():
        required = REQUIRED_FIELDS.get(entry.entry_type, {"title", "year"})
        missing = sorted(field for field in required if not entry.fields.get(field))
        if missing:
            incomplete[key] = missing
    return incomplete


def _section(title: str, values: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    if values:
        lines.extend(f"- `{value}`" for value in values)
    else:
        lines.append("None.")
    lines.append("")
    return lines
