"""Draft claim parsing."""

from __future__ import annotations

import re

from citeproof.models import Claim
from citeproof.text import split_sentences

CITE_COMMAND_RE = re.compile(r"\\cite[a-zA-Z*]*\{([^}]+)\}")
BRACKET_CITE_RE = re.compile(r"\[([^\]]*@[\w:.-]+[^\]]*)\]")
AT_CITE_RE = re.compile(r"@([\w:.-]+)")
COMMA_CLAUSE_MARKER_RE = re.compile(r",\s+(?:while|whereas|but|and)\s+")
SEMICOLON_CLAUSE_BOUNDARY_RE = re.compile(r";\s+")
LATEX_ENVIRONMENTS_TO_DROP = (
    "comment",
    "equation",
    "figure",
    "figure*",
    "IEEEkeywords",
    "table",
    "table*",
    "tabular",
    "tikzpicture",
)


def parse_claims(text: str, require_citation: bool = True) -> list[Claim]:
    """Parse citation-bearing claims from a draft."""

    claims: list[Claim] = []
    for sentence in split_sentences(_prepare_draft_text(text)):
        for clause in split_citation_clauses(sentence):
            citation_keys = extract_citation_keys(clause)
            if require_citation and not citation_keys:
                continue
            claim_text = clean_claim_text(clause)
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
    cleaned = re.sub(r"[{}]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([.!?,;:])", r"\1", cleaned)
    return cleaned


def split_citation_clauses(sentence: str) -> list[str]:
    """Split one sentence into citation-local clauses when the boundary is explicit."""

    pieces = _split_explicit_citation_clauses(sentence)
    cited_pieces = [piece for piece in pieces if extract_citation_keys(piece)]
    if len(cited_pieces) < 2 or len(cited_pieces) != len(pieces):
        return [sentence]
    return [_ensure_terminal_punctuation(piece, sentence) for piece in cited_pieces]


def _split_latex_keys(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",")]


def _split_explicit_citation_clauses(sentence: str) -> list[str]:
    pieces: list[str] = []
    for piece in SEMICOLON_CLAUSE_BOUNDARY_RE.split(sentence):
        pieces.extend(
            marker_piece.strip()
            for marker_piece in COMMA_CLAUSE_MARKER_RE.split(piece)
            if marker_piece.strip()
        )
    return pieces


def _ensure_terminal_punctuation(piece: str, original: str) -> str:
    if piece[-1:] in ".!?":
        return piece
    terminal = original.rstrip()[-1:]
    if terminal in ".!?":
        return f"{piece}{terminal}"
    return piece


def _strip_markdown_noise(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _prepare_draft_text(text: str) -> str:
    text = _strip_markdown_noise(text)
    text = _strip_latex_comments(text)
    for environment in LATEX_ENVIRONMENTS_TO_DROP:
        text = _drop_latex_environment(text, environment)
    text = _unwrap_latex_text_commands(text)
    text = re.sub(r"\\(?:section|subsection|subsubsection|caption|label|ref)\*?\{[^}]*\}", " ", text)
    text = re.sub(r"\\(?!cite)[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _strip_latex_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        escaped = False
        kept = []
        for char in line:
            if char == "%" and not escaped:
                break
            kept.append(char)
            escaped = char == "\\" and not escaped
        lines.append("".join(kept))
    return "\n".join(lines)


def _drop_latex_environment(text: str, environment: str) -> str:
    pattern = re.compile(
        rf"\\begin\{{{re.escape(environment)}\}}.*?\\end\{{{re.escape(environment)}\}}",
        re.DOTALL,
    )
    return pattern.sub(" ", text)


def _unwrap_latex_text_commands(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\\(?:emph|textbf|textit|texttt|underline)\{([^{}]*)\}", r"\1", text)
    return text
