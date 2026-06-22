"""Local source loading and chunking."""

from __future__ import annotations

import json
from pathlib import Path

from citeproof.models import Source, SourceChunk
from citeproof.text import chunk_text

TEXT_SUFFIXES = {".txt", ".md"}


def load_sources(source_dir: str | Path) -> list[Source]:
    """Load text and JSONL sources from a directory."""

    root = Path(source_dir)
    if not root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {root}")

    sources: list[Source] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8").strip()
            if text:
                sources.append(
                    Source(
                        source_id=path.stem,
                        citation_key=path.stem,
                        title=path.stem,
                        text=text,
                        path=str(path),
                    )
                )
        elif path.suffix.lower() == ".jsonl":
            sources.extend(_load_jsonl_sources(path))

    if not sources:
        raise ValueError(f"No text or JSONL sources found in {root}")
    return sources


def build_chunks(sources: list[Source]) -> list[SourceChunk]:
    """Build searchable chunks from source documents."""

    chunks: list[SourceChunk] = []
    for source in sources:
        for index, chunk in enumerate(chunk_text(source.text)):
            chunks.append(
                SourceChunk(
                    source_id=source.source_id,
                    citation_key=source.citation_key,
                    title=source.title,
                    text=chunk,
                    chunk_id=f"{source.source_id}:{index}",
                )
            )
    return chunks


def _load_jsonl_sources(path: Path) -> list[Source]:
    sources: list[Source] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        text = str(data.get("text", "")).strip()
        if not text:
            raise ValueError(f"Missing text in {path}:{line_number}")
        source_id = str(data.get("source_id") or data.get("citation_key") or f"{path.stem}-{line_number}")
        citation_key = str(data.get("citation_key") or source_id)
        sources.append(
            Source(
                source_id=source_id,
                citation_key=citation_key,
                title=data.get("title"),
                text=text,
                path=str(path),
            )
        )
    return sources
