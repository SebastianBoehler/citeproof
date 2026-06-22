from citeproof.evals.metrics import summarize
from citeproof.models import Label


def test_summary_reports_secondary_trust_metrics() -> None:
    summary = summarize(
        expected=[
            Label.SUPPORTED,
            Label.SUPPORTED,
            Label.CONTRADICTED,
            Label.UNSUPPORTED,
            Label.PARTIALLY_SUPPORTED,
        ],
        predicted=[
            Label.SUPPORTED,
            Label.PARTIALLY_SUPPORTED,
            Label.CONTRADICTED,
            Label.UNCERTAIN,
            Label.SUPPORTED,
        ],
    )

    assert summary.supported_precision == 0.5
    assert summary.supported_recall == 0.5
    assert summary.unsupported_recall == 0.0
    assert summary.contradiction_recall == 1.0
    assert summary.manual_review_rate == 0.4
    assert summary.to_dict()["supported_precision"] == 0.5
