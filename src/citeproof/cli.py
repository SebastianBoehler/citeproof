"""CiteProof command-line interface."""

from __future__ import annotations

import argparse
import sys

from citeproof.evals.runner import run_eval_file
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
    results = verify_draft(args.draft, args.sources)
    write_reports(results, args.json_output, args.markdown_output)
    if args.format == "markdown":
        print(results_to_markdown(results))
    else:
        print(results_to_json(results))
    return _exit_code(results)


def _run_verify_claim(args: argparse.Namespace) -> int:
    result = verify_claim_text(args.claim, args.sources, args.cite)
    print(results_to_json([result]))
    return _exit_code([result])


def _run_eval(args: argparse.Namespace) -> int:
    summary = run_eval_file(args.dataset)
    print(summary.to_json())
    return 0


def _run_eval_draft(args: argparse.Namespace) -> int:
    result = run_draft_eval(args.draft, args.sources, args.expected, args.bib)
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
    report = verify_paper(args.tex, args.bib, args.sources)
    if args.json_output:
        _write_text(args.json_output, report.to_json())
    if args.markdown_output:
        _write_text(args.markdown_output, render_paper_report(report))
    print(report.to_json() if args.format == "json" else render_paper_report(report))
    return _paper_exit_code(report)


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="citeproof")
    subparsers = parser.add_subparsers(required=True)

    verify = subparsers.add_parser("verify", help="Verify a citation-bearing draft.")
    verify.add_argument("draft")
    verify.add_argument("--sources", required=True)
    verify.add_argument("--format", choices=["json", "markdown"], default="json")
    verify.add_argument("--json-output")
    verify.add_argument("--markdown-output")
    verify.set_defaults(func=_run_verify)

    claim = subparsers.add_parser("verify-claim", help="Verify one claim.")
    claim.add_argument("claim")
    claim.add_argument("--sources", required=True)
    claim.add_argument("--cite", action="append", default=[])
    claim.set_defaults(func=_run_verify_claim)

    eval_parser = subparsers.add_parser("eval", help="Run a claim-support eval JSONL file.")
    eval_parser.add_argument("dataset")
    eval_parser.set_defaults(func=_run_eval)

    eval_draft = subparsers.add_parser("eval-draft", help="Evaluate draft labels against JSONL.")
    eval_draft.add_argument("draft")
    eval_draft.add_argument("--sources", required=True)
    eval_draft.add_argument("--expected", required=True)
    eval_draft.add_argument("--bib")
    eval_draft.add_argument("--details-output")
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
    paper.set_defaults(func=_run_verify_paper)

    mcp = subparsers.add_parser("mcp", help="Run the CiteProof MCP server.")
    mcp.set_defaults(func=_run_mcp)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
