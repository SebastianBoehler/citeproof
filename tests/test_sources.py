from citeproof.models import Source
from citeproof.sources import align_sources_to_bibtex, build_chunks


def test_align_sources_to_bibtex_uses_title_overlap() -> None:
    sources = [
        Source(
            source_id="Attention Is All You Need",
            citation_key="Attention Is All You Need",
            title="Attention Is All You Need",
            text="Transformer paper text",
        )
    ]

    aligned = align_sources_to_bibtex(sources, {"vaswani2017attention": "Attention Is All You Need"})

    assert aligned[0].citation_key == "vaswani2017attention"


def test_build_chunks_preserves_pdf_page_numbers() -> None:
    source = Source(
        source_id="paper",
        citation_key="paper2024",
        title="Paper",
        text="Page one evidence.\n\nPage two evidence.",
        pages=("Page one evidence.", "Page two evidence."),
    )

    chunks = build_chunks([source])

    assert [chunk.page for chunk in chunks] == [1, 2]
    assert [chunk.chunk_id for chunk in chunks] == ["paper:p1:0", "paper:p2:0"]
