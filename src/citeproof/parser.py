"""Draft claim parsing."""

from __future__ import annotations

import re

from citeproof.models import Claim
from citeproof.text import split_sentences

CITE_COMMAND_RE = re.compile(r"\\cite[a-zA-Z*]*\{([^}]+)\}")
BRACKET_CITE_RE = re.compile(r"\[([^\]]*@[\w:.-]+[^\]]*)\]")
AT_CITE_RE = re.compile(r"@([\w:.-]+)")


def parse_claims(text: str, require_citation: bool = True) -> list[Claim]:
    """Parse citation-bearing claims from a draft."""

    claims: list[Claim] = []
    for sentence in split_sentences(_strip_markdown_noise(text)):
        citation_keys = extract_citation_keys(sentence)
        if require_citation and not citation_keys:
            continue
        claim_text = clean_claim_text(sentence)
        if claim_text:
            claims.append(Claim(text=claim_text, citation_keys=tuple(citation_keys)))
    return claims


def extract_citation_keys(text: str) -> list[str]:
    """Extract LaTeX and Pandoc-style citation keys."""

    keys: list[str] = []
    for match in CITE_COMMAND_RE.finditer(text):
        keys.extend(_split_latex_keys(match.group(1)))
    for match in BRACKET_CITE_RE.finditer(text):
        keys.extend(AT_CITE_RE.findall(match.group(1)))
    return list(dict.fromkeys(key.strip() for key in keys if key.strip()))


def clean_claim_text(text: str) -> str:
    """Remove citation syntax while preserving claim text."""

    cleaned = CITE_COMMAND_RE.sub("", text)
    cleaned = BRACKET_CITE_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([.!?,;:])", r"\1", cleaned)
    return cleaned


def _split_latex_keys(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",")]


def _strip_markdown_noise(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)
