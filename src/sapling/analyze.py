import anthropic

from .models import Note

SYSTEM_PROMPT = """\
You are an academic study assistant. The user is doing a master's degree and
wants to retain what they read.

Given a piece of academic reading, extract a structured note that the user can
revisit later to remind themselves of the material.

Guidelines:
- Be specific. "X is important" is useless. Capture the actual claim,
  mechanism, or finding.
- Each key point's `detail` field should be a short paragraph that gives enough
  context to remind the reader why this point mattered, without re-reading the
  source.
- Prefer reusing tags from the user's existing vocabulary (provided in the user
  message) over inventing new ones. Only add a new tag when none of the
  existing tags fit.
- The `subject` is the broad academic domain. Don't be too granular here.
- Order lists from foundational/general to specific/detailed.\
"""


def analyze(text: str, existing_tags: list[str]) -> Note:
    """Extract a structured Note from a piece of reading using Claude."""
    client = anthropic.Anthropic()
    tag_block = (
        "Existing tags (prefer these; lowercase kebab-case):\n  " + ", ".join(sorted(existing_tags))
        if existing_tags
        else "No existing tags yet — establish the vocabulary."
    )
    response = client.messages.parse(
        model="claude-opus-4-7",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"{tag_block}\n\n---\n\nReading to extract:\n\n{text}",
            }
        ],
        output_format=Note,
    )
    parsed = response.parsed_output
    if parsed is None:
        raise RuntimeError(
            f"Claude refused or returned malformed output (stop_reason={response.stop_reason})"
        )
    return parsed
