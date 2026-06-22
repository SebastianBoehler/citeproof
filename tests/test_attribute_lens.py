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


def test_ignores_different_contexts() -> None:
    findings = inspect_attribute_conflicts(
        "The image dataset is publicly available.",
        "The text baseline is private.",
    )

    assert findings == ()
