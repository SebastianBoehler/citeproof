"""CiteProof command-line interface."""

from __future__ import annotations

import argparse
import sys

from citeproof.evals.runner import run_eval_file
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


def _run_mcp(_args: argparse.Namespace) -> int:
    from citeproof.mcp_server import run

    run()
    return 0


def _exit_code(results: list[object]) -> int:
    return 2 if any(result.label.value in {"contradicted", "unsupported"} for result in results) else 0


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

    mcp = subparsers.add_parser("mcp", help="Run the CiteProof MCP server.")
    mcp.set_defaults(func=_run_mcp)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
