"""External bibliography metadata verification."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Protocol

from citeproof.bibliography import BibEntry
from citeproof.text import tokenize


@dataclass(frozen=True)
class MetadataRecord:
    """One external metadata hit."""

    provider: str
    title: str
    year: str | None = None
    authors: tuple[str, ...] = ()
    doi: str | None = None
    venue: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class MetadataCheck:
    """Verification result for one bibliography entry."""

    key: str
    status: str
    confidence: float
    reason: str
    provider: str | None = None
    matched_title: str | None = None
    matched_year: str | None = None
    matched_doi: str | None = None
    api_calls: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class MetadataProvider(Protocol):
    """External scholarly metadata provider."""

    name: str

    def search(self, entry: BibEntry) -> list[MetadataRecord]:
        """Return candidate records for a BibTeX entry."""


def build_providers(names: list[str] | None = None, timeout: float = 8.0) -> list[MetadataProvider]:
    """Build external metadata providers by short name."""

    from citeproof.metadata_providers import (
        ArxivProvider,
        CrossrefProvider,
        OpenAlexProvider,
        SemanticScholarProvider,
    )

    registry = {
        "crossref": CrossrefProvider,
        "openalex": OpenAlexProvider,
        "semanticscholar": SemanticScholarProvider,
        "s2": SemanticScholarProvider,
        "arxiv": ArxivProvider,
    }
    selected = names or ["crossref", "openalex", "semanticscholar", "arxiv"]
    providers: list[MetadataProvider] = []
    for name in selected:
        key = name.strip().lower()
        if key not in registry:
            raise ValueError(f"Unknown metadata provider: {name}")
        providers.append(registry[key](timeout=timeout))
    return providers


def verify_entry_metadata(
    entry: BibEntry,
    providers: list[MetadataProvider] | None = None,
) -> MetadataCheck:
    """Verify one BibTeX entry against external metadata providers."""

    if not entry.fields.get("title") and not entry.fields.get("doi"):
        return MetadataCheck(entry.key, "skipped", 0.0, "Entry has neither title nor DOI.")

    api_calls = 0
    errors: list[str] = []
    best: tuple[float, MetadataRecord, str] | None = None
    for provider in providers or build_providers():
        api_calls += 1
        try:
            records = provider.search(entry)
        except Exception as exc:  # pragma: no cover - provider/network dependent
            errors.append(f"{provider.name}: {exc}")
            continue
        for record in records:
            score, reason = score_metadata_match(entry, record)
            if best is None or score > best[0]:
                best = (score, record, reason)

    if best is None:
        reason = "No external metadata hit found."
        if errors:
            reason += f" Provider errors: {'; '.join(errors)}"
            return MetadataCheck(entry.key, "error", 0.0, reason, api_calls=api_calls)
        return MetadataCheck(entry.key, "not_found", 0.0, reason, api_calls=api_calls)

    score, record, reason = best
    status = "verified" if score >= 0.82 else "mismatch" if score >= 0.55 else "not_found"
    return MetadataCheck(
        key=entry.key,
        status=status,
        confidence=round(score, 3),
        reason=reason,
        provider=record.provider,
        matched_title=record.title,
        matched_year=record.year,
        matched_doi=record.doi,
        api_calls=api_calls,
    )


def verify_entries_metadata(
    entries: dict[str, BibEntry],
    providers: list[MetadataProvider] | None = None,
    limit: int | None = None,
) -> list[MetadataCheck]:
    """Verify a BibTeX entry map."""

    selected = list(entries.values())[:limit]
    active_providers = providers or build_providers()
    return [verify_entry_metadata(entry, active_providers) for entry in selected]


def score_metadata_match(entry: BibEntry, record: MetadataRecord) -> tuple[float, str]:
    """Score a candidate metadata hit against one BibTeX entry."""

    title_score = _title_similarity(entry.fields.get("title", ""), record.title)
    year_score = _year_score(entry.fields.get("year"), record.year)
    author_score = _author_score(entry.fields.get("author", ""), record.authors)
    doi_score = _doi_score(entry.fields.get("doi"), record.doi)
    score = (0.68 * title_score) + (0.12 * year_score) + (0.10 * author_score) + (
        0.10 * doi_score
    )
    if entry.fields.get("year") and record.year and year_score == 0.0:
        score = min(score, 0.81)
    if entry.fields.get("doi") and record.doi and doi_score == 0.0:
        score = min(score, 0.54)
    reason = (
        f"title={title_score:.2f}, year={year_score:.2f}, "
        f"authors={author_score:.2f}, doi={doi_score:.2f}"
    )
    return score, reason


def _title_similarity(left: str, right: str) -> float:
    left_norm = _normalize(left)
    right_norm = _normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    left_tokens = set(tokenize(left_norm))
    right_tokens = set(tokenize(right_norm))
    overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    return max(overlap, SequenceMatcher(None, left_norm, right_norm).ratio())


def _year_score(expected: str | None, actual: str | None) -> float:
    if not expected or not actual:
        return 0.5
    return 1.0 if expected == actual else 0.0


def _author_score(author_field: str, authors: tuple[str, ...]) -> float:
    expected = {_last_name(author) for author in re.split(r"\s+and\s+", author_field) if author}
    actual = {_last_name(author) for author in authors if author}
    expected.discard("")
    actual.discard("")
    if not expected or not actual:
        return 0.5
    return len(expected & actual) / len(expected)


def _doi_score(expected: str | None, actual: str | None) -> float:
    if not expected or not actual:
        return 0.5
    return 1.0 if _normalize_doi(expected) == _normalize_doi(actual) else 0.0


def _normalize(text: str) -> str:
    return " ".join(tokenize(text))


def _normalize_doi(doi: str) -> str:
    return doi.lower().replace("https://doi.org/", "").strip()


def _last_name(author: str) -> str:
    if "," in author:
        author = author.split(",", 1)[0]
    return re.sub(r"[^a-z]", "", author.lower().split()[-1]) if author.split() else ""
