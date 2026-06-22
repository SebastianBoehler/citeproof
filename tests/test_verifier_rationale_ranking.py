from citeproof.models import Claim, Label, Source
from citeproof.sources import build_chunks
from citeproof.verifier import verify_claim


def test_verify_claim_surfaces_low_ranked_calibration_contradiction() -> None:
    paragraphs = [
        (
            f"Method X improves accuracy over PPO in robotics benchmark {index}. "
            "The experiment reports higher throughput and better sample efficiency for Method X."
        )
        for index in range(12)
    ]
    paragraphs.append(
        "Calibration remains unchanged after applying the method. "
        "The reliability curve and expected calibration error show no difference from PPO."
    )
    source = Source(
        source_id="paper",
        citation_key="paper",
        text="\n\n".join(paragraphs),
    )

    result = verify_claim(
        Claim("Method X improves calibration over PPO.", ("paper",)),
        build_chunks([source]),
    )

    assert result.label == Label.CONTRADICTED
    assert result.trace is not None
    atom = result.trace.atom_verifications[0]
    assert atom.contradiction_candidate_count >= 1
    assert atom.best_contradiction_rank == 1
