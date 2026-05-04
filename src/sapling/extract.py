from pathlib import Path

import pypdf


def extract_text(path: Path) -> str:
    """Read a file and return its text content."""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        reader = pypdf.PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError(f"Unsupported file type: {suffix}")
