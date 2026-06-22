from citeproof.technical_property_lens import inspect_technical_property_conflicts


def test_detects_complexity_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The algorithm runs in linear time.",
        "The algorithm runs in quadratic time.",
    )

    assert any("Complexity conflict" in finding for finding in findings)


def test_detects_inference_fidelity_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The method uses exact inference.",
        "The method uses approximate inference.",
    )

    assert any("Inference fidelity conflict" in finding for finding in findings)


def test_detects_trainability_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The encoder is frozen during training.",
        "The encoder is fine-tuned end-to-end during training.",
    )

    assert any("Trainability conflict" in finding for finding in findings)


def test_detects_reward_density_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The agent is trained with dense rewards.",
        "The agent is trained with sparse rewards.",
    )

    assert any("Reward density conflict" in finding for finding in findings)


def test_detects_evaluation_domain_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The model is evaluated on out-of-domain data.",
        "The model is evaluated on in-domain data.",
    )

    assert any("Evaluation domain conflict" in finding for finding in findings)


def test_detects_data_sensitivity_conflict() -> None:
    findings = inspect_technical_property_conflicts(
        "The dataset contains private medical records.",
        "The dataset contains public medical records.",
    )

    assert any("Data sensitivity conflict" in finding for finding in findings)


def test_ignores_evidence_with_claim_value_plus_extra_value() -> None:
    findings = inspect_technical_property_conflicts(
        "The algorithm runs in linear time.",
        "The algorithm runs in linear time for sparse inputs and quadratic time otherwise.",
    )

    assert findings == ()


def test_ignores_property_terms_in_different_contexts() -> None:
    findings = inspect_technical_property_conflicts(
        "The linear probe is trained on the encoder.",
        "The decoder has quadratic time complexity.",
    )

    assert findings == ()
