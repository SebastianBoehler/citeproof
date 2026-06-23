from citeproof.entailment import judge_evidence
from citeproof.models import Claim, Label, SourceChunk
from citeproof.rationales import select_rationales
from citeproof.retrieval import retrieve_evidence


def test_kim_lipani_survey_claim_is_supported_by_actual_abstract() -> None:
    judgment = judge_evidence(
        "Kim and Lipani jointly predict user actions and utterances in goal-oriented settings.",
        "We propose a deep learning-based user simulator that predicts users' satisfaction "
        "scores and actions while also jointly generating users' utterances in a multi-task "
        "manner for goal-oriented dialogue systems.",
    )

    assert judgment.label == Label.SUPPORTED


def test_gentus_introduction_claim_is_supported_by_actual_abstract() -> None:
    judgment = judge_evidence(
        "Lin et al. introduced GenTUS for task-oriented user simulation.",
        "User simulators are commonly used to train task-oriented dialogue systems. "
        "In this work, we propose a generative transformer-based user simulator (GenTUS). "
        "GenTUS generates both semantic actions and natural language utterances.",
    )

    assert judgment.label == Label.SUPPORTED


def test_yoon_discrepancy_claim_is_supported_by_actual_summary() -> None:
    judgment = judge_evidence(
        "Yoon et al. evaluated LLMs as user simulators for conversational recommendation, "
        "finding discrepancies with real behavior.",
        "We introduce a new protocol for evaluating LLMs as user simulators for "
        "conversational recommendation. By running the tasks on simulators, we show how "
        "the tasks effectively reveal discrepancies of simulators from real users.",
    )

    assert judgment.label == Label.SUPPORTED


def test_yoon_pdf_extracted_discrepancy_window_is_supported() -> None:
    judgment = judge_evidence(
        "Yoon et al. evaluated LLMs as user simulators for conversational recommendation, "
        "finding discrepancies with real behavior.",
        "Through evaluation of baseline simu-\n"
        "lators, we demonstrate these tasks effectively\n"
        "reveal deviations of language models from hu-\n"
        "man behavior, and offer insights on how to\n"
        "reduce the deviations with model selection and\n"
        "prompting strategies.1\n"
        "1 Introduction\n"
        "In everyday life, recommendations are often sought\n"
        "through conversations. Such experience is what con-\n"
        "versational recommendation systems seek to provide.",
    )

    assert judgment.label == Label.SUPPORTED


def test_select_rationale_promotes_survey_support_over_related_work() -> None:
    related_work = SourceChunk(
        source_id="yoon2024",
        citation_key="yoon2024evaluating",
        chunk_id="yoon:p8:0",
        page=8,
        text=(
            "LLMs as human proxies are increasingly used. Other work explores LLMs as "
            "user simulators in conversational search and evaluates LLMs for replicating "
            "human behavior in social science experiments."
        ),
    )
    support = SourceChunk(
        source_id="yoon2024",
        citation_key="yoon2024evaluating",
        chunk_id="yoon:p9:0",
        page=9,
        text=(
            "We introduce a new protocol for evaluating LLMs as user simulators for "
            "conversational recommendation. By running the tasks on simulators, we show "
            "how the tasks effectively reveal discrepancies of simulators from real users."
        ),
    )

    candidates = select_rationales(
        Claim(
            "Yoon et al. evaluated LLMs as user simulators for conversational recommendation, "
            "finding discrepancies with real behavior.",
            ("yoon2024evaluating",),
        ),
        [related_work, support],
        limit=1,
        min_score=0.08,
    )

    assert candidates[0].chunk_id == "yoon:p9:0"


def test_retrieval_promotes_survey_support_with_language_model_wording() -> None:
    related_work = SourceChunk(
        source_id="yoon2024",
        citation_key="yoon2024evaluating",
        chunk_id="yoon:p8:0",
        text="LLMs are often discussed as user simulators in conversational search.",
    )
    support = SourceChunk(
        source_id="yoon2024",
        citation_key="yoon2024evaluating",
        chunk_id="yoon:p1:2",
        text=(
            "Through evaluation of baseline simu-\n"
            "lators, we demonstrate these tasks effectively reveal deviations of "
            "language models from hu-\n"
            "man behavior, and offer insights on how to reduce the deviations "
            "with model selection and prompting strategies. In everyday life, "
            "recommendations are often sought through conversations. Such "
            "experience is what con-\n"
            "versational recommendation systems seek to provide."
        ),
    )

    chunks = retrieve_evidence(
        Claim(
            "Yoon et al. evaluated LLMs as user simulators for conversational recommendation, "
            "finding discrepancies with real behavior.",
            ("yoon2024evaluating",),
        ),
        [related_work, support],
        limit=1,
    )

    assert chunks[0].chunk_id == "yoon:p1:2"


def test_select_rationale_keeps_low_overlap_survey_support() -> None:
    chunk = SourceChunk(
        source_id="yoon2024",
        citation_key="yoon2024evaluating",
        chunk_id="yoon:p1:2",
        text=(
            "Through evaluation of baseline simulators, these tasks reveal deviations "
            "of language models from human behavior in conversational recommendation systems."
        ),
    )

    candidates = select_rationales(
        Claim(
            "Yoon et al. evaluated LLMs as user simulators for conversational recommendation, "
            "finding discrepancies with real behavior.",
            ("yoon2024evaluating",),
        ),
        [chunk],
        limit=1,
        min_score=0.1,
    )

    assert candidates[0].chunk_id == "yoon:p1:2"
