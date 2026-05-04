import re

from pydantic import BaseModel, Field, field_validator


class KeyPoint(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=300,
        description="A single key idea, in one sentence.",
    )
    detail: str = Field(
        min_length=20,
        max_length=2000,
        description=(
            "A short paragraph (2-4 sentences) elaborating on this point with the context "
            "needed to recall it later without re-reading the source."
        ),
    )


class Note(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
        description="A short title for the note (4-8 words).",
    )
    subject: str = Field(
        min_length=1,
        max_length=80,
        description=(
            "The top-level academic domain (e.g. 'genetics', 'machine learning'). "
            "Reuse existing subjects when possible. Don't be too granular here."
        ),
    )
    summary: str = Field(
        min_length=20,
        max_length=2000,
        description="A 3-5 sentence overview of what was read.",
    )
    key_points: list[KeyPoint] = Field(
        min_length=3,
        max_length=8,
        description="3-8 key points, ordered roughly from foundational to specific.",
    )
    tags: list[str] = Field(
        min_length=1,
        max_length=15,
        description=(
            "Lowercase, kebab-case tags. STRONGLY prefer reusing tags from the provided "
            "vocabulary; only add a new tag when none of the existing ones fit."
        ),
    )
    concepts: list[str] = Field(
        max_length=20,
        description=(
            "Named concepts or terms-of-art in this material that other notes might link to."
        ),
    )

    @field_validator("subject", mode="after")
    @classmethod
    def _normalize_subject(cls, v: str) -> str:
        return " ".join(v.lower().split())

    @field_validator("tags", mode="after")
    @classmethod
    def _normalize_tags(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for raw in v:
            t = re.sub(r"[\s_]+", "-", raw.lower().strip())
            t = re.sub(r"[^a-z0-9-]", "", t).strip("-")
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return out

    @field_validator("concepts", mode="after")
    @classmethod
    def _dedupe_concepts(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for raw in v:
            t = raw.strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                out.append(t)
        return out
