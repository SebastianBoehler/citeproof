"""Controlled technical property conflict checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from citeproof.text import tokenize


@dataclass(frozen=True)
class TechnicalPropertyGroup:
    label: str
    values: tuple[tuple[str, tuple[str, ...]], ...]


GROUPS = (
    TechnicalPropertyGroup(
        "Complexity",
        (
            ("constant", (r"\bconstant\s+time\b", r"\bo\s*\(\s*1\s*\)",)),
            ("logarithmic", (r"\blogarithmic\b", r"\bo\s*\(\s*log\s*n\s*\)",)),
            ("linear", (r"\blinear\s+(?:time|complexity)\b", r"\bo\s*\(\s*n\s*\)",)),
            (
                "quadratic",
                (r"\bquadratic\s+(?:time|complexity)\b", r"\bo\s*\(\s*n\s*\^?\s*2\s*\)"),
            ),
            (
                "cubic",
                (r"\bcubic\s+(?:time|complexity)\b", r"\bo\s*\(\s*n\s*\^?\s*3\s*\)"),
            ),
            ("exponential", (r"\bexponential\s+(?:time|complexity)\b", r"\bo\s*\(\s*2\^n\s*\)")),
        ),
    ),
    TechnicalPropertyGroup(
        "Inference fidelity",
        (
            ("exact", (r"\bexact\s+(?:attention|algorithm|computation|inference|method)\b",)),
            (
                "approximate",
                (
                    r"\bapproximate\s+(?:attention|algorithm|computation|inference|method)\b",
                    r"\bapproximation\b",
                ),
            ),
        ),
    ),
    TechnicalPropertyGroup(
        "Memory representation",
        (
            (
                "symbolic knowledge graph",
                (r"\bsymbolic\s+knowledge\s+graph\b", r"\bknowledge\s+graph\b"),
            ),
            (
                "dense vector index",
                (r"\bdense\s+(?:vector\s+)?index\b", r"\bvector\s+index\b"),
            ),
        ),
    ),
    TechnicalPropertyGroup(
        "Trainability",
        (
            ("frozen", (r"\bfrozen\b", r"\bkept\s+fixed\b")),
            ("fine-tuned", (r"\bfine[- ]tuned\b", r"\bfine[- ]tuning\b")),
        ),
    ),
    TechnicalPropertyGroup(
        "Reward density",
        (
            ("dense", (r"\bdense\s+rewards?\b",)),
            ("sparse", (r"\bsparse\s+rewards?\b",)),
        ),
    ),
    TechnicalPropertyGroup(
        "Evaluation domain",
        (
            ("in-domain", (r"\bin[- ]domain\b",)),
            ("out-of-domain", (r"\bout[- ]of[- ]domain\b",)),
        ),
    ),
    TechnicalPropertyGroup(
        "Data sensitivity",
        (
            ("private", (r"\bprivate\s+(?:medical\s+)?records?\b", r"\bprivate\s+data\b")),
            ("public", (r"\bpublic\s+(?:medical\s+)?records?\b", r"\bpublic\s+data\b")),
        ),
    ),
    TechnicalPropertyGroup(
        "Data origin",
        (
            (
                "synthetic",
                (
                    r"\bsynthetic\s+(?:clinical\s+)?(?:data|dialogues?|images?|interactions?|queries|records?)\b",
                    r"\bsynthetic\s+user\s+(?:dialogues?|interactions?|queries)\b",
                    r"\bsimulated\s+(?:user\s+)?(?:data|dialogues?|images?|interactions?|queries|records?)\b",
                ),
            ),
            (
                "real",
                (
                    r"\breal\s+(?:clinical\s+)?(?:data|dialogues?|images?|interactions?|queries|records?)\b",
                    r"\breal\s+user\s+(?:dialogues?|interactions?|queries)\b",
                    r"\breal\s+patient\s+records?\b",
                ),
            ),
        ),
    ),
    TechnicalPropertyGroup(
        "Trainable scope",
        (
            ("all model weights", (r"\ball\s+(?:model\s+)?weights\b", r"\ball\s+parameters\b")),
            ("adapter weights", (r"\badapter\s+weights\b", r"\blow[- ]rank\s+adapter\s+weights\b")),
            (
                "frozen base weights",
                (
                    r"\b(?:base|model|pretrained)\s+weights\s+(?:are\s+)?frozen\b",
                    r"\bkeeps?\s+(?:base|model|pretrained)\s+weights\s+frozen\b",
                ),
            ),
        ),
    ),
    TechnicalPropertyGroup(
        "Architecture family",
        (
            ("dense transformer", (r"\bdense\s+transformer\b",)),
            (
                "mixture-of-experts",
                (r"\bmixture[- ]of[- ]experts\b", r"\bmoe\b"),
            ),
        ),
    ),
    TechnicalPropertyGroup(
        "Pretraining objective",
        (
            (
                "causal language modeling",
                (r"\bcausal\s+language\s+model(?:ing)?\b", r"\bclm\b"),
            ),
            (
                "masked language modeling",
                (r"\bmasked\s+language\s+model(?:ing)?\b", r"\bmlm\b"),
            ),
            (
                "replaced-token detection",
                (r"\breplaced[- ]token\s+detection\b", r"\brtd\b"),
            ),
        ),
    ),
    TechnicalPropertyGroup(
        "Evaluation setting",
        (
            ("zero-shot", (r"\bzero[- ]shot\b",)),
            ("one-shot", (r"\bone[- ]shot\b",)),
            ("few-shot", (r"\bfew[- ]shot\b",)),
        ),
    ),
    TechnicalPropertyGroup(
        "Decoding strategy",
        (
            ("greedy search", (r"\bgreedy\s+(?:search|decoding)\b",)),
            ("beam search", (r"\bbeam\s+(?:search|decoding)\b",)),
            ("sampling", (r"\bsampling\b", r"\bsample[- ]based\s+decoding\b")),
        ),
    ),
)

TRIGGER_WORDS_RE = re.compile(
    r"\b("
    r"adapter|all|approximate|approximation|architecture|attention|base|beam|causal|clinical|clm|constant|"
    r"cubic|data|decod(?:e|es|ed|ing)|dense|detection|domain|exact|experts?|"
    r"exponential|few|fine|fixed|frozen|graph|greedy|index|inference|keeps?|kept|knowledge|"
    r"language|linear|logarithmic|low|masked|medical|memory|mlm|model|modeling|moe|objective|one|out|"
    r"parameters|pretrained|private|public|quadratic|rank|records?|replaced|rewards?|"
    r"real|rtd|sampling|search|shot|simulated|sparse|synthetic|time|token|transformer|"
    r"tuned|tuning|user|vector|weights?|zero"
    r")\b",
    re.IGNORECASE,
)
SUBJECT_TERMS = {
    "algorithm",
    "architecture",
    "attention",
    "classifier",
    "index",
    "memory",
    "method",
    "model",
    "retrieval",
    "system",
    "training",
}


def inspect_technical_property_conflicts(claim: str, evidence: str) -> tuple[str, ...]:
    """Return deterministic hard conflicts for controlled technical properties."""

    findings: list[str] = []
    for group in GROUPS:
        claim_values = set(_mentioned_values(group, claim))
        evidence_values = set(_mentioned_values(group, evidence))
        if not claim_values or not evidence_values or claim_values & evidence_values:
            continue
        for claim_value in claim_values:
            for evidence_value in evidence_values:
                if _context_overlaps(claim, evidence):
                    findings.append(
                        f"{group.label} conflict: claim says {claim_value} "
                        f"while evidence says {evidence_value}."
                    )
    return tuple(dict.fromkeys(findings))


def _mentioned_values(group: TechnicalPropertyGroup, text: str) -> tuple[str, ...]:
    values: list[str] = []
    for value, patterns in group.values:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            values.append(value)
    return tuple(values)


def _context_overlaps(claim: str, evidence: str) -> bool:
    claim_tokens = _context_tokens(claim)
    evidence_tokens = _context_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    if len(claim_tokens & evidence_tokens) / min(len(claim_tokens), len(evidence_tokens)) >= 0.67:
        return True
    return len((claim_tokens & evidence_tokens) & SUBJECT_TERMS) >= 2


def _context_tokens(text: str) -> set[str]:
    tokens = set(tokenize(TRIGGER_WORDS_RE.sub(" ", text)))
    tokens.update(token for token in tokenize(text) if token in SUBJECT_TERMS)
    return tokens
