"""Text normalization helpers."""

from __future__ import annotations

import re

WORD_RE = re.compile(r"[a-z0-9]+")
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "with",
}


def tokenize(text: str) -> list[str]:
    """Return normalized content tokens."""

    return [token for token in WORD_RE.findall(text.lower()) if token not in STOPWORDS]


def split_sentences(text: str) -> list[str]:
    """Split text into rough sentences."""

    return [part.strip() for part in SENTENCE_BOUNDARY_RE.split(text) if part.strip()]


def chunk_text(text: str, max_chars: int = 700) -> list[str]:
    """Build compact chunks from paragraphs and sentences."""

    chunks: list[str] = []
    current = ""
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]

    for block in blocks:
        parts = split_sentences(block) if len(block) > max_chars else [block]
        for part in parts:
            if not current:
                current = part
                continue
            if len(current) + len(part) + 1 <= max_chars:
                current = f"{current} {part}"
            else:
                chunks.append(current)
                current = part

    if current:
        chunks.append(current)
    return chunks


def token_overlap_ratio(left: str, right: str) -> float:
    """Return the share of left tokens covered by right tokens."""

    left_tokens = set(tokenize(left))
    if not left_tokens:
        return 0.0
    right_tokens = set(tokenize(right))
    return len(left_tokens & right_tokens) / len(left_tokens)
