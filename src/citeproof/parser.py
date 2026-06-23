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
SELF_METHOD_CITATION_RE = re.compile(
    r"\bwe\s+(?:adopt|apply|employ|evaluate|investigate|leverage|study|use)\b",
    re.IGNORECASE,
)
METHOD_SCOPE_SUFFIX_RE = re.compile(r"^[,;:]?\s*(?:across|for|in|of|on|to|under|with)\b", re.IGNORECASE)
PARENTHESIZED_SOURCE_CITATION_RE = re.compile(
    r"(?P<context>\b(?:an?|the)\s+(?:[A-Za-z-]+\s+){0,4}"
    r"(?:benchmark|collection|corpus|dataset))\s*"
    r"\(\s*(?P<name>[^()\\]+?)\s*~?\s*(?P<cite>\\cite[a-zA-Z*]*\{[^}]+\})\s*\)",
    re.IGNORECASE,
)
CLAUSE_PREDICATE_RE = re.compile(
    r"\b(?:achieves?|are|captures?|computes?|contains?|covers?|defines?|has|have|"
    r"improves?|increases?|is|outperforms?|provides?|reduces?|requires?|shows?|"
    r"spans?|trains?|uses?|was|were)\b",
    re.IGNORECASE,
)
LATEX_ENVIRONMENTS_TO_DROP = (
    "abstract",
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
    cleaned = cleaned.replace("~", " ")
    cleaned = re.sub(r"[{}]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([.!?,;:])", r"\1", cleaned)
    return cleaned


def split_citation_clauses(sentence: str) -> list[str]:
    """Split one sentence into citation-local clauses when the boundary is explicit."""

    source_pieces = _scoped_parenthesized_source_citations(sentence)
    if source_pieces:
        return source_pieces
    scoped_piece = _scoped_mid_sentence_method_citation(sentence)
    if scoped_piece:
        return [scoped_piece]
    pieces = _split_explicit_citation_clauses(sentence)
    cited_pieces = [piece for piece in pieces if extract_citation_keys(piece)]
    if (
        len(cited_pieces) < 2
        or len(cited_pieces) != len(pieces)
        or not all(_looks_like_claim_clause(piece) for piece in cited_pieces)
    ):
        return [sentence]
    return [_ensure_terminal_punctuation(piece, sentence) for piece in cited_pieces]


def _split_latex_keys(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",")]


def _scoped_parenthesized_source_citations(sentence: str) -> list[str]:
    matches = list(PARENTHESIZED_SOURCE_CITATION_RE.finditer(sentence))
    if not matches:
        return []
    matched_citation_keys = [
        key
        for match in matches
        for key in extract_citation_keys(match.group("cite"))
    ]
    if set(matched_citation_keys) != set(extract_citation_keys(sentence)):
        return []
    return [
        f"{_strip_source_name(match.group('name'))} is {match.group('context')} {match.group('cite')}."
        for match in matches
    ]


def _strip_source_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("~", " ")).strip(" .;,")


def _scoped_mid_sentence_method_citation(sentence: str) -> str | None:
    matches = list(CITE_COMMAND_RE.finditer(sentence))
    if len(matches) != 1:
        return None
    match = matches[0]
    prefix = sentence[: match.end()].strip()
    suffix = sentence[match.end() :].strip()
    if not suffix or not METHOD_SCOPE_SUFFIX_RE.match(suffix):
        return None
    if not SELF_METHOD_CITATION_RE.search(clean_claim_text(prefix)):
        return None
    return _ensure_terminal_punctuation(prefix, sentence)


def _split_explicit_citation_clauses(sentence: str) -> list[str]:
    pieces: list[str] = []
    for piece in SEMICOLON_CLAUSE_BOUNDARY_RE.split(sentence):
        pieces.extend(
            marker_piece.strip()
            for marker_piece in COMMA_CLAUSE_MARKER_RE.split(piece)
            if marker_piece.strip()
        )
    return pieces


def _looks_like_claim_clause(piece: str) -> bool:
    return bool(CLAUSE_PREDICATE_RE.search(clean_claim_text(piece)))


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
    text = re.sub(r"\\documentclass(?:\[[^\]]*\])?\{[^}]+\}", " ", text)
    text = re.sub(r"\\usepackage(?:\[[^\]]*\])?\{[^}]+\}", " ", text)
    text = re.sub(r"\\(?:begin|end)\{document\}", " ", text)
    text = re.sub(r"\\(?:title|author|date|bibliography|bibliographystyle)\{[^}]*\}", " ", text)
    text = re.sub(r"\\maketitle\b", " ", text)
    text = re.sub(r"\\(?:section|subsection|subsubsection|caption|label|ref)\*?\{[^}]*\}", " ", text)
    text = re.sub(r"\\(?:begin|end)\{[^}]+\}", " ", text)
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
