from pathlib import Path

import pytest
from ebooklib import epub
from fpdf import FPDF


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Page one: hello sapling.")
    pdf.add_page()
    pdf.cell(0, 10, "Page two: structured study notes.")
    out = tmp_path_factory.mktemp("data") / "sample.pdf"
    pdf.output(str(out))
    return out


@pytest.fixture(scope="session")
def sample_epub(tmp_path_factory: pytest.TempPathFactory) -> Path:
    book = epub.EpubBook()
    book.set_identifier("test-epub")
    book.set_title("Sample")
    book.set_language("en")
    chapter = epub.EpubHtml(title="Chapter 1", file_name="ch1.xhtml", lang="en")
    chapter.content = (
        "<html><body>"
        "<h1>Chapter 1</h1>"
        "<p>EPUB body content for testing extraction.</p>"
        "<p>Second paragraph with more substantive prose to satisfy trafilatura's "
        "content-length heuristics during extraction.</p>"
        "</body></html>"
    )
    book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]
    out = tmp_path_factory.mktemp("data") / "sample.epub"
    epub.write_epub(str(out), book)
    return out
