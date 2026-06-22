from citeproof.parser import extract_citation_keys, parse_claims


def test_extracts_latex_citations() -> None:
    keys = extract_citation_keys("A claim \\cite{smith2024,jones2023}.")

    assert keys == ["smith2024", "jones2023"]


def test_extracts_pandoc_citations() -> None:
    keys = extract_citation_keys("A claim [@smith2024; @jones2023].")

    assert keys == ["smith2024", "jones2023"]


def test_parse_claims_keeps_only_cited_sentences() -> None:
    claims = parse_claims("Uncited sentence. Cited sentence \\cite{smith2024}.")

    assert len(claims) == 1
    assert claims[0].text == "Cited sentence."
    assert claims[0].citation_keys == ("smith2024",)
