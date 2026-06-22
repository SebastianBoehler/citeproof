from citeproof.attribute_lens import inspect_attribute_conflicts


def test_detects_modality_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The dataset contains 10,000 images.",
        "The dataset contains 10,000 text samples.",
    )

    assert any("Modality conflict" in finding for finding in findings)


def test_detects_task_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The method improves summarization performance.",
        "The method improves translation performance.",
    )

    assert any("Task conflict" in finding for finding in findings)


def test_detects_split_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The model was evaluated on the test set.",
        "The model was evaluated on the validation set.",
    )

    assert any("Split conflict" in finding for finding in findings)


def test_detects_language_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The benchmark evaluates German documents.",
        "The benchmark evaluates English documents.",
    )

    assert any("Language conflict" in finding for finding in findings)


def test_detects_optimizer_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The model uses Adam optimization.",
        "The model uses SGD optimization.",
    )

    assert any("Optimizer conflict" in finding for finding in findings)


def test_detects_availability_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The dataset is publicly available.",
        "The dataset is not publicly available.",
    )

    assert any("Availability conflict" in finding for finding in findings)


def test_detects_delayed_availability_negation() -> None:
    findings = inspect_attribute_conflicts(
        "The dataset is publicly available.",
        "The dataset is not yet publicly available.",
    )

    assert any("Availability conflict" in finding for finding in findings)


def test_ignores_different_contexts() -> None:
    findings = inspect_attribute_conflicts(
        "The image dataset is publicly available.",
        "The text baseline is private.",
    )

    assert findings == ()


def test_ignores_evidence_with_claim_value_plus_extra_value() -> None:
    findings = inspect_attribute_conflicts(
        "The dataset contains images.",
        "The dataset contains images and text captions.",
    )

    assert findings == ()


def test_ignores_ordinary_table_reference() -> None:
    findings = inspect_attribute_conflicts(
        "The dataset contains images.",
        "Table 1 reports that the dataset contains images.",
    )

    assert findings == ()


def test_detects_supervision_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The method uses supervised training.",
        "The method uses unsupervised training without labels.",
    )

    assert any("Supervision conflict" in finding for finding in findings)


def test_detects_study_design_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The study is randomized.",
        "The study is observational and not randomized.",
    )

    assert any("Study design conflict" in finding for finding in findings)


def test_detects_summarization_style_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The system performs abstractive summarization.",
        "The system performs extractive summarization.",
    )

    assert any("Summarization style conflict" in finding for finding in findings)


def test_detects_agent_setting_conflict() -> None:
    findings = inspect_attribute_conflicts(
        "The policy is trained in a multi-agent environment.",
        "The policy is trained in a single-agent environment.",
    )

    assert any("Agent setting conflict" in finding for finding in findings)


def test_ignores_method_attribute_terms_in_different_contexts() -> None:
    findings = inspect_attribute_conflicts(
        "The supervised baseline is reported in Table 1.",
        "The method uses unsupervised training.",
    )

    assert findings == ()
