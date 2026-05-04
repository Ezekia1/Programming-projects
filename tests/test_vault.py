import time
from pathlib import Path

import frontmatter

from sapling.models import KeyPoint, Note
from sapling.vault import existing_tags, slugify, write_note


def make_note(**overrides) -> Note:
    base = dict(
        title="CRISPR overview",
        subject="genetics",
        summary="A summary that is at least twenty characters long for testing purposes.",
        key_points=[
            KeyPoint(
                text="Cas9 cuts dsDNA at sites adjacent to PAM",
                detail="Cas9 needs a guide RNA and recognition of a 5'-NGG PAM motif.",
            ),
            KeyPoint(
                text="CRISPR adapts immunity to invading nucleic acids",
                detail="Spacers are integrated from past infections and transcribed as crRNAs.",
            ),
            KeyPoint(
                text="Editing precision depends on guide design",
                detail=(
                    "Off-target effects are reduced by careful sgRNA selection "
                    "and HiFi Cas9 variants."
                ),
            ),
        ],
        tags=["crispr", "gene-editing"],
        concepts=["Cas9", "PAM"],
    )
    base.update(overrides)
    return Note(**base)


def test_slugify() -> None:
    assert slugify("Hello World!") == "hello-world"
    assert slugify("") == "note"
    assert slugify("  multi   spaces ") == "multi-spaces"


def test_slugify_strips_path_traversal() -> None:
    assert slugify("../../etc/passwd") == "etcpasswd"
    assert "/" not in slugify("a/b/c")


def test_write_note_creates_file(tmp_path: Path) -> None:
    path = write_note(make_note(), tmp_path, source="/tmp/source.pdf")
    assert path.exists()
    assert path.parent.name == "genetics"
    post = frontmatter.load(path)
    assert post.metadata["title"] == "CRISPR overview"
    assert post.metadata["tags"] == ["crispr", "gene-editing"]
    assert "Cas9 cuts dsDNA" in post.content


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


# --- C4 additions -----------------------------------------------------------


def test_frontmatter_includes_prompt_version_and_timestamps(tmp_path: Path) -> None:
    path = write_note(make_note(), tmp_path, source="/tmp/x.pdf", prompt_version="v7")
    md = frontmatter.load(path)
    assert md.metadata["prompt_version"] == "v7"
    assert md.metadata["created"]
    assert md.metadata["updated"]
    assert md.metadata["concepts"] == ["Cas9", "PAM"]
    assert md.metadata["source"] == "/tmp/x.pdf"


def test_created_preserved_across_rewrites(tmp_path: Path) -> None:
    p1 = write_note(make_note(), tmp_path, source="/tmp/x.pdf", prompt_version="v1")
    created_initial = frontmatter.load(p1).metadata["created"]
    time.sleep(1.1)  # ISO-second-resolution timestamps; ensure updated differs
    p2 = write_note(make_note(), tmp_path, source="/tmp/x.pdf", prompt_version="v2")
    md2 = frontmatter.load(p2)
    assert md2.metadata["created"] == created_initial
    assert md2.metadata["updated"] != created_initial
    assert md2.metadata["prompt_version"] == "v2"


def test_body_has_h1_summary_keypoints_and_concepts(tmp_path: Path) -> None:
    path = write_note(make_note(), tmp_path, source="/tmp/x.pdf")
    body = frontmatter.load(path).content
    # H1 title
    assert body.startswith("# CRISPR overview"), body[:80]
    # Required sections in expected order
    pos_summary = body.find("## Summary")
    pos_keypoints = body.find("## Key points")
    pos_concepts = body.find("## Concepts")
    assert 0 < pos_summary < pos_keypoints < pos_concepts, (
        pos_summary,
        pos_keypoints,
        pos_concepts,
    )
    # Each key_point becomes an H3
    assert "### Cas9 cuts dsDNA at sites adjacent to PAM" in body
    # Concepts rendered as bullets
    assert "- Cas9" in body
    assert "- PAM" in body


def test_concepts_section_omitted_when_no_concepts(tmp_path: Path) -> None:
    path = write_note(make_note(concepts=[]), tmp_path, source="/tmp/x.pdf")
    body = frontmatter.load(path).content
    assert "## Concepts" not in body


def test_special_characters_in_title_safe(tmp_path: Path) -> None:
    path = write_note(make_note(title="What is X / Y? (a survey)"), tmp_path, source="/tmp/x.pdf")
    assert path.exists()
    # Path doesn't contain unsafe chars
    assert "/" not in path.name
    assert "?" not in path.name
    assert "(" not in path.name


def test_existing_tags_dedupes_across_files(tmp_path: Path) -> None:
    write_note(make_note(), tmp_path, source="/tmp/a.pdf")
    write_note(
        make_note(title="Other note", tags=["crispr", "biology"]),
        tmp_path,
        source="/tmp/b.pdf",
    )
    tags = existing_tags(tmp_path)
    # crispr appears in both files, should appear once in the union
    assert tags.count("crispr") == 1
    assert "biology" in tags
    assert "gene-editing" in tags
