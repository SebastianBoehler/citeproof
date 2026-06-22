from citeproof.dashboard import paper_report_to_html, results_to_html
from citeproof.models import EvidenceSpan, Label, VerificationResult
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
