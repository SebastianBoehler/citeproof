from citeproof.models import Claim
from citeproof.parser import extract_citation_keys, parse_claims, split_citation_clauses


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


def test_parse_claims_splits_explicit_citation_clauses() -> None:
    claims = parse_claims(
        "Method X improves turn taking \\cite{smith2024}; "
        "Method Y reduces latency \\cite{jones2023}."
    )

    assert [claim.citation_keys for claim in claims] == [("smith2024",), ("jones2023",)]
    assert [claim.text for claim in claims] == [
        "Method X improves turn taking.",
        "Method Y reduces latency.",
    ]


def test_parse_claims_splits_comma_while_citation_clauses() -> None:
    claims = parse_claims(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, "
        "while Prefix Tuning improves accuracy on SQuAD \\cite{prefix2021}."
    )

    assert claims == [
        Claim("LoRA improves accuracy on GLUE.", ("lora2021",)),
        Claim("Prefix Tuning improves accuracy on SQuAD.", ("prefix2021",)),
    ]


def test_parse_claims_splits_comma_but_citation_clauses() -> None:
    claims = parse_claims(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, "
        "but Prefix Tuning improves accuracy on SQuAD \\cite{prefix2021}."
    )

    assert claims == [
        Claim("LoRA improves accuracy on GLUE.", ("lora2021",)),
        Claim("Prefix Tuning improves accuracy on SQuAD.", ("prefix2021",)),
    ]


def test_parse_claims_splits_comma_whereas_citation_clauses() -> None:
    claims = parse_claims(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, "
        "whereas Prefix Tuning improves accuracy on SQuAD \\cite{prefix2021}."
    )

    assert claims == [
        Claim("LoRA improves accuracy on GLUE.", ("lora2021",)),
        Claim("Prefix Tuning improves accuracy on SQuAD.", ("prefix2021",)),
    ]


def test_parse_claims_splits_comma_while_copula_claims() -> None:
    claims = parse_claims(
        "LoRA is effective on GLUE \\cite{lora2021}, "
        "while Prefix Tuning is effective on SQuAD \\cite{prefix2021}."
    )

    assert claims == [
        Claim("LoRA is effective on GLUE.", ("lora2021",)),
        Claim("Prefix Tuning is effective on SQuAD.", ("prefix2021",)),
    ]


def test_parse_claims_splits_comma_and_citation_clauses() -> None:
    claims = parse_claims(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, "
        "and Prefix Tuning improves accuracy on SQuAD \\cite{prefix2021}."
    )

    assert claims == [
        Claim("LoRA improves accuracy on GLUE.", ("lora2021",)),
        Claim("Prefix Tuning improves accuracy on SQuAD.", ("prefix2021",)),
    ]


def test_split_citation_clauses_requires_citations_on_both_sides() -> None:
    clauses = split_citation_clauses(
        "LoRA improves accuracy on GLUE \\cite{lora2021}, while the baseline is unchanged."
    )

    assert clauses == [
        "LoRA improves accuracy on GLUE \\cite{lora2021}, while the baseline is unchanged."
    ]


def test_split_citation_clauses_keeps_sentence_when_middle_piece_is_uncited() -> None:
    sentence = (
        "LoRA improves accuracy on GLUE \\cite{lora2021}, while the baseline is unchanged, "
        "and Prefix Tuning improves accuracy on SQuAD \\cite{prefix2021}."
    )

    assert split_citation_clauses(sentence) == [sentence]


def test_parse_claims_does_not_split_coordinated_citation_list() -> None:
    claims = parse_claims(
        "We compare LoRA \\cite{lora2021}, and Prefix Tuning \\cite{prefix2021} on GLUE."
    )

    assert claims == [
        Claim(
            "We compare LoRA, and Prefix Tuning on GLUE.",
            ("lora2021", "prefix2021"),
        )
    ]


def test_parse_claims_scopes_mid_sentence_method_citation() -> None:
    claims = parse_claims(
        "In this paper, we investigate QLoRA fine-tuning~\\cite{dettmers2023qlora} "
        "of four open-source instruction-tuned LLMs (1.2B--7B parameters) "
        "for next user turn prediction."
    )

    assert claims == [
        Claim(
            "In this paper, we investigate QLoRA fine-tuning.",
            ("dettmers2023qlora",),
        )
    ]


def test_parse_claims_scopes_parenthesized_dataset_citations() -> None:
    claims = parse_claims(
        "We train on 6{,}000 samples drawn equally from an open-domain corpus "
        "(WildChat~\\cite{zhao2024wildchat}) and a task-oriented corpus "
        "(Schema-Guided Dialog~\\cite{rastogi2020sgd}), and compare against pretrained base models."
    )

    assert claims == [
        Claim("WildChat is an open-domain corpus.", ("zhao2024wildchat",)),
        Claim("Schema-Guided Dialog is a task-oriented corpus.", ("rastogi2020sgd",)),
    ]


def test_parse_claims_keeps_author_citation_scope() -> None:
    claims = parse_claims(
        "Naous et al.~\\cite{naous2025flipping} recently demonstrated that "
        "assistant-trained LLMs make poor user simulators."
    )

    assert claims == [
        Claim(
            "Naous et al. recently demonstrated that assistant-trained LLMs make poor user simulators.",
            ("naous2025flipping",),
        )
    ]


def test_parse_claims_drops_latex_tables_and_comments() -> None:
    draft = (
        "\\begin{comment} Hidden claim \\cite{hidden2024}. \\end{comment}\n"
        "\\begin{table} Table claim \\cite{table2024}. \\end{table}\n"
        "\\section{Intro} Real claim \\cite{real2024}."
    )

    claims = parse_claims(draft)

    assert [claim.citation_keys for claim in claims] == [("real2024",)]


def test_parse_claims_drops_latex_preamble() -> None:
    draft = (
        "\\documentclass{article}\n"
        "\\title{Demo Paper}\n"
        "\\author{Demo Author}\n"
        "\\begin{document}\n"
        "\\maketitle\n"
        "\\section{Intro}\n"
        "Adaptive replay improves sample efficiency \\cite{jones2023adaptive}.\n"
        "\\end{document}\n"
    )

    claims = parse_claims(draft)

    assert claims == [
        Claim("Adaptive replay improves sample efficiency.", ("jones2023adaptive",))
    ]


def test_parse_claims_drops_latex_environment_wrappers() -> None:
    draft = (
        "\\begin{abstract}\n"
        "This abstract has no citation.\n"
        "\\end{abstract}\n"
        "\\begin{enumerate}\n"
        "\\item First contribution.\n"
        "\\end{enumerate}\n"
        "User simulators rely on agenda-based systems \\cite{shi2019simulators}.\n"
    )

    claims = parse_claims(draft)

    assert claims == [
        Claim("User simulators rely on agenda-based systems.", ("shi2019simulators",))
    ]
