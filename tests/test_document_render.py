from citeproof.document_render import render_audit_document


def test_render_audit_document_preserves_latex_sections_and_citations() -> None:
    source = r"""
    \section{Method}
    Adaptive replay improves sample efficiency \cite{jones2023adaptive}.
    """
    results = [
        {
            "claim": "Adaptive replay improves sample efficiency.",
            "label": "supported",
            "confidence": 0.9,
            "citations": ["jones2023adaptive"],
        }
    ]

    html = render_audit_document(source, results)

    assert '<h2 class="doc-heading">Method</h2>' in html
    assert "Adaptive replay improves sample efficiency" in html
    assert 'data-index="0"' in html
    assert "jones2023adaptive" in html


def test_render_audit_document_does_not_bind_reused_key_to_unrelated_paragraph() -> None:
    source = r"""
    Method X outperforms PPO \cite{smith2024}.

    The ablation removes exploration \cite{smith2024}.
    """
    results = [
        {
            "claim": "Method X outperforms PPO.",
            "label": "contradicted",
            "citations": ["smith2024"],
        },
        {
            "claim": "The ablation removes exploration.",
            "label": "partially_supported",
            "citations": ["smith2024"],
        },
    ]

    html = render_audit_document(source, results)

    assert html.count('data-claim="0"') == 1
    assert html.count('data-claim="1"') == 1


def test_render_audit_document_marks_multiple_claims_in_one_paragraph() -> None:
    source = r"""
    Adaptive replay improves sample efficiency \cite{jones2023}.
    Method X outperforms PPO \cite{smith2024}.
    """
    results = [
        {
            "claim": "Adaptive replay improves sample efficiency.",
            "label": "supported",
            "citations": ["jones2023"],
        },
        {
            "claim": "Method X outperforms PPO.",
            "label": "contradicted",
            "citations": ["smith2024"],
        },
    ]

    html = render_audit_document(source, results)

    assert "multi-annotated" in html
    assert html.count('class="claim-span annotated') == 2
    assert html.count('data-claim="0"') == 1
    assert html.count('data-claim="1"') == 1


def test_render_audit_document_falls_back_without_source_text() -> None:
    html = render_audit_document(
        None,
        [
            {
                "claim": "Method X improves accuracy.",
                "label": "contradicted",
                "citations": ["smith2024"],
            }
        ],
    )

    assert "Method X improves accuracy." in html
    assert "status-contradicted" in html
