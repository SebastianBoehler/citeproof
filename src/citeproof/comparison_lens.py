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
    r"(?P<relation>outperforms|is better than|has higher accuracy than|is superior to)\s+"
    r"(?P<right>.+?)(?:\.|$)",
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
COMPARISON_RELATIONS = {
    "outperforms": "generic",
    "is better than": "generic",
    "has higher accuracy than": "higher_accuracy",
    "is superior to": "generic",
}


@dataclass(frozen=True)
class ComparisonInspection:
    label: Label | None
    findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Comparison:
    left: str
    right: str
    relation: str
    context: tuple[str, ...] = ()


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
    if claim_comparison.relation != evidence_comparison.relation:
        return ComparisonInspection(
            Label.PARTIALLY_SUPPORTED,
            (
                "Comparison dimension mismatch: claim "
                f"{claim_comparison.relation} vs evidence {evidence_comparison.relation}",
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
    if _comparison_direction_reversed(claim_comparison, evidence_comparison, normalize_anchor):
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


def _comparison_direction_reversed(
    claim: _Comparison,
    evidence: _Comparison,
    normalize_anchor: AnchorNormalizer,
) -> bool:
    return (
        normalize_anchor(claim.left) == normalize_anchor(evidence.right)
        and normalize_anchor(claim.right) == normalize_anchor(evidence.left)
    )


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
    return material_anchors(stripped) or (stripped,)


def _comparison_anchor(text: str, material_anchors: AnchorExtractor) -> str | None:
    anchors = material_anchors(text)
    if len(anchors) != 1:
        return None
    return anchors[0]
