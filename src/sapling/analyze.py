import logging

import anthropic
from pydantic import ValidationError

from .models import Note

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """\
ROLE
You are a study assistant for a graduate student doing a master's degree.
Your job is to turn academic readings into structured notes the student
can revisit later instead of re-reading the source.

AUDIENCE
Imagine the student opening this note 6 months from now with no memory of
the reading. The note should be enough to reconstruct the substance — not
the prose, but the claims, the mechanisms, the relationships.

QUALITY BAR
- Every key_point captures a specific, restatable claim — a finding, a
  mechanism, a definition, a counterexample. Not "X is important", not
  "the chapter discusses Y."
- Every key_point's `detail` paragraph (2-4 sentences) gives the context
  that makes the point recallable: the why behind it, the mechanism, the
  boundary conditions, the worked example. A reader should finish the
  paragraph thinking "ah, yes, I remember this", not "wait, what?"
- The `summary` is a faithful gist, not a teaser.

ANTI-PATTERNS — avoid these
- ❌ "X is important." → ✅ "X reduces variance because the estimator
   averages independent samples."
- ❌ "The author argues for Y." → ✅ "Y holds when the function is convex
   on the interval; the author's proof relies on Jensen's inequality."
- ❌ Vague tags like "concepts", "ideas", "study". Tags are for retrieval —
   they must be specific.
- ❌ Padding key_points to 8 when the source only has 4 substantive ones.
   The floor is 3 and the floor is honest.

FIELD GUIDANCE

  title (4-8 words): the specific topic or claim of THIS reading. Not the
    course name, not the book title.

  subject: the broad academic domain — e.g. "genetics", "topology",
    "philosophy of mind". Reuse existing subjects when relevant. Lowercase.
    Don't be granular ("CRISPR" is a tag, not a subject).

  summary (3-5 sentences): the gist of the reading.

  key_points (3-8 items, foundational → specific): each a single concrete
    claim with a context paragraph in `detail`.

  tags (lowercase kebab-case, 1-15 items): retrieval keys. STRONGLY prefer
    reusing tags from the EXISTING TAG VOCABULARY block in the user
    message; only add a new tag when none of the existing ones fit. New
    tags should follow kebab-case ("gene-editing", not "Gene_Editing").

  concepts (proper case preserved, up to 20): named terms-of-art that
    other notes might link to — proper nouns, defined terms, theorem
    names. "CRISPR-Cas9", "Hilbert space", "Bellman equation."

CONSTRAINTS
- Don't invent claims the source didn't make. If the source is short or
  thin, return 3 key points — don't pad to 8.
- If the source uses idiosyncratic terminology that has a more standard
  name in the field, use the standard name in tags and concepts. The
  student is being taught a field, not learning one author's vocabulary.

WORKED EXAMPLE

Input fragment: "Cas9 is a key enzyme in CRISPR systems. It cuts DNA at
specific sites. To work, it requires a guide RNA and recognition of a
short DNA motif called the PAM."

Bad output:
  key_point.text:   "CRISPR is useful."
  key_point.detail: "It's used in many fields and helps researchers."

Good output:
  key_point.text:   "Cas9 cleaves dsDNA at sites adjacent to a 5'-NGG PAM."
  key_point.detail: "Cas9 is guided to a target by a 20-nt sgRNA whose
   sequence matches the protospacer. Cleavage requires a PAM (5'-NGG for
   S. pyogenes Cas9) immediately 3' of the protospacer; without PAM, Cas9
   doesn't cut. This is the basis for the specificity of CRISPR editing."

Now extract the note from the reading provided in the user message.\
"""


def analyze(
    text: str,
    existing_tags: list[str],
    *,
    model: str = "claude-opus-4-7",
) -> Note:
    """Extract a structured Note from a piece of reading using Claude."""
    client = anthropic.Anthropic()
    user_message = _build_user_message(text, existing_tags)
    logger.info(
        "analyze: model=%s prompt_version=%s tags_in=%d text_chars=%d",
        model,
        PROMPT_VERSION,
        len(existing_tags),
        len(text),
    )
    try:
        response = client.messages.parse(
            model=model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            output_format=Note,
        )
    except ValidationError as e:
        raise RuntimeError(f"Claude returned output that failed Note validation: {e}") from e

    parsed = response.parsed_output
    if parsed is None:
        if response.stop_reason == "refusal":
            raise RuntimeError("Claude refused to extract a note from this content.")
        raise RuntimeError(
            f"Claude returned no parsed output (stop_reason={response.stop_reason})."
        )
    return parsed


def _build_user_message(text: str, existing_tags: list[str]) -> str:
    if existing_tags:
        tag_block = (
            "EXISTING TAG VOCABULARY (prefer these — only add a new tag when none fit):\n  "
            + ", ".join(sorted(existing_tags))
        )
    else:
        tag_block = "NO EXISTING TAGS YET — establish a clean lowercase kebab-case vocabulary."
    return f"{tag_block}\n\n---\n\nREADING TO EXTRACT:\n\n{text}"
