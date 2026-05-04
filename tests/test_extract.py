from pathlib import Path

import pytest

from sapling.extract import extract_text


def test_extract_txt(tmp_path: Path) -> None:
    f = tmp_path / "note.txt"
    f.write_text("hello world")
    assert extract_text(f) == "hello world"


def test_extract_md(tmp_path: Path) -> None:
    f = tmp_path / "note.md"
    f.write_text("# Title\n\nbody")
    assert "Title" in extract_text(f)


def test_extract_unsupported(tmp_path: Path) -> None:
    f = tmp_path / "x.docx"
    f.write_text("")
    with pytest.raises(ValueError):
        extract_text(f)
