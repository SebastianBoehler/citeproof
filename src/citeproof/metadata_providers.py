"""External metadata provider adapters."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from citeproof.bibliography import BibEntry
from citeproof.metadata import MetadataRecord


class CrossrefProvider:
    name = "crossref"

    def __init__(self, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def search(self, entry: BibEntry) -> list[MetadataRecord]:
        doi = entry.fields.get("doi")
        if doi:
            url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
            return [_crossref_record(_get_json(url, self.timeout)["message"])]
        query = urllib.parse.urlencode({"query.title": entry.fields.get("title", ""), "rows": 3})
        data = _get_json(f"https://api.crossref.org/works?{query}", self.timeout)
        return [_crossref_record(item) for item in data.get("message", {}).get("items", [])]


class OpenAlexProvider:
    name = "openalex"

    def __init__(self, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def search(self, entry: BibEntry) -> list[MetadataRecord]:
        query = urllib.parse.urlencode({"search": entry.fields.get("title", ""), "per-page": 3})
        data = _get_json(f"https://api.openalex.org/works?{query}", self.timeout)
        return [_openalex_record(item) for item in data.get("results", [])]


class SemanticScholarProvider:
    name = "semanticscholar"

    def __init__(self, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def search(self, entry: BibEntry) -> list[MetadataRecord]:
        fields = "title,year,authors,venue,externalIds,url"
        query = urllib.parse.urlencode({"query": entry.fields.get("title", ""), "fields": fields})
        url = f"https://api.semanticscholar.org/graph/v1/paper/search/match?{query}"
        data = _get_json(url, self.timeout)
        rows = data.get("data", [data]) if isinstance(data, dict) else []
        return [_semantic_scholar_record(item) for item in rows if item.get("title")]


class ArxivProvider:
    name = "arxiv"

    def __init__(self, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def search(self, entry: BibEntry) -> list[MetadataRecord]:
        title = entry.fields.get("title", "")
        query = urllib.parse.urlencode({"search_query": f'ti:"{title}"', "max_results": 3})
        xml = _get_text(f"https://export.arxiv.org/api/query?{query}", self.timeout)
        root = ET.fromstring(xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        return [_arxiv_record(item, ns) for item in root.findall("atom:entry", ns)]


def _crossref_record(item: dict) -> MetadataRecord:
    title = _first(item.get("title"))
    year = _date_year(item.get("published-print") or item.get("published-online") or item.get("issued"))
    authors = tuple(
        " ".join(part for part in [author.get("given"), author.get("family")] if part)
        for author in item.get("author", [])
    )
    return MetadataRecord(
        "crossref",
        title,
        year,
        authors,
        item.get("DOI"),
        _first(item.get("container-title")),
    )


def _openalex_record(item: dict) -> MetadataRecord:
    authors = tuple(
        author.get("author", {}).get("display_name", "") for author in item.get("authorships", [])
    )
    venue = (item.get("primary_location") or {}).get("source") or {}
    return MetadataRecord(
        "openalex",
        item.get("title", ""),
        str(item.get("publication_year") or "") or None,
        tuple(author for author in authors if author),
        item.get("doi"),
        venue.get("display_name"),
        item.get("id"),
    )


def _semantic_scholar_record(item: dict) -> MetadataRecord:
    external_ids = item.get("externalIds") or {}
    authors = tuple(author.get("name", "") for author in item.get("authors", []))
    return MetadataRecord(
        "semanticscholar",
        item.get("title", ""),
        str(item.get("year") or "") or None,
        tuple(author for author in authors if author),
        external_ids.get("DOI"),
        item.get("venue"),
        item.get("url"),
    )


def _arxiv_record(item: ET.Element, ns: dict[str, str]) -> MetadataRecord:
    title = item.findtext("atom:title", default="", namespaces=ns)
    published = item.findtext("atom:published", default="", namespaces=ns)
    authors = tuple(
        author.findtext("atom:name", default="", namespaces=ns)
        for author in item.findall("atom:author", ns)
    )
    return MetadataRecord(
        "arxiv",
        re.sub(r"\s+", " ", title).strip(),
        published[:4] or None,
        tuple(author for author in authors if author),
        None,
        "arXiv",
        item.findtext("atom:id", default=None, namespaces=ns),
    )


def _get_json(url: str, timeout: float) -> dict:
    return json.loads(_get_text(url, timeout))


def _get_text(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "citeproof/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _first(values: object) -> str:
    return values[0] if isinstance(values, list) and values else ""


def _date_year(date_parts: object) -> str | None:
    if not isinstance(date_parts, dict):
        return None
    parts = date_parts.get("date-parts") or []
    return str(parts[0][0]) if parts and parts[0] else None
