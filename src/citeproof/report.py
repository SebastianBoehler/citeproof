"""Evidence ledger reporting."""

from __future__ import annotations

import json
from pathlib import Path

from citeproof.dashboard import results_to_html
from citeproof.models import VerificationResult


def results_to_json(results: list[VerificationResult]) -> str:
    """Serialize results as stable JSON."""

    return json.dumps([result.to_dict() for result in results], indent=2, sort_keys=True)


def results_to_markdown(results: list[VerificationResult]) -> str:
    """Render results as a compact Markdown report."""

    lines = ["# CiteProof Report", ""]
    for index, result in enumerate(results, start=1):
        lines.extend(
            [
                f"## {index}. {result.label.value}",
                "",
                f"**Claim:** {result.claim}",
                "",
                f"**Confidence:** {result.confidence:.3f}",
                "",
                f"**Citations:** {', '.join(result.citations) if result.citations else 'none'}",
                "",
                f"**Reason:** {result.reason}",
                "",
                f"**Failure mode:** {result.failure_mode.value if result.failure_mode else 'none'}",
                "",
            ]
        )
        for evidence_index, evidence in enumerate(result.evidence, start=1):
            lines.extend(
                [
                    f"**Evidence {evidence_index}:** `{evidence.source_id}` score={evidence.score:.4f}",
                    "",
                    f"> {evidence.text}",
                    "",
                ]
            )
        if result.trace:
            lines.extend(["**Atoms:**", ""])
            for atom in result.trace.atom_verifications:
                mode = atom.failure_mode.value if atom.failure_mode else "none"
                lines.append(f"- `{atom.label.value}` {atom.text} (failure={mode})")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(
    results: list[VerificationResult],
    json_output: str | Path | None,
    markdown_output: str | Path | None,
    html_output: str | Path | None = None,
    source_text: str | None = None,
) -> None:
    """Write requested report files."""

    if json_output:
        path = Path(json_output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(results_to_json(results), encoding="utf-8")
    if markdown_output:
        path = Path(markdown_output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(results_to_markdown(results), encoding="utf-8")
    if html_output:
        path = Path(html_output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(results_to_html(results, source_text=source_text), encoding="utf-8")
