from pydantic import BaseModel, Field


class KeyPoint(BaseModel):
    text: str = Field(description="A single key idea, in one sentence.")
    detail: str = Field(
        description=(
            "A short paragraph (2-4 sentences) elaborating on this point with the context "
            "needed to recall it later without re-reading the source."
        )
    )


class Note(BaseModel):
    title: str = Field(description="A short title for the note (4-8 words).")
    subject: str = Field(
        description=(
            "The top-level academic domain (e.g. 'genetics', 'machine learning'). "
            "Reuse existing subjects when possible. Don't be too granular here."
        )
    )
    summary: str = Field(description="A 3-5 sentence overview of what was read.")
    key_points: list[KeyPoint] = Field(
        description="3-8 key points, ordered roughly from foundational to specific."
    )
    tags: list[str] = Field(
        description=(
            "Lowercase, kebab-case tags. Reuse existing tags from the provided vocabulary "
            "when they apply — only add a new tag when none of the existing ones fit."
        )
    )
    concepts: list[str] = Field(
        description=(
            "Named concepts or terms-of-art in this material that other notes might link to."
        )
    )
