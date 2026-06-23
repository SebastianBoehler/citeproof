"""Benchmark-related CLI commands."""

from __future__ import annotations

import argparse

from citeproof.benchmark import mutate_benchmark_file


def add_benchmark_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register benchmark utility commands."""

    mutate = subparsers.add_parser(
        "mutate-benchmark",
        help="Generate adversarial claim-support cases from mutation specs.",
    )
    mutate.add_argument("seed")
    mutate.add_argument("--output", required=True)
    mutate.set_defaults(func=_run_mutate_benchmark)


def _run_mutate_benchmark(args: argparse.Namespace) -> int:
    rows = mutate_benchmark_file(args.seed, args.output)
    print(f"Wrote {len(rows)} adversarial cases to {args.output}.")
    return 0
