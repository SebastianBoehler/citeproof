"""Whole-paper verification combining bibliography and source evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from citeproof.bibliography import parse_bibtex, verify_bibliography
from citeproof.models import Source
from citeproof.parser import parse_claims
from citeproof.sources import align_sources_to_bibtex, build_chunks, load_sources
from citeproof.verifier import verify_claim


@dataclass(frozen=True)
class PaperVerificationReport:
    """Combined bibliography and claim-support report."""

    bibliography: dict
    claim_results: list[dict]
    mapped_source_count: int
    loaded_source_count: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def verify_paper(
    tex_path: str | Path,
    bib_path: str | Path,
    source_dir: str | Path,
) -> PaperVerificationReport:
    """Verify a LaTeX draft against BibTeX metadata and local source files."""

    bibliography = verify_bibliography(tex_path, bib_path)
    trusted_sources, loaded_count, mapped_count = load_bib_aligned_sources(bib_path, source_dir)
    chunks = build_chunks(trusted_sources)
    claims = parse_claims(Path(tex_path).read_text(encoding="utf-8"))
    results = [verify_claim(claim, chunks) for claim in claims]
    return PaperVerificationReport(
        bibliography=bibliography.to_dict(),
        claim_results=[result.to_dict() for result in results],
        mapped_source_count=mapped_count,
        loaded_source_count=loaded_count,
    )


def load_bib_aligned_sources(
    bib_path: str | Path,
    source_dir: str | Path,
) -> tuple[list[Source], int, int]:
    """Load sources and keep only files that map to BibTeX keys."""

    entries = parse_bibtex(Path(bib_path).read_text(encoding="utf-8"))
    title_by_key = {
        key: entry.fields["title"]
        for key, entry in entries.items()
        if entry.fields.get("title")
    }
    sources = load_sources(source_dir)
    aligned_sources = align_sources_to_bibtex(sources, title_by_key)
    trusted_sources = [source for source in aligned_sources if source.citation_key in title_by_key]
    mapped_keys = {source.citation_key for source in trusted_sources}
    return trusted_sources, len(sources), len(mapped_keys)


def render_paper_report(report: PaperVerificationReport) -> str:
    """Render a compact Markdown paper verification report."""

    bibliography = report.bibliography
    lines = [
        "# CiteProof Paper Report",
        "",
        "## Source Mapping",
        "",
        f"- Loaded source files: {report.loaded_source_count}",
        f"- Sources mapped to BibTeX keys: {report.mapped_source_count}",
        "",
        "## Bibliography",
        "",
        f"- Errors: {bibliography['error_count']}",
        f"- Warnings: {bibliography['warning_count']}",
        f"- Missing BibTeX entries: {len(bibliography['missing_bib_entries'])}",
        f"- Unused BibTeX entries: {len(bibliography['unused_bib_entries'])}",
        "",
        "## Claim Labels",
        "",
    ]
    counts: dict[str, int] = {}
    for result in report.claim_results:
        counts[result["label"]] = counts.get(result["label"], 0) + 1
    lines.extend(f"- {label}: {count}" for label, count in sorted(counts.items()))
    lines.extend(["", "## Claim Details", ""])
    for index, result in enumerate(report.claim_results, start=1):
        citations = ", ".join(result["citations"]) if result["citations"] else "none"
        lines.extend(
            [
                f"### {index}. {result['label']}",
                "",
                f"**Claim:** {result['claim']}",
                "",
                f"**Citations:** {citations}",
                "",
                f"**Confidence:** {result['confidence']:.3f}",
                "",
                f"**Reason:** {result['reason']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
