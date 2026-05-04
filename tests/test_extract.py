from pathlib import Path

import pypdf
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


def test_extract_pdf(sample_pdf: Path) -> None:
    text = extract_text(sample_pdf)
    assert "Page one: hello sapling." in text
    assert "Page two: structured study notes." in text


def test_extract_pdf_encrypted(tmp_path: Path, sample_pdf: Path) -> None:
    writer = pypdf.PdfWriter(clone_from=str(sample_pdf))
    writer.encrypt("secret")
    encrypted = tmp_path / "encrypted.pdf"
    with encrypted.open("wb") as f:
        writer.write(f)
    with pytest.raises(ValueError, match="encrypted"):
        extract_text(encrypted)


def test_extract_pdf_no_text(tmp_path: Path) -> None:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    blank = tmp_path / "blank.pdf"
    with blank.open("wb") as f:
        writer.write(f)
    with pytest.raises(ValueError, match="no extractable text"):
        extract_text(blank)


def test_extract_epub(sample_epub: Path) -> None:
    text = extract_text(sample_epub)
    assert "EPUB body content" in text


def test_extract_epub_chapter_order(multi_chapter_epub: Path) -> None:
    text = extract_text(multi_chapter_epub)
    pos_alpha = text.find("alpha")
    pos_beta = text.find("beta")
    pos_gamma = text.find("gamma")
    assert pos_alpha != -1 and pos_beta != -1 and pos_gamma != -1, text
    # Spine declared order is gamma -> alpha -> beta
    assert pos_gamma < pos_alpha < pos_beta, (pos_gamma, pos_alpha, pos_beta)


def test_extract_html(tmp_path: Path) -> None:
    html = tmp_path / "article.html"
    html.write_text(
        "<html><head><title>T</title></head><body>"
        "<nav>menu links nav stuff</nav>"
        "<article>"
        "<h1>Real article heading</h1>"
        "<p>This is the real article body. It contains enough words that "
        "trafilatura will pick it up as the main content over the surrounding "
        "boilerplate that we want stripped out of the extracted text.</p>"
        "<p>Second paragraph with additional substantive content for the "
        "extractor's length heuristics.</p>"
        "</article>"
        "<footer>copyright footer boilerplate</footer>"
        "</body></html>",
        encoding="utf-8",
    )
    text = extract_text(html)
    assert "real article body" in text.lower()
    assert "menu links nav stuff" not in text
    assert "copyright footer boilerplate" not in text


def test_extract_html_empty(tmp_path: Path) -> None:
    html = tmp_path / "empty.html"
    html.write_text("<html><body></body></html>", encoding="utf-8")
    with pytest.raises(ValueError, match="no extractable"):
        extract_text(html)
