"""CLI wiring for benchmark comparison."""

from __future__ import annotations

import argparse
import json

from citeproof.benchmark_compare import compare_eval_suite


def add_compare_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register benchmark comparison commands."""

    parser = subparsers.add_parser(
        "compare-benchmark",
        help="Compare CiteProof against benchmark baselines.",
    )
    parser.add_argument("manifest")
    parser.add_argument("--methods", default="citeproof,lexical")
    parser.add_argument("--nli-model")
    parser.add_argument("--raw-llm-model")
    parser.add_argument("--raw-llm-base-url")
    parser.add_argument("--json-output")
    parser.set_defaults(func=_run_compare_benchmark)


def _run_compare_benchmark(args: argparse.Namespace) -> int:
    report = compare_eval_suite(
        args.manifest,
        _split_methods(args.methods),
        nli_model=args.nli_model,
        raw_llm_model=args.raw_llm_model,
        raw_llm_base_url=args.raw_llm_base_url,
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text)
    return 0


def _split_methods(raw: str) -> list[str]:
    methods = [part.strip() for part in raw.split(",") if part.strip()]
    if not methods:
        raise ValueError("At least one benchmark comparison method is required.")
    return methods
