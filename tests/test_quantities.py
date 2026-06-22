from decimal import Decimal

from citeproof.quantities import numbers_to_units, quantity_mentions, quantity_units


def test_quantity_units_normalizes_compact_suffixes() -> None:
    quantities = quantity_units(
        "Schema-Guided Dialogue contains over 16k task-oriented dialogues."
    )

    assert quantities == {"dialogue": (Decimal("16000"),)}


def test_quantity_units_normalizes_comma_and_decimal_digits() -> None:
    quantities = quantity_units("The corpus has 15,000 dialogues and 3.5 percent noise.")

    assert quantities == {"dialogue": (Decimal("15000"),), "%": (Decimal("3.5"),)}


def test_quantity_units_matches_scale_words_and_compact_suffixes() -> None:
    scale_word = quantity_units("WildChat contains 1 million conversations.")
    compact = quantity_units("WildChat contains 1M conversations.")

    assert scale_word == {"conversation": (Decimal("1000000"),)}
    assert compact == scale_word


def test_quantity_units_normalizes_spelled_small_numbers() -> None:
    quantities = quantity_units("The model was trained on four GPUs.")

    assert quantities == {"gpu": (Decimal("4"),)}


def test_quantity_units_normalizes_two_word_numbers() -> None:
    quantities = quantity_units("The evaluation used forty two examples.")

    assert quantities == {"example": (Decimal("42"),)}


def test_quantity_units_normalizes_percent_units() -> None:
    quantities = quantity_units("Accuracy rose by 5 percent and recall rose by 7%.")

    assert quantities == {"%": (Decimal("5"), Decimal("7"))}


def test_quantity_mentions_do_not_double_count_scale_word_overlaps() -> None:
    mentions = quantity_mentions("WildChat contains 1 million conversations.")

    assert len(mentions) == 1
    assert mentions[0].number == Decimal("1000000")
    assert mentions[0].unit == "conversation"
    assert mentions[0].text == "1 million conversations"


def test_quantity_units_deduplicates_identical_numbers_per_unit() -> None:
    quantities = quantity_units("We used 4 GPUs, then reused four GPUs.")

    assert quantities == {"gpu": (Decimal("4"),)}


def test_numbers_to_units_groups_units_by_decimal_number() -> None:
    quantities = numbers_to_units("The run used four GPUs and four samples.")

    assert quantities == {Decimal("4"): {"gpu", "sample"}}
