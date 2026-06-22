from citeproof.bibliography import BibEntry
from citeproof.metadata import MetadataRecord, score_metadata_match, verify_entry_metadata


class FakeProvider:
    name = "fake"

    def __init__(self, records: list[MetadataRecord]) -> None:
        self.records = records

    def search(self, _entry: BibEntry) -> list[MetadataRecord]:
        return self.records


def test_metadata_match_scores_realistic_title_year_author() -> None:
    entry = BibEntry(
        key="smith2024",
        entry_type="article",
        fields={
            "title": "Grounded Citation Verification for Drafts",
            "author": "Smith, Ada and Jones, Bob",
            "year": "2024",
        },
    )
    record = MetadataRecord(
        provider="fake",
        title="Grounded Citation Verification for Drafts",
        year="2024",
        authors=("Ada Smith", "Bob Jones"),
    )

    score, _reason = score_metadata_match(entry, record)

    assert score >= 0.9


def test_verify_entry_metadata_marks_verified_provider_hit() -> None:
    entry = BibEntry(
        key="smith2024",
        entry_type="article",
        fields={"title": "Grounded Citation Verification for Drafts", "year": "2024"},
    )
    provider = FakeProvider(
        [
            MetadataRecord(
                provider="fake",
                title="Grounded Citation Verification for Drafts",
                year="2024",
            )
        ]
    )

    check = verify_entry_metadata(entry, providers=[provider])

    assert check.status == "verified"
    assert check.provider == "fake"


def test_verify_entry_metadata_marks_missing_hit_not_found() -> None:
    entry = BibEntry(
        key="fake2025",
        entry_type="article",
        fields={"title": "A Fabricated Paper That Does Not Exist", "year": "2025"},
    )

    check = verify_entry_metadata(entry, providers=[FakeProvider([])])

    assert check.status == "not_found"


def test_year_mismatch_cannot_be_fully_verified() -> None:
    entry = BibEntry(
        key="smith2024",
        entry_type="article",
        fields={
            "title": "Grounded Citation Verification for Drafts",
            "author": "Smith, Ada",
            "year": "2024",
        },
    )
    provider = FakeProvider(
        [
            MetadataRecord(
                provider="fake",
                title="Grounded Citation Verification for Drafts",
                year="2025",
                authors=("Ada Smith",),
            )
        ]
    )

    check = verify_entry_metadata(entry, providers=[provider])

    assert check.status == "mismatch"
