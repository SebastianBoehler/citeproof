from pathlib import Path

from citeproof.paper import verify_paper


def test_verify_paper_maps_sources_and_returns_claims(tmp_path: Path) -> None:
    tex = tmp_path / "paper.tex"
    bib = tmp_path / "refs.bib"
    sources = tmp_path / "sources"
    sources.mkdir()
    tex.write_text(
        "Adaptive replay improves sample efficiency \\cite{jones2023adaptive}.",
        encoding="utf-8",
    )
    bib.write_text(
        "@article{jones2023adaptive,\n"
        "  author = {Jones, A.},\n"
        "  title = {Adaptive Replay for Sparse Rewards},\n"
        "  journal = {Journal},\n"
        "  year = {2023}\n"
        "}\n",
        encoding="utf-8",
    )
    (sources / "Adaptive Replay for Sparse Rewards.txt").write_text(
        "Adaptive replay improves sample efficiency in sparse reward settings.",
        encoding="utf-8",
    )

    report = verify_paper(tex, bib, sources)

    assert report.mapped_source_count == 1
    assert report.claim_results[0]["label"] in {"supported", "partially_supported"}
