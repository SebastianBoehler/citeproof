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


def test_quantity_units_allows_hyphenated_academic_modifiers() -> None:
    in_domain = quantity_units("The suite has 42 in-domain examples.")
    out_of_domain = quantity_units("The suite has 42 out-of-domain examples.")

    assert in_domain == {"example": (Decimal("42"),)}
    assert out_of_domain == {"example": (Decimal("42"),)}


def test_quantity_units_does_not_match_unit_prefixes_inside_longer_words() -> None:
    assert quantity_units("The score was 3 percentiles higher.") == {}
    assert quantity_units("The benchmark covers 5 conversational domains.") == {
        "domain": (Decimal("5"),)
    }


def test_quantity_units_uses_head_unit_after_supported_modifier() -> None:
    quantities = quantity_units("The dataset includes 1M dialogue turns.")

    assert quantities == {"turn": (Decimal("1000000"),)}


def test_quantity_units_recognizes_academic_count_units() -> None:
    quantities = quantity_units(
        "The study enrolled 100 patients, 12 sites, and 4 treatment arms."
    )

    assert quantities == {
        "patient": (Decimal("100"),),
        "site": (Decimal("12"),),
        "arm": (Decimal("4"),),
    }


def test_quantity_units_recognizes_participants_and_studies() -> None:
    quantities = quantity_units("The meta-analysis included 240 participants and 12 studies.")

    assert quantities == {
        "participant": (Decimal("240"),),
        "study": (Decimal("12"),),
    }


def test_quantity_units_recognizes_duration_units() -> None:
    quantities = quantity_units("The study measured mortality at 30 days and 6 months.")

    assert quantities == {
        "day": (Decimal("30"),),
        "month": (Decimal("6"),),
    }


def test_quantity_units_recognizes_dose_units() -> None:
    quantities = quantity_units("Patients received 10 mg and 2 doses.")

    assert quantities == {
        "mg": (Decimal("10"),),
        "dose": (Decimal("2"),),
    }


def test_quantity_units_normalizes_billion_suffix() -> None:
    quantities = quantity_units("The model has 7B parameters and a 32k token context.")

    assert quantities == {
        "parameter": (Decimal("7000000000"),),
        "token": (Decimal("32000"),),
    }


def test_quantity_units_recognizes_architecture_counts() -> None:
    quantities = quantity_units("The model has 12 layers and 16 attention heads.")

    assert quantities == {
        "layer": (Decimal("12"),),
        "head": (Decimal("16"),),
    }


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
