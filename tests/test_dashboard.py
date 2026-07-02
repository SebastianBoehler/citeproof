from citeproof.dashboard import paper_report_to_html, results_to_html
from citeproof.models import (
    AtomVerification,
    ClaimVerificationTrace,
    EvidenceSpan,
    FailureMode,
    Label,
    VerificationResult,
)
from citeproof.paper import PaperVerificationReport


def test_results_to_html_contains_interactive_claim_data() -> None:
    result = VerificationResult(
        claim="Method X improves accuracy.",
        label=Label.SUPPORTED,
        confidence=0.95,
        citations=("smith2024",),
        evidence=(
            EvidenceSpan(
                source_id="smith2024.txt",
                citation_key="smith2024",
                text="Method X improves accuracy over the baseline.",
                score=0.82,
            ),
        ),
        reason="Verifier gates agree.",
    )

    html = results_to_html([result])

    assert "<!doctype html>" in html
    assert "citeproof-data" in html
    assert "Method X improves accuracy." in html
    assert "smith2024" in html
    assert "Paper Text Overlay" in html
    assert "Evidence Snippets" in html
    assert "documentHtml" in html


def test_paper_report_to_html_contains_mapping_summary() -> None:
    report = PaperVerificationReport(
        bibliography={
            "error_count": 0,
            "warning_count": 1,
            "missing_bib_entries": [],
            "unused_bib_entries": [],
        },
        claim_results=[
            {
                "claim": "Adaptive replay improves sample efficiency.",
                "label": "supported",
                "confidence": 0.9,
                "citations": ["jones2023adaptive"],
                "evidence": [],
                "reason": "Verifier gates agree.",
                "failure_mode": None,
                "trace": None,
            }
        ],
        mapped_source_count=1,
        loaded_source_count=2,
    )

    html = paper_report_to_html(report)

    assert "CiteProof Paper Audit" in html
    assert "Mapped sources" in html
    assert "jones2023adaptive" in html


def test_results_to_html_makes_failure_reason_prominent() -> None:
    trace = ClaimVerificationTrace(
        claim="Method X works everywhere.",
        citations=("smith2024",),
        source_gate_status="resolved",
        atom_verifications=(
            AtomVerification(
                text="Method X works everywhere.",
                context="Method X works everywhere.",
                label=Label.PARTIALLY_SUPPORTED,
                confidence=0.72,
                failure_mode=FailureMode.SCOPE_OVERSTATEMENT,
                candidate_count=3,
                best_support_rank=1,
                best_contradiction_rank=None,
            ),
        ),
        final_label=Label.PARTIALLY_SUPPORTED,
        final_confidence=0.72,
        final_failure_mode=FailureMode.SCOPE_OVERSTATEMENT,
        review_action="narrow the claim scope",
    )
    result = VerificationResult(
        claim="Method X works everywhere.",
        label=Label.PARTIALLY_SUPPORTED,
        confidence=0.72,
        citations=("smith2024",),
        evidence=(),
        reason="Evidence supports a narrower claim than the draft states.",
        failure_mode=FailureMode.SCOPE_OVERSTATEMENT,
        trace=trace,
    )

    html = results_to_html([result])

    assert "Why this label?" in html
    assert "failure-mode-value" in html
    assert "scope_overstatement" in html
    assert "Source gate" in html
    assert "Atomic Evidence Trace" in html
    assert "Best contradiction" in html
    assert "narrow the claim scope" in html
