"""Real-API smoke test for analyze().

Gated by RUN_API_TESTS=1. Requires ANTHROPIC_API_KEY in env. Costs ~$0.05-0.10
per run on Opus 4.7. The point of this test is to verify the prompt produces
a study-grade Note on a known input — not just that the wiring works (the
mocked tests in test_analyze.py cover wiring).
"""

import os

import pytest

from sapling.analyze import analyze
from sapling.models import Note

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_API_TESTS") != "1",
    reason="Real-API tests are gated by RUN_API_TESTS=1",
)


SAMPLE_READING = """\
Binary search is a divide-and-conquer algorithm for locating a target value
in a sorted array. The algorithm maintains a window [low, high] over the
array. At each step it computes mid = (low + high) // 2, compares
arr[mid] to the target, and recurses or iterates on the half that could
still contain the target.

Correctness follows from the loop invariant: if the target is present, it
lies in [low, high]. Each iteration halves the window, so termination
follows. The standard implementation runs in O(log n) time and O(1) space.

Subtleties: integer overflow when computing mid (write low + (high - low)//2
to avoid it on fixed-width integers), off-by-one errors in the boundary
update, and the choice of inclusive vs. exclusive high. The "find leftmost"
and "find rightmost" variants require careful handling of the equality case
to avoid infinite loops.

Binary search is the canonical example for analyses involving the master
theorem (T(n) = T(n/2) + O(1) gives Theta(log n)) and a recurring template
for problems where a monotone predicate exists over an integer range.
"""


def test_real_api_extracts_note_with_existing_tags_reused():
    existing = ["algorithms", "complexity-analysis", "data-structures"]
    note = analyze(SAMPLE_READING, existing_tags=existing)

    assert isinstance(note, Note)
    assert note.title and note.subject
    assert 3 <= len(note.key_points) <= 8
    assert len(note.tags) >= 1
    # Topical fit should produce at least one reused tag.
    overlap = set(note.tags) & set(existing)
    assert overlap, f"Expected reuse of existing tags; got tags={note.tags}"
