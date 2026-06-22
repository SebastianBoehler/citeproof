"""Render draft text into citation-annotated audit HTML."""

from __future__ import annotations

import re
from html import escape
from typing import Any

from citeproof.parser import CITE_COMMAND_RE, clean_claim_text, extract_citation_keys, parse_claims
from citeproof.text import split_sentences

SECTION_RE = re.compile(r"\\(?P<level>section|subsection|subsubsection)\*?\{(?P<title>[^{}]+)\}")
DROP_ENVIRONMENTS = ("abstract", "equation", "figure", "figure*", "table", "table*", "tabular")
TEXT_COMMAND_RE = re.compile(r"\\(?P<command>emph|textbf|textit|texttt)\{(?P<value>[^{}]*)\}")


def render_audit_document(
    source_text: str | None,
    claim_results: list[dict[str, Any]],
) -> str:
    """Render source text with inline citation annotations."""

    if not source_text:
        return _fallback_claim_blocks(claim_results)
    claims = parse_claims(source_text)
    blocks = _source_blocks(source_text)
    html_blocks: list[str] = []
    for kind, text in blocks:
        if kind == "heading":
            html_blocks.append(f'<h2 class="doc-heading">{escape(text)}</h2>')
            continue
        claim_indices = _claim_indices_for_block(text, claims, claim_results)
        if claim_indices:
            html_blocks.append(_annotated_paragraph(text, claim_indices, claim_results))
        else:
            rendered = _render_inline(text, {}, claim_results)
            if rendered.strip():
                html_blocks.append(f'<p class="doc-paragraph">{rendered}</p>')
    return "\n".join(html_blocks) or _fallback_claim_blocks(claim_results)


