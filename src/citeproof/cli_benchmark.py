"""Benchmark-related CLI commands."""

from __future__ import annotations

import argparse

from citeproof.benchmark import mutate_benchmark_file
from citeproof.evals.external import SUPPORTED_FORMATS, convert_external_benchmark


def add_benchmark_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register benchmark utility commands."""

    mutate = subparsers.add_parser(
        "mutate-benchmark",
        help="Generate adversarial claim-support cases from mutation specs.",
    )
    mutate.add_argument("seed")
    mutate.add_argument("--output", required=True)
    mutate.set_defaults(func=_run_mutate_benchmark)

    convert = subparsers.add_parser(
        "convert-external-benchmark",
        help="Normalize external claim-evidence benchmarks to CiteProof JSONL.",
    )
    convert.add_argument("input")
    convert.add_argument("--format", choices=SUPPORTED_FORMATS, required=True)
    convert.add_argument("--output", required=True)
    convert.set_defaults(func=_run_convert_external_benchmark)


def _run_mutate_benchmark(args: argparse.Namespace) -> int:
    rows = mutate_benchmark_file(args.seed, args.output)
    print(f"Wrote {len(rows)} adversarial cases to {args.output}.")
    return 0


def _run_convert_external_benchmark(args: argparse.Namespace) -> int:
    rows = convert_external_benchmark(args.input, args.output, source_format=args.format)
    print(f"Wrote {len(rows)} {args.format} cases to {args.output}.")
    return 0
