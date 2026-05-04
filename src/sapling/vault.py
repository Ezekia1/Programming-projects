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


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def write_note(
    note: Note,
    vault_dir: Path,
    source: str,
    *,
    prompt_version: str = "unknown",
) -> Path:
    """Write the note to <vault>/<subject>/<title>.md.

    Idempotent on (subject, title): re-running on a note with the same subject
    and title overwrites the file in place. The `created` timestamp is
    preserved across rewrites; `updated` always reflects the current write.
    """
    subject_dir = vault_dir / slugify(note.subject)
    subject_dir.mkdir(parents=True, exist_ok=True)
    path = subject_dir / f"{slugify(note.title)}.md"

    now = _now_iso()
    created = now
    if path.exists():
        existing = frontmatter.load(path)
        if "created" in existing.metadata:
            created = str(existing.metadata["created"])

    metadata = {
        "title": note.title,
        "subject": note.subject,
        "tags": note.tags,
        "concepts": note.concepts,
        "source": source,
        "prompt_version": prompt_version,
        "created": created,
        "updated": now,
    }

    body_parts: list[str] = [
        f"# {note.title}\n",
        f"## Summary\n\n{note.summary}\n",
        "## Key points\n",
    ]
    for kp in note.key_points:
        body_parts.append(f"### {kp.text}\n\n{kp.detail}\n")
    if note.concepts:
        concept_lines = "\n".join(f"- {c}" for c in note.concepts)
        body_parts.append(f"## Concepts\n\n{concept_lines}\n")

    post = frontmatter.Post("\n".join(body_parts), **metadata)
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return path
