from citeproof.models import Source
from citeproof.sources import align_sources_to_bibtex


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
