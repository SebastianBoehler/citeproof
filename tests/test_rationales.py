from citeproof.models import Claim, SourceChunk
from citeproof.rationales import select_rationales


def test_select_rationale_prefers_sentence_window_with_claim_terms() -> None:
    chunk = SourceChunk(
        source_id="paper",
        citation_key="smith2024",
        chunk_id="paper:p1:0",
        page=1,
        text=(
            "The introduction discusses related work. "
            "Training with Method X required half as many hours as the baseline. "
            "The conclusion discusses deployment."
        ),
    )

    candidates = select_rationales(
        Claim("Method X reduces training time.", ("smith2024",)),
        [chunk],
        limit=1,
    )

    assert len(candidates) == 1
    assert "half as many hours" in candidates[0].text
    assert candidates[0].retrieval_method == "sentence_window"
    assert candidates[0].rank == 1


def test_select_rationale_returns_empty_for_source_silence() -> None:
    chunk = SourceChunk(
        source_id="paper",
        citation_key="smith2024",
        chunk_id="paper:p1:0",
        page=1,
        text="This paper describes a dataset collection interface.",
    )

    candidates = select_rationales(
        Claim("Method X reduces training time.", ("smith2024",)),
        [chunk],
        limit=3,
        min_score=0.2,
    )

    assert candidates == ()


def test_select_rationale_for_source_identity_requires_source_name() -> None:
    distractor = SourceChunk(
        source_id="WildChat- 1M ChatGPT Interaction Logs in the Wild",
        citation_key="zhao2024wildchat",
        chunk_id="wildchat:p11:0",
        page=11,
        text="Figure 4 shows embeddings of user prompts from W ILD C HAT and other datasets.",
    )
    chunk = SourceChunk(
        source_id="WildChat- 1M ChatGPT Interaction Logs in the Wild",
        citation_key="zhao2024wildchat",
        chunk_id="wildchat:p1:0",
        page=1,
        text=(
            "Dolma: An Open Corpus of Three Trillion Tokens for Language Model Pretraining. "
            "W ILD C HAT is a corpus of 1 million user-ChatGPT interaction logs."
        ),
    )

    candidates = select_rationales(
        Claim("WildChat is an open-domain corpus.", ("zhao2024wildchat",)),
        [distractor, chunk],
        limit=1,
        min_score=0.08,
    )

    assert len(candidates) == 1
    assert "W ILD C HAT is a corpus" in candidates[0].text


def test_select_rationale_promotes_metric_definition_support() -> None:
    distractor = SourceChunk(
        source_id="BLEURT",
        citation_key="sellam2020bleurt",
        chunk_id="bleurt:p5:0",
        page=5,
        text="Table results list a B LEURT-based metric under distribution shifts.",
    )
    support = SourceChunk(
        source_id="BLEURT",
        citation_key="sellam2020bleurt",
        chunk_id="bleurt:p2:0",
        page=2,
        text=(
            "Our insight is that it is possible to combine expressivity and robustness by "
            "pre-training a fully learned metric. To this end, we introduce B LEURT, "
            "a text generation metric based on BERT."
        ),
    )

    candidates = select_rationales(
        Claim("BLEURT is a learned metric robust to distribution shifts.", ("sellam2020bleurt",)),
        [distractor, support],
        limit=1,
        min_score=0.08,
    )

    assert candidates[0].chunk_id == "bleurt:p2:0"


def test_select_rationale_promotes_relevant_conflict_cue_window() -> None:
    distractors = " ".join(
        f"Method X improves accuracy over PPO in robotics benchmark {index}."
        for index in range(8)
    )
    chunk = SourceChunk(
        source_id="paper",
        citation_key="paper",
        chunk_id="paper:0",
        text=(
            f"{distractors} "
            "Calibration remains unchanged after applying the method. "
            "The reliability curve shows no difference from PPO."
        ),
    )

    candidates = select_rationales(
        Claim("Method X improves calibration over PPO.", ("paper",)),
        [chunk],
        limit=1,
        min_score=0.08,
    )

    assert len(candidates) == 1
    assert "Calibration remains unchanged" in candidates[0].text
    assert candidates[0].rerank_score is not None
    assert candidates[0].rerank_score > candidates[0].lexical_score
