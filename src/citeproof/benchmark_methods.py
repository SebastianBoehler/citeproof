"""Benchmark comparison classifier methods."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from citeproof.adjudicator import adjudicate_evidence
from citeproof.entailment import judge_evidence
from citeproof.models import EvidenceJudgment, Label
from citeproof.text import token_overlap_ratio

Classifier = Callable[[str, str], EvidenceJudgment]
LABELS = {label.value for label in Label}

METHOD_INFO = {
    "citeproof": {
        "description": "Conservative CiteProof adjudicator with atomization and deterministic fact gates.",
        "requires": [],
    },
    "heuristic": {
        "description": "Direct deterministic evidence judge without adjudicator atomization.",
        "requires": [],
    },
    "lexical": {
        "description": "Token-overlap baseline with no contradiction reasoning.",
        "requires": [],
    },
    "nli": {
        "description": "Local transformer NLI judge only.",
        "requires": ["uv extra: nli"],
    },
    "raw-llm": {
        "description": "OpenAI-compatible chat model judge with a strict JSON prompt.",
        "requires": ["OPENAI_API_KEY"],
    },
}


def method_catalog(methods: list[str] | None = None) -> dict[str, dict[str, object]]:
    """Return public metadata for comparison methods."""

    selected = methods or list(METHOD_INFO)
    return {method: METHOD_INFO[method] for method in selected if method in METHOD_INFO}


def build_classifier(
    method: str,
    *,
    nli_model: str | None = None,
    raw_llm_model: str | None = None,
    raw_llm_base_url: str | None = None,
) -> Classifier:
    """Create a benchmark classifier by method name."""

    if method == "citeproof":
        return adjudicate_evidence
    if method == "heuristic":
        return judge_evidence
    if method == "lexical":
        return lexical_classifier
    if method == "nli":
        from citeproof.nli import build_nli_judge

        return build_nli_judge(nli_model)
    if method == "raw-llm":
        return OpenAIChatClassifier(
            raw_llm_model or os.getenv("CITEPROOF_RAW_LLM_MODEL", "gpt-4.1-mini"),
            base_url=raw_llm_base_url or os.getenv("CITEPROOF_RAW_LLM_BASE_URL"),
        )
    raise ValueError(f"Unknown benchmark comparison method: {method}")


def lexical_classifier(claim: str, evidence: str) -> EvidenceJudgment:
    """Simple token-overlap baseline with no contradiction reasoning."""

    overlap = token_overlap_ratio(claim, evidence)
    if overlap >= 0.68:
        return EvidenceJudgment(Label.SUPPORTED, min(0.95, 0.55 + overlap / 2), "Lexical overlap.")
    if overlap >= 0.38:
        return EvidenceJudgment(Label.PARTIALLY_SUPPORTED, 0.45 + overlap / 2, "Partial overlap.")
    return EvidenceJudgment(Label.UNSUPPORTED, 0.35, "Low lexical overlap.")


class OpenAIChatClassifier:
    """Raw LLM claim-evidence classifier using an OpenAI-compatible chat endpoint."""

    def __init__(self, model: str, *, base_url: str | None = None, timeout: float = 60.0) -> None:
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("raw-llm comparison requires OPENAI_API_KEY.")

    def __call__(self, claim: str, evidence: str) -> EvidenceJudgment:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify whether the evidence supports the claim. Return only JSON with "
                        "label, confidence, and reason. Labels: supported, partially_supported, "
                        "contradicted, unsupported, uncertain."
                    ),
                },
                {"role": "user", "content": f"Claim: {claim}\n\nEvidence: {evidence}"},
            ],
        }
        data = self._post(payload)
        parsed = _parse_json_object(str(data["choices"][0]["message"]["content"]))
        label = _normalize_label(str(parsed.get("label", "uncertain")))
        confidence = float(parsed.get("confidence", 0.5))
        return EvidenceJudgment(label, max(0.0, min(1.0, confidence)), str(parsed.get("reason", "")))

    def _post(self, payload: dict[str, object]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"raw-llm request failed with HTTP {exc.code}: {body}") from exc


def _parse_json_object(text: str) -> dict[str, object]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("raw-llm response did not contain a JSON object.")
        return json.loads(match.group(0))


def _normalize_label(raw: str) -> Label:
    label = raw.strip().casefold().replace("-", "_")
    aliases = {"support": "supported", "refuted": "contradicted", "neutral": "unsupported"}
    label = aliases.get(label, label)
    if label not in LABELS:
        return Label.UNCERTAIN
    return Label(label)
