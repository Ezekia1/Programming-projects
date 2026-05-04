from pathlib import Path

import pypdf
import trafilatura
from ebooklib import ITEM_DOCUMENT, epub


def extract_text(path: Path) -> str:
    """Read a file and return its text content."""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".epub":
        return _extract_epub(path)
    if suffix in {".html", ".htm"}:
        return _extract_html(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf(path: Path) -> str:
    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError(f"PDF is encrypted: {path}")
    text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        raise ValueError(
            f"PDF has no extractable text (likely scanned/image-only): {path}"
        )
    return text


def _extract_epub(path: Path) -> str:
    book = epub.read_epub(str(path))
    chapters: list[str] = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        text = trafilatura.extract(item.get_content(), output_format="txt")
        if text:
            chapters.append(text)
    if not chapters:
        raise ValueError(f"EPUB has no extractable text: {path}")
    return "\n\n".join(chapters)


def _extract_html(path: Path) -> str:
    text = trafilatura.extract(path.read_bytes(), output_format="txt")
    if not text:
        raise ValueError(f"HTML has no extractable article content: {path}")
    return text
