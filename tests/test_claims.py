from citeproof.claims import atomize_claim
from citeproof.models import Claim


def test_atomize_preserves_original_context() -> None:
    claim = Claim(
        "WildChat contains 1M conversations and spans diverse languages.",
        ("wildchat",),
    )

    group = atomize_claim(claim)

    assert group.original.text == claim.text
    assert [atom.text for atom in group.atoms] == [
        "WildChat contains 1M conversations.",
        "WildChat spans diverse languages.",
    ]
    assert all(atom.context == claim.text for atom in group.atoms)
    assert all(atom.citation_keys == ("wildchat",) for atom in group.atoms)


def test_atomize_multiword_subject_conjunction() -> None:
    claim = Claim(
        "POMDP-based spoken dialog systems provide robustness to recognition errors "
        "and solve exact policy learning tractably for real-world dialogs.",
        ("pomdp",),
    )

    group = atomize_claim(claim)

    assert [atom.text for atom in group.atoms] == [
        "POMDP-based spoken dialog systems provide robustness to recognition errors.",
        "POMDP-based spoken dialog systems solve exact policy learning tractably for real-world dialogs.",
    ]
    assert all(atom.context == claim.text for atom in group.atoms)


def test_atomize_does_not_split_unrelated_short_sentence() -> None:
    claim = Claim(
        "BERTScore computes contextual embedding similarity.",
        ("bertscore",),
    )

    group = atomize_claim(claim)

    assert group.original.text == claim.text
    assert [atom.text for atom in group.atoms] == [claim.text]
    assert group.atoms[0].context == claim.text
