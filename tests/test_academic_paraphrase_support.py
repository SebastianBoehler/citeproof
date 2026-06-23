from citeproof.adjudicator import adjudicate_evidence
from citeproof.models import Label


def test_academic_abbreviation_paraphrase_is_supported() -> None:
    judgment = adjudicate_evidence(
        "Prompting assistant language models to act as users can produce poor user "
        "simulators, and stronger assistants can yield worse simulators.",
        "Assistant LMs make for poor user simulators, with the surprising finding "
        "that better assistants yield worse simulators.",
    )

    assert judgment.label == Label.SUPPORTED


def test_generated_rationale_paraphrase_is_supported() -> None:
    judgment = adjudicate_evidence(
        "Distilling step-by-step uses LLM-generated rationales as additional "
        "supervision to train smaller task-specific models.",
        "Our method extracts LLM rationales as additional supervision for training "
        "small models. We prompt the LLM to generate output labels along with "
        "rationales to justify the labels. Second, we leverage these rationales in "
        "addition to the task labels to train smaller downstream models.",
    )

    assert judgment.label == Label.SUPPORTED


def test_ppl_local_modeling_paraphrase_is_supported() -> None:
    judgment = adjudicate_evidence(
        "The long-text perplexity paper argues that low perplexity may reflect local "
        "language modeling rather than long-text understanding.",
        "We find that there is no correlation between PPL and LLMs' long-text "
        "understanding ability. Besides, PPL may only reflect the model's ability "
        "to model local information instead of catching long-range dependency.",
    )

    assert judgment.label == Label.SUPPORTED


def test_retrieval_generation_pipeline_paraphrase_is_supported() -> None:
    judgment = adjudicate_evidence(
        "The system feeds a retrieved candidate along with the query into a generator "
        "and then post-reranks generated and retrieved candidates.",
        "Given a user-issued query, we first obtain a candidate reply by information "
        "retrieval from a large database. The query, along with the candidate reply, "
        "is then fed to an utterance generator. After that we use the scorer in the "
        "retrieval system again for post-reranking.",
    )

    assert judgment.label == Label.SUPPORTED
