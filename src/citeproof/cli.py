"""CiteProof command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from citeproof.entailment import judge_evidence
from citeproof.evals.runner import run_eval_cases, run_eval_file
from citeproof.evals.draft import run_draft_eval
from citeproof.paper import render_paper_report, verify_paper
from citeproof.report import results_to_json, results_to_markdown, write_reports
from citeproof.verifier import verify_claim_text, verify_draft


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"citeproof: error: {exc}", file=sys.stderr)
        return 1


def _run_verify(args: argparse.Namespace) -> int:
    results = verify_draft(args.draft, args.sources, judge=_make_judge(args))
    write_reports(results, args.json_output, args.markdown_output)
    if args.format == "markdown":
        print(results_to_markdown(results))
    else:
        print(results_to_json(results))
    return _exit_code(results)


def _run_verify_claim(args: argparse.Namespace) -> int:
    result = verify_claim_text(args.claim, args.sources, args.cite, judge=_make_judge(args))
    print(results_to_json([result]))
    return _exit_code([result])


def _run_eval(args: argparse.Namespace) -> int:
    judge = _make_judge(args)
    if args.details_output:
        from citeproof.evals.metrics import summarize
        from citeproof.models import Label

        cases = run_eval_cases(args.dataset, judge=judge)
        summary = summarize(
            [Label(case["expected_label"]) for case in cases],
            [Label(case["predicted_label"]) for case in cases],
        )
        _write_text(args.details_output, json.dumps(cases, indent=2, sort_keys=True))
    else:
        summary = run_eval_file(args.dataset, judge=judge)
    print(summary.to_json())
    return 0


def _run_eval_suite(args: argparse.Namespace) -> int:
    from citeproof.evals.suite import run_eval_suite, suite_passed

    report = run_eval_suite(args.manifest, judge=_make_judge(args))
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output:
        _write_text(args.json_output, text)
    print(text)
    return 0 if suite_passed(report) else 2


def _run_eval_draft(args: argparse.Namespace) -> int:
    result = run_draft_eval(
        args.draft,
        args.sources,
        args.expected,
        args.bib,
        judge=_make_judge(args),
    )
    print(result["summary"])
    if args.details_output:
        import json

        _write_text(args.details_output, json.dumps(result["cases"], indent=2, sort_keys=True))
    return 0


def _run_verify_bib(args: argparse.Namespace) -> int:
    from citeproof.bibliography import render_bibliography_report, verify_bibliography

    report = verify_bibliography(args.tex, args.bib)
    if args.json_output:
        _write_text(args.json_output, report.to_json())
    if args.markdown_output:
        _write_text(args.markdown_output, render_bibliography_report(report))
    print(report.to_json() if args.format == "json" else render_bibliography_report(report))
    return 2 if report.error_count else 0


def _run_verify_paper(args: argparse.Namespace) -> int:
    report = verify_paper(args.tex, args.bib, args.sources, judge=_make_judge(args))
    if args.json_output:
        _write_text(args.json_output, report.to_json())
    if args.markdown_output:
        _write_text(args.markdown_output, render_paper_report(report))
    print(report.to_json() if args.format == "json" else render_paper_report(report))
    return _paper_exit_code(report)


def _run_verify_metadata(args: argparse.Namespace) -> int:
    from pathlib import Path

    from citeproof.bibliography import parse_bibtex
    from citeproof.metadata import build_providers, verify_entries_metadata

    entries = parse_bibtex(Path(args.bib).read_text(encoding="utf-8"))
    providers = build_providers(_split_csv(args.providers), timeout=args.timeout)
    checks = verify_entries_metadata(entries, providers=providers, limit=args.limit)
    text = json.dumps([check.to_dict() for check in checks], indent=2, sort_keys=True)
    if args.json_output:
        _write_text(args.json_output, text)
    print(text)
    bad = {"mismatch", "not_found", "error"}
    return 2 if any(check.status in bad for check in checks) else 0


def _run_hallmark_predict(args: argparse.Namespace) -> int:
    from citeproof.evals.hallmark import predictions_to_jsonl, predict_hallmark_jsonl
    from citeproof.metadata import build_providers

    providers = build_providers(_split_csv(args.providers), timeout=args.timeout)
    predictions = predict_hallmark_jsonl(args.input, providers=providers, limit=args.limit)
    text = predictions_to_jsonl(predictions)
    if args.output:
        _write_text(args.output, text)
    print(text, end="")
    return 0


def _run_mcp(_args: argparse.Namespace) -> int:
    from citeproof.mcp_server import run

    run()
    return 0


def _exit_code(results: list[object]) -> int:
    return 2 if any(result.label.value in {"contradicted", "unsupported"} for result in results) else 0


def _paper_exit_code(report: object) -> int:
    if report.bibliography["error_count"]:
        return 2
    labels = {result["label"] for result in report.claim_results}
    return 2 if labels & {"contradicted", "unsupported"} else 0


def _write_text(path: str, text: str) -> None:
    from pathlib import Path

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def _make_judge(args: argparse.Namespace):
    if getattr(args, "verifier", "heuristic") == "heuristic":
        return judge_evidence
    from citeproof.nli import build_nli_judge

    return build_nli_judge(getattr(args, "nli_model", None))


def _add_verifier_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--verifier", choices=["heuristic", "nli"], default="heuristic")
    parser.add_argument("--nli-model")


def _split_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="citeproof")
    subparsers = parser.add_subparsers(required=True)

    verify = subparsers.add_parser("verify", help="Verify a citation-bearing draft.")
    verify.add_argument("draft")
    verify.add_argument("--sources", required=True)
    verify.add_argument("--format", choices=["json", "markdown"], default="json")
    verify.add_argument("--json-output")
    verify.add_argument("--markdown-output")
    _add_verifier_args(verify)
    verify.set_defaults(func=_run_verify)

    claim = subparsers.add_parser("verify-claim", help="Verify one claim.")
    claim.add_argument("claim")
    claim.add_argument("--sources", required=True)
    claim.add_argument("--cite", action="append", default=[])
    _add_verifier_args(claim)
    claim.set_defaults(func=_run_verify_claim)

    eval_parser = subparsers.add_parser("eval", help="Run a claim-support eval JSONL file.")
    eval_parser.add_argument("dataset")
    eval_parser.add_argument("--details-output")
    _add_verifier_args(eval_parser)
    eval_parser.set_defaults(func=_run_eval)

    eval_suite = subparsers.add_parser(
        "eval-suite",
        help="Run a manifest of claim-support eval datasets.",
    )
    eval_suite.add_argument("manifest")
    eval_suite.add_argument("--json-output")
    _add_verifier_args(eval_suite)
    eval_suite.set_defaults(func=_run_eval_suite)

    eval_draft = subparsers.add_parser("eval-draft", help="Evaluate draft labels against JSONL.")
    eval_draft.add_argument("draft")
    eval_draft.add_argument("--sources", required=True)
    eval_draft.add_argument("--expected", required=True)
    eval_draft.add_argument("--bib")
    eval_draft.add_argument("--details-output")
    _add_verifier_args(eval_draft)
    eval_draft.set_defaults(func=_run_eval_draft)

    bib = subparsers.add_parser("verify-bib", help="Verify LaTeX citation keys against BibTeX.")
    bib.add_argument("tex")
    bib.add_argument("--bib", required=True)
    bib.add_argument("--format", choices=["json", "markdown"], default="json")
    bib.add_argument("--json-output")
    bib.add_argument("--markdown-output")
    bib.set_defaults(func=_run_verify_bib)

    paper = subparsers.add_parser("verify-paper", help="Verify a LaTeX paper with BibTeX and sources.")
    paper.add_argument("tex")
    paper.add_argument("--bib", required=True)
    paper.add_argument("--sources", required=True)
    paper.add_argument("--format", choices=["json", "markdown"], default="json")
    paper.add_argument("--json-output")
    paper.add_argument("--markdown-output")
    _add_verifier_args(paper)
    paper.set_defaults(func=_run_verify_paper)

    metadata = subparsers.add_parser("verify-metadata", help="Verify BibTeX entries externally.")
    metadata.add_argument("--bib", required=True)
    metadata.add_argument(
        "--providers",
        default="crossref,openalex,semanticscholar,arxiv",
        help="Comma-separated providers: crossref, openalex, semanticscholar, arxiv.",
    )
    metadata.add_argument("--limit", type=int)
    metadata.add_argument("--timeout", type=float, default=4.0)
    metadata.add_argument("--json-output")
    metadata.set_defaults(func=_run_verify_metadata)

    hallmark = subparsers.add_parser(
        "hallmark-predict",
        help="Predict HALLMARK bibliography-hallucination labels.",
    )
    hallmark.add_argument("input")
    hallmark.add_argument("--output")
    hallmark.add_argument("--providers", default="crossref,openalex,semanticscholar,arxiv")
    hallmark.add_argument("--limit", type=int)
    hallmark.add_argument("--timeout", type=float, default=4.0)
    hallmark.set_defaults(func=_run_hallmark_predict)

    mcp = subparsers.add_parser("mcp", help="Run the CiteProof MCP server.")
    mcp.set_defaults(func=_run_mcp)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
