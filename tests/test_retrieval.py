from citeproof.models import Claim, SourceChunk
from citeproof.retrieval import retrieve_evidence


def test_retrieval_normalizes_pdf_spaced_metric_names() -> None:
    claim = Claim("BLEURT is a learned metric robust to distribution shifts.", ("sellam2020bleurt",))
    distractor = SourceChunk(
        source_id="BLEURT",
        citation_key="sellam2020bleurt",
        chunk_id="p2:generic",
        page=2,
        text="An ideal learned metric would be robust to distribution drifts.",
    )
    target = SourceChunk(
        source_id="BLEURT",
        citation_key="sellam2020bleurt",
        chunk_id="p1:abstract",
        page=1,
        text=(
            "We propose B LEURT, a learned evaluation metric based on BERT. "
            "It yields superior results when training data is out-of-distribution."
        ),
    )

    assert retrieve_evidence(claim, [distractor, target], limit=1)[0].chunk_id == "p1:abstract"
