from sapling.models import KeyPoint, Note


def test_note_round_trip() -> None:
    n = Note(
        title="Test",
        subject="testing",
        summary="A summary.",
        key_points=[KeyPoint(text="a", detail="b")],
        tags=["t1"],
        concepts=["c1"],
    )
    assert Note.model_validate_json(n.model_dump_json()) == n
