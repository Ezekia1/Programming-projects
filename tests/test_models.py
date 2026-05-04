import pytest
from pydantic import ValidationError

from sapling.models import KeyPoint, Note


def _kps(n: int = 3) -> list[KeyPoint]:
    return [
        KeyPoint(text=f"point {i}", detail="A detail paragraph long enough to pass.")
        for i in range(n)
    ]


def _note(**overrides) -> Note:
    base = dict(
        title="Test note",
        subject="testing",
        summary="A summary that is at least twenty characters long.",
        key_points=_kps(),
        tags=["t1"],
        concepts=[],
    )
    base.update(overrides)
    return Note(**base)


def test_note_round_trip() -> None:
    n = _note(concepts=["c1"])
    assert Note.model_validate_json(n.model_dump_json()) == n


def test_subject_lowercased_and_collapsed() -> None:
    assert _note(subject="  Genetics  ").subject == "genetics"
    assert _note(subject="Machine\tLearning").subject == "machine learning"


def test_tags_normalized_kebab_lowercase_deduped() -> None:
    n = _note(tags=["Gene Editing", "gene-editing", "CRISPR_Cas9", "crispr-cas9"])
    assert n.tags == ["gene-editing", "crispr-cas9"]


def test_tags_strip_punctuation() -> None:
    n = _note(tags=["genetics!", "  spaces  ", "weird@chars"])
    assert "genetics" in n.tags
    assert "spaces" in n.tags
    # punctuation stripped — no hyphen because @ doesn't translate to one
    assert "weirdchars" in n.tags


def test_concepts_dedupe_case_preserving() -> None:
    n = _note(concepts=["CRISPR", "crispr", "Cas9"])
    assert n.concepts == ["CRISPR", "Cas9"]


def test_key_points_below_min_rejected() -> None:
    with pytest.raises(ValidationError):
        _note(key_points=_kps(2))


def test_key_points_above_max_rejected() -> None:
    with pytest.raises(ValidationError):
        _note(key_points=_kps(9))


def test_tags_non_empty_required() -> None:
    with pytest.raises(ValidationError):
        _note(tags=[])


def test_summary_min_length_enforced() -> None:
    with pytest.raises(ValidationError):
        _note(summary="too short")


def test_keypoint_detail_min_length_enforced() -> None:
    with pytest.raises(ValidationError):
        Note(
            title="t",
            subject="x",
            summary="A summary that is at least twenty characters long.",
            key_points=[KeyPoint(text="a", detail="b")],
            tags=["x"],
            concepts=[],
        )
