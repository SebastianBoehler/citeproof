import json
from pathlib import Path

from citeproof.benchmark import mutate_benchmark_file
from citeproof.cli import main


def test_mutate_benchmark_file_expands_seed_mutations(tmp_path: Path) -> None:
    seed = tmp_path / "seed.jsonl"
    output = tmp_path / "mutated.jsonl"
    seed.write_text(
        json.dumps(
            {
                "id": "real-bert",
                "claim": "BERTScore uses contextual embeddings.",
                "evidence": "BERTScore computes token similarity using contextual embeddings.",
                "expected_label": "supported",
                "mutations": [
                    {
                        "kind": "entity_swap",
                        "claim": "BLEURT uses contextual embeddings.",
                        "expected_label": "contradicted",
                        "expected_failure_mode": "entity_conflict",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = mutate_benchmark_file(seed, output)

    assert rows == [
        {
            "id": "real-bert::entity_swap",
            "parent_id": "real-bert",
            "mutation_kind": "entity_swap",
            "claim": "BLEURT uses contextual embeddings.",
            "evidence": "BERTScore computes token similarity using contextual embeddings.",
            "expected_label": "contradicted",
            "expected_failure_mode": "entity_conflict",
        }
    ]
    assert output.read_text(encoding="utf-8").strip() == json.dumps(rows[0], sort_keys=True)


def test_mutate_benchmark_cli_writes_output(tmp_path: Path) -> None:
    seed = tmp_path / "seed.jsonl"
    output = tmp_path / "mutated.jsonl"
    seed.write_text(
        json.dumps(
            {
                "id": "real-weak-correlation",
                "claim": "Word-overlap metrics correlate weakly with human judgments.",
                "evidence": "All metrics show either weak or no correlation with human judgements.",
                "expected_label": "supported",
                "mutations": [
                    {
                        "kind": "polarity_swap",
                        "claim": "Word-overlap metrics correlate strongly with human judgments.",
                        "expected_label": "contradicted",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    code = main(["mutate-benchmark", str(seed), "--output", str(output)])

    assert code == 0
    assert '"mutation_kind": "polarity_swap"' in output.read_text(encoding="utf-8")
