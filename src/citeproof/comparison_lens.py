"""Comparison-direction checks for deterministic fact inspection."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from citeproof.models import Label

AnchorExtractor = Callable[[str], tuple[str, ...]]
AnchorNormalizer = Callable[[str], str]

COMPARISON_RE = re.compile(
    r"(?P<left>.+?)\s+"
    r"(?P<relation>beats|outperforms|outperformed|exceeds|is better than|is superior to|"
    r"has higher accuracy than|achieves higher accuracy than|has lower error than|"
    r"ties|is tied with|matches|is comparable to)\s+"
    r"(?P<right>.+?)(?:\.|$)",
    re.IGNORECASE,
)
PASSIVE_OUTPERFORMED_RE = re.compile(
    r"(?P<right>.+?)\s+(?:be|been|being|is|are|was|were)\s+outperformed\s+by\s+"
    r"(?P<left>.+?)(?:\.|$)",
    re.IGNORECASE,
)
COMPARISON_CONTEXT_PREFIX_RE = re.compile(
    r"^\s*(?:on|in|for)\s+(?P<context>[^,]+),\s*(?P<body>.+)$", re.IGNORECASE
)
COMPARISON_BENCHMARK_PREFIX_RE = re.compile(
    r"^\s*(?:the\s+)?(?P<context>.+?)\s+benchmark\s+shows\s+(?P<body>.+)$",
    re.IGNORECASE,
)
COMPARISON_CONTEXT_SUFFIX_RE = re.compile(
    r"(?P<right>.+?)\s+(?:on|in|for)\s+(?P<context>.+)$", re.IGNORECASE
)
PLACEHOLDER_ANCHOR_RE = re.compile(r"\b(?:Method|Model|System|Dataset|Benchmark)\s+[A-Z]\b")

@dataclass(frozen=True)
class ComparisonInspection:
    label: Label | None
    findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _RelationSpec:
    family: str
    dimension: str


@dataclass(frozen=True)
class _Comparison:
    left: str
    right: str
    relation: _RelationSpec
    context: tuple[str, ...] = ()


COMPARISON_RELATIONS = {
    "beats": _RelationSpec("higher_is_better", "generic"),
    "outperforms": _RelationSpec("higher_is_better", "generic"),
    "outperformed": _RelationSpec("higher_is_better", "generic"),
    "exceeds": _RelationSpec("higher_is_better", "generic"),
    "is better than": _RelationSpec("higher_is_better", "generic"),
    "is superior to": _RelationSpec("higher_is_better", "generic"),
    "has higher accuracy than": _RelationSpec("higher_is_better", "accuracy"),
    "achieves higher accuracy than": _RelationSpec("higher_is_better", "accuracy"),
    "has lower error than": _RelationSpec("lower_is_better", "error"),
    "ties": _RelationSpec("neutral", "generic"),
    "is tied with": _RelationSpec("neutral", "generic"),
    "matches": _RelationSpec("neutral", "generic"),
    "is comparable to": _RelationSpec("neutral", "generic"),
}


def inspect_comparison_direction(
    claim: str,
    evidence: str,
    material_anchors: AnchorExtractor,
    normalize_anchor: AnchorNormalizer,
) -> ComparisonInspection:
    claim_comparison = _extract_comparison(claim, material_anchors, normalize_anchor)
    evidence_comparison = _extract_comparison(evidence, material_anchors, normalize_anchor)
    if not claim_comparison or not evidence_comparison:
        return ComparisonInspection(None)
    if not _same_comparison_pair(claim_comparison, evidence_comparison, normalize_anchor):
        return ComparisonInspection(None)
    if _neutral_strength_mismatch(claim_comparison, evidence_comparison):
        return ComparisonInspection(
            Label.PARTIALLY_SUPPORTED,
            (
                "Comparison strength mismatch: claim "
                f"{_relation_label(claim_comparison.relation)} vs evidence "
                f"{_relation_label(evidence_comparison.relation)}",
            ),
        )
    if claim_comparison.relation != evidence_comparison.relation:
        return ComparisonInspection(
            Label.PARTIALLY_SUPPORTED,
            (
                "Comparison dimension mismatch: claim "
                f"{_relation_label(claim_comparison.relation)} vs evidence "
                f"{_relation_label(evidence_comparison.relation)}",
            ),
        )
    if not _comparison_contexts_compatible(claim_comparison, evidence_comparison, normalize_anchor):
        return ComparisonInspection(
            Label.PARTIALLY_SUPPORTED,
            (
                "Comparison context mismatch: claim "
                f"{', '.join(claim_comparison.context)} vs evidence "
                f"{', '.join(evidence_comparison.context)}",
            ),
        )
    if claim_comparison.relation.family != "neutral" and _comparison_direction_reversed(
        claim_comparison, evidence_comparison, normalize_anchor
    ):
        return ComparisonInspection(
            Label.CONTRADICTED,
            (
                "Comparison direction conflict: claim "
                f"{claim_comparison.left} > {claim_comparison.right} vs evidence "
                f"{evidence_comparison.left} > {evidence_comparison.right}",
            ),
        )
    return ComparisonInspection(None)


def _extract_comparison(
    text: str,
    material_anchors: AnchorExtractor,
    normalize_anchor: AnchorNormalizer,
) -> _Comparison | None:
    context, body = _strip_leading_comparison_context(text, material_anchors)
    passive = _extract_passive_outperformed(
        body, context, material_anchors, normalize_anchor
    )
    if passive:
        return passive
    match = COMPARISON_RE.search(body)
    if not match:
        return None
    right_text, suffix_context = _split_trailing_comparison_context(
        match.group("right"), material_anchors
    )
    left = _comparison_anchor(match.group("left"), material_anchors)
    right = _comparison_anchor(right_text, material_anchors)
    if not left or not right:
        return None
    if normalize_anchor(left) == normalize_anchor(right):
        return None
    relation = COMPARISON_RELATIONS[match.group("relation").casefold()]
    return _Comparison(left, right, relation, context + suffix_context)


def _extract_passive_outperformed(
    body: str,
    leading_context: tuple[str, ...],
    material_anchors: AnchorExtractor,
    normalize_anchor: AnchorNormalizer,
) -> _Comparison | None:
    match = PASSIVE_OUTPERFORMED_RE.search(body)
    if not match:
        return None
    left_text, suffix_context = _split_trailing_comparison_context(
        match.group("left"), material_anchors
    )
    left = _comparison_anchor(left_text, material_anchors)
    right = _comparison_anchor(match.group("right"), material_anchors)
    if not left or not right:
        return None
    if normalize_anchor(left) == normalize_anchor(right):
        return None
    return _Comparison(
        left,
        right,
        COMPARISON_RELATIONS["outperformed"],
        leading_context + suffix_context,
    )


def _comparison_direction_reversed(
    claim: _Comparison,
    evidence: _Comparison,
    normalize_anchor: AnchorNormalizer,
) -> bool:
    return (
        normalize_anchor(claim.left) == normalize_anchor(evidence.right)
        and normalize_anchor(claim.right) == normalize_anchor(evidence.left)
    )


def _relation_label(relation: _RelationSpec) -> str:
    return f"{relation.family}/{relation.dimension}"


def _neutral_strength_mismatch(claim: _Comparison, evidence: _Comparison) -> bool:
    return claim.relation.family != evidence.relation.family and "neutral" in {
        claim.relation.family,
        evidence.relation.family,
    }


def _same_comparison_pair(
    claim: _Comparison,
    evidence: _Comparison,
    normalize_anchor: AnchorNormalizer,
) -> bool:
    claim_pair = {normalize_anchor(claim.left), normalize_anchor(claim.right)}
    evidence_pair = {normalize_anchor(evidence.left), normalize_anchor(evidence.right)}
    return claim_pair == evidence_pair


def _comparison_contexts_compatible(
    claim: _Comparison,
    evidence: _Comparison,
    normalize_anchor: AnchorNormalizer,
) -> bool:
    if not claim.context or not evidence.context:
        return True
    claim_contexts = {normalize_anchor(context) for context in claim.context}
    return any(normalize_anchor(context) in claim_contexts for context in evidence.context)


def _strip_leading_comparison_context(
    text: str,
    material_anchors: AnchorExtractor,
) -> tuple[tuple[str, ...], str]:
    for pattern in (COMPARISON_CONTEXT_PREFIX_RE, COMPARISON_BENCHMARK_PREFIX_RE):
        match = pattern.match(text)
        if match:
            return _context_anchors(match.group("context"), material_anchors), match.group("body")
    return (), text


def _split_trailing_comparison_context(
    text: str,
    material_anchors: AnchorExtractor,
) -> tuple[str, tuple[str, ...]]:
    match = COMPARISON_CONTEXT_SUFFIX_RE.match(text.strip())
    if not match:
        return text, ()
    return match.group("right"), _context_anchors(match.group("context"), material_anchors)


def _context_anchors(text: str, material_anchors: AnchorExtractor) -> tuple[str, ...]:
    stripped = text.strip(" .,;:()[]{}")
    if not stripped:
        return ()
    anchors = material_anchors(stripped)
    if len(anchors) == 1 and _normalize_context_key(anchors[0]) == _normalize_context_key(stripped):
        return anchors
    return (stripped,)


def _normalize_context_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _comparison_anchor(text: str, material_anchors: AnchorExtractor) -> str | None:
    anchors = material_anchors(text)
    if len(anchors) != 1:
        placeholder = PLACEHOLDER_ANCHOR_RE.search(text)
        return placeholder.group(0) if placeholder else None
    return anchors[0]
