import re
from datetime import datetime
from pathlib import Path

import frontmatter

from .models import Note


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:60] or "note"


def existing_tags(vault_dir: Path) -> list[str]:
    """Scan the vault for tags currently in use, sorted unique."""
    if not vault_dir.exists():
        return []
    tags: set[str] = set()
    for md in vault_dir.rglob("*.md"):
        post = frontmatter.load(md)
        for tag in post.metadata.get("tags") or []:
            tags.add(str(tag))
    return sorted(tags)


def write_note(note: Note, vault_dir: Path, source: str) -> Path:
    """Write the note to <vault>/<subject>/<title>.md. Idempotent on (subject, title)."""
    subject_dir = vault_dir / slugify(note.subject)
    subject_dir.mkdir(parents=True, exist_ok=True)
    path = subject_dir / f"{slugify(note.title)}.md"

    metadata = {
        "title": note.title,
        "subject": note.subject,
        "tags": note.tags,
        "concepts": note.concepts,
        "source": source,
        "updated": datetime.now().isoformat(timespec="seconds"),
    }
    body_parts: list[str] = [f"## Summary\n\n{note.summary}\n", "## Key points\n"]
    for kp in note.key_points:
        body_parts.append(f"### {kp.text}\n\n{kp.detail}\n")
    post = frontmatter.Post("\n".join(body_parts), **metadata)
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return path