def _fallback_claim_blocks(claim_results: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, result in enumerate(claim_results):
        badges = _claim_badges([index], claim_results)
        blocks.append(
            '<p class="doc-paragraph annotated '
            f'status-{_label_class(result)}" data-claim="{index}">'
            f'{escape(result["claim"])} {badges}</p>'
        )
    return "\n".join(blocks)


def _source_blocks(source_text: str) -> list[tuple[str, str]]:
    text = _strip_comments(source_text)
    text = _strip_latex_boilerplate(text)
    for environment in DROP_ENVIRONMENTS:
        text = re.sub(
            rf"\\begin\{{{re.escape(environment)}\}}.*?\\end\{{{re.escape(environment)}\}}",
            " ",
            text,
            flags=re.DOTALL,
        )
    blocks: list[tuple[str, str]] = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        position = 0
        for match in SECTION_RE.finditer(paragraph):
            prefix = paragraph[position : match.start()].strip()
            if prefix:
                blocks.append(("paragraph", prefix))
            blocks.append(("heading", _strip_inline_commands(match.group("title"))))
            position = match.end()
        suffix = paragraph[position:].strip()
        if suffix:
            blocks.append(("paragraph", suffix))
    return blocks


def _claim_indices_for_block(
    block: str,
    claims: list[Any],
    claim_results: list[dict[str, Any]],
) -> list[int]:
    block_keys = set(extract_citation_keys(block))
    if not block_keys:
        return []
    normalized_block = _normalize_text(clean_claim_text(block))
    indices: list[int] = []
    for index, claim in enumerate(claims[: len(claim_results)]):
        result_keys = set(claim_results[index].get("citations", ()))
        if not (set(claim.citation_keys) & block_keys or result_keys & block_keys):
            continue
        normalized_claim = _normalize_text(claim.text)
        if normalized_claim and normalized_claim in normalized_block:
            indices.append(index)
    if indices:
        return indices
    for index, result in enumerate(claim_results):
        if set(result.get("citations", ())) & block_keys:
            indices.append(index)
    return indices


def _annotated_paragraph(
    text: str,
    claim_indices: list[int],
    claim_results: list[dict[str, Any]],
) -> str:
    if len(claim_indices) > 1:
        return _multi_claim_paragraph(text, claim_indices, claim_results)
    citation_map = _citation_index_map(claim_indices, claim_results)
    rendered = _render_inline(text, citation_map, claim_results)
    badges = _claim_badges(claim_indices, claim_results)
    return f'<p class="doc-paragraph">{rendered} {badges}</p>'


def _multi_claim_paragraph(
    text: str,
    claim_indices: list[int],
    claim_results: list[dict[str, Any]],
) -> str:
    parts = []
    for sentence in split_sentences(text):
        indices = _result_indices_for_fragment(sentence, claim_indices, claim_results)
        if not indices:
            parts.append(_render_inline(sentence, {}, claim_results))
            continue
        citation_map = _citation_index_map(indices, claim_results)
        rendered = _render_inline(sentence, citation_map, claim_results)
        badges = _claim_badges(indices, claim_results)
        parts.append(f"{rendered} {badges}")
    return f'<p class="doc-paragraph">{" ".join(part for part in parts if part.strip())}</p>'


def _result_indices_for_fragment(
    text: str,
    candidate_indices: list[int],
    claim_results: list[dict[str, Any]],
) -> list[int]:
    fragment_keys = set(extract_citation_keys(text))
    if not fragment_keys:
        return []
    normalized_fragment = _normalize_text(clean_claim_text(text))
    key_matches: list[int] = []
    exact_matches: list[int] = []
    for index in candidate_indices:
        result = claim_results[index]
        if not (set(result.get("citations", ())) & fragment_keys):
            continue
        key_matches.append(index)
        normalized_claim = _normalize_text(str(result.get("claim", "")))
        if normalized_claim and normalized_claim in normalized_fragment:
            exact_matches.append(index)
    return exact_matches or key_matches


def _citation_index_map(
    claim_indices: list[int],
    claim_results: list[dict[str, Any]],
) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index in claim_indices:
        for key in claim_results[index].get("citations", ()):
            mapping.setdefault(key, index)
    return mapping


def _render_inline(
    text: str,
    citation_map: dict[str, int],
    claim_results: list[dict[str, Any]],
) -> str:
    placeholders: dict[str, str] = {}

    def replace_citation(match: re.Match[str]) -> str:
        parts = []
        for key in [part.strip() for part in match.group(1).split(",") if part.strip()]:
            index = citation_map.get(key, _first_result_for_key(key, claim_results))
            token = f"@@CITE{len(placeholders)}@@"
            parts.append(token)
            placeholders[token] = (
                f'<button class="cite inline-cite" data-index="{index}" '
                f'title="Inspect citation {escape(key)}">{escape(key)}</button>'
            )
        return " ".join(parts)

    rendered = CITE_COMMAND_RE.sub(replace_citation, text)
    rendered = _strip_inline_commands(rendered)
    rendered = escape(rendered)
    for token, html in placeholders.items():
        rendered = rendered.replace(token, html)
    return rendered


def _first_result_for_key(key: str, claim_results: list[dict[str, Any]]) -> int:
    for index, result in enumerate(claim_results):
        if key in result.get("citations", ()):
            return index
    return 0


def _claim_badges(indices: list[int], claim_results: list[dict[str, Any]]) -> str:
    badges = []
    for index in indices:
        result = claim_results[index]
        label = escape(str(result.get("label", "unknown")))
        badges.append(
            f'<button class="badge mini-badge {_label_class(result)}" data-index="{index}">'
            f"{label}</button>"
        )
    return '<span class="annotation-badges">' + "".join(badges) + "</span>"


def _label_class(result: dict[str, Any]) -> str:
    label = result.get("label", "uncertain")
    if label in {"supported", "partially_supported", "contradicted", "unsupported", "uncertain"}:
        return str(label)
    return "uncertain"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        kept = []
        escaped = False
        for char in line:
            if char == "%" and not escaped:
                break
            kept.append(char)
            escaped = char == "\\" and not escaped
        lines.append("".join(kept))
    return "\n".join(lines)


def _strip_latex_boilerplate(text: str) -> str:
    text = re.sub(r"\\documentclass(?:\[[^\]]*\])?\{[^}]+\}", " ", text)
    text = re.sub(r"\\usepackage(?:\[[^\]]*\])?\{[^}]+\}", " ", text)
    text = re.sub(r"\\(?:begin|end)\{document\}", " ", text)
    text = re.sub(r"\\(?:title|author|date|label|bibliography|bibliographystyle)\{[^}]*\}", " ", text)
    text = re.sub(r"\\maketitle\b", " ", text)
    return text


def _strip_inline_commands(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = TEXT_COMMAND_RE.sub(r"\g<value>", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
