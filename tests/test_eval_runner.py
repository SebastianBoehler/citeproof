from pathlib import Path

from citeproof.evals.runner import run_eval_cases, run_eval_file

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_eval_runner_reports_false_supported_rate(tmp_path: Path) -> None:
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        '{"claim":"A improves B.","evidence":"A improves B.","expected_label":"supported"}\n'
        '{"claim":"A improves B.","evidence":"A does not improve B.","expected_label":"contradicted"}\n',
        encoding="utf-8",
    )

    summary = run_eval_file(dataset)

    assert summary.total == 2
    assert summary.false_supported_rate == 0.0


def test_eval_cases_include_trust_diagnostics(tmp_path: Path) -> None:
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        '{"id":"fake-support","claim":"A improves B.",'
        '"evidence":"A improves B.","expected_label":"unsupported"}\n',
        encoding="utf-8",
    )

    cases = run_eval_cases(dataset)

    assert cases == [
        {
            "id": "fake-support",
            "expected_label": "unsupported",
            "predicted_label": "supported",
            "confidence": 0.95,
            "failure_mode": None,
            "false_supported": True,
            "pass": False,
            "reason": "Verifier gates agree.",
        }
    ]


def test_eval_cases_report_structured_failure_modes(tmp_path: Path) -> None:
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        '{"id":"unit-conflict","claim":"The evaluation used 42 percent of the dataset.",'
        '"evidence":"The evaluation used 42 examples from the dataset.",'
        '"expected_label":"contradicted"}\n'
        '{"id":"metric-negation","claim":"Method X improves F1 score over the baseline.",'
        '"evidence":"Method X improves accuracy over the baseline, with no F1 score improvement.",'
        '"expected_label":"contradicted"}\n',
        encoding="utf-8",
    )

    cases = run_eval_cases(dataset)

    assert [case["failure_mode"] for case in cases] == ["unit_conflict", "negation_conflict"]


def test_eval_cases_assert_optional_expected_failure_mode(tmp_path: Path) -> None:
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        '{"id":"diagnostic-match","claim":"The evaluation used 42 percent of the dataset.",'
        '"evidence":"The evaluation used 42 examples from the dataset.",'
        '"expected_label":"contradicted","expected_failure_mode":"unit_conflict"}\n'
        '{"id":"diagnostic-mismatch","claim":"The evaluation used 42 percent of the dataset.",'
        '"evidence":"The evaluation used 42 examples from the dataset.",'
        '"expected_label":"contradicted","expected_failure_mode":"negation_conflict"}\n',
        encoding="utf-8",
    )

    cases = run_eval_cases(dataset)

    assert [
        (
            case["expected_failure_mode"],
            case["failure_mode"],
            case["failure_mode_pass"],
            case["pass"],
        )
        for case in cases
    ] == [
        ("unit_conflict", "unit_conflict", True, True),
        ("negation_conflict", "unit_conflict", False, False),
    ]


def test_edge_cases_with_expected_failure_modes_pass() -> None:
    cases = run_eval_cases(REPO_ROOT / "examples/edge_cases/claim_support.jsonl")
    mode_cases = [case for case in cases if "expected_failure_mode" in case]

    assert {"source-silence-related", "metric-cross-contradiction", "material-anchor-swap"} <= {
        case["id"] for case in mode_cases
    }
    assert all(case["failure_mode_pass"] for case in mode_cases)
    assert all(case["pass"] for case in mode_cases)
