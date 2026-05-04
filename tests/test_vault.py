from pathlib import Path

import frontmatter

from sapling.models import KeyPoint, Note
from sapling.vault import existing_tags, slugify, write_note


def make_note() -> Note:
    return Note(
        title="CRISPR overview",
        subject="genetics",
        summary="A short summary.",
        key_points=[KeyPoint(text="Cas9 cuts DNA", detail="Via PAM-adjacent recognition.")],
        tags=["crispr", "gene-editing"],
        concepts=["Cas9", "PAM"],
    )


def test_slugify() -> None:
    assert slugify("Hello World!") == "hello-world"
    assert slugify("") == "note"
    assert slugify("  multi   spaces ") == "multi-spaces"


def test_write_note_creates_file(tmp_path: Path) -> None:
    path = write_note(make_note(), tmp_path, source="/tmp/source.pdf")
    assert path.exists()
    assert path.parent.name == "genetics"
    post = frontmatter.load(path)
    assert post.metadata["title"] == "CRISPR overview"
    assert post.metadata["tags"] == ["crispr", "gene-editing"]
    assert "Cas9 cuts DNA" in post.content


def test_write_note_idempotent(tmp_path: Path) -> None:
    p1 = write_note(make_note(), tmp_path, source="/tmp/x.pdf")
    p2 = write_note(make_note(), tmp_path, source="/tmp/x.pdf")
    assert p1 == p2
    assert len(list(tmp_path.rglob("*.md"))) == 1


def test_existing_tags(tmp_path: Path) -> None:
    write_note(make_note(), tmp_path, source="/tmp/x.pdf")
    tags = existing_tags(tmp_path)
    assert "crispr" in tags
    assert "gene-editing" in tags


def test_existing_tags_missing_dir(tmp_path: Path) -> None:
    assert existing_tags(tmp_path / "does-not-exist") == []
