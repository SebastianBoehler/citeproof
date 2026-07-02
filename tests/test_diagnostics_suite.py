from citeproof.evals.runner import run_eval_file
from citeproof.evals.suite import run_eval_suite, suite_passed


def test_diagnostic_claim_support_examples_pass() -> None:
    summary = run_eval_file("examples/diagnostics/claim_support.jsonl")

    assert summary.accuracy == 1.0
    assert summary.false_supported_rate == 0.0
    assert summary.contradiction_recall == 1.0


def test_eval_suite_includes_unlocked_diagnostic_layer() -> None:
    report = run_eval_suite("examples/eval_suite.json")
    diagnostic = report["layers"]["diagnostic"]

    assert suite_passed(report) is True
    assert diagnostic["datasets"] == ["diagnostic_contradictions"]
    assert diagnostic["summary"]["accuracy"] == 1.0
