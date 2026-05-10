# Goals

Build a personal study tool that ingests readings, uses Claude to extract structured knowledge, and stores it in a markdown vault. Visualization comes later — only after enough content exists to make it worthwhile.

## Non-goals (for now)

- Tree/graph visualization. Defer to C8. Build it only after C5–C7 have been used on real coursework for at least two weeks and a concrete shape need has emerged.
- Cross-device sync, mobile, web UI. Plain markdown vault — use Obsidian, iCloud, or git for sync.
- Backwards compatibility with anything. This is a personal tool; rewrite freely.

## Operating principle

Ship the smallest thing that works end-to-end first. Each checkpoint is a state where the tool can be used on real material; checkpoints are not internal milestones.

## Checkpoints

Each checkpoint has explicit pass criteria. A checkpoint is "done" when the criteria pass — not when code exists.

### C1 — Environment ready

- `uv sync` succeeds
- `uv run pytest` passes (initial tests included)
- `uv run ruff check` clean
- `uv run sapling --help` prints help text

### C2 — Text extraction

- `extract_text(path)` handles `.txt`, `.md`, `.pdf`, `.epub`, `.html` / `.htm`
- Tests cover each format including edge cases (encrypted PDF, no-text PDF, empty HTML)
- Smoke-tested on at least one real open-access paper

### C3 — Structured extraction

- `analyze(text, existing_tags) -> Note` returns a validated Pydantic Note
- `Note` has: title, subject, summary, 3–8 key_points (text + detail), tags, concepts
- Existing tags are passed in; the prompt tells Claude to reuse them
- Tests: shape via mocked client; one real-API smoke test gated by `RUN_API_TESTS=1`

### C4 — Vault writer

- `write_note(note, vault_dir, source, prompt_version=...)` writes `<vault>/<subject-slug>/<title-slug>.md`
- Frontmatter has title, subject, tags, concepts, source, prompt_version, created, updated
- `created` is preserved across rewrites; `updated` reflects each write
- Body has `# title`, `## Summary`, `## Key points` (one H3 per point), and `## Concepts` (bullet list, omitted if empty)
- Idempotent on (subject, title): re-running on the same note overwrites in place, doesn't duplicate
- `existing_tags(vault_dir)` returns sorted unique tags from frontmatter

### C5 — End-to-end CLI

- `uv run sapling ingest <path>` runs C2 → C3 → C4
- Prints title, subject, tags, summary, key points before saving
- Confirms before write (skip with `--yes`)
- Smoke-tested on at least one real reading

### C6 — Tag reconciliation under real load

- After ingesting at least 10 notes, hand-audit: are tags consistent (case, kebab vs snake)?
- If not, tighten the prompt; consider a one-shot normalization pass over the vault

### C7 — Review/edit gate

- Before write, the structured output is shown in full (summary + each key_point's text and detail + concepts)
- User can: **accept**, **edit** (opens `$EDITOR` on a YAML view), or **reject**
- On edit save, re-validates via Pydantic; on validation failure, shows the error inline and offers to re-edit (broken YAML carried back into the editor) or abandon
- Reject means no file is written
- `--yes` skips the prompt and auto-accepts (for batch ingestion)

### C8 — Visualization (deferred)

Do not start until C5–C7 are battle-tested.

- Decision: tree (per-subject) or graph (cross-cutting via concept links)?
- Make this decision based on what the vault actually looks like, not on the original idea.

## Stop conditions

If after using the tool for 2 weeks you find yourself reaching for `grep` more than a hypothetical visualization, build a CLI search/browse instead. The goal is recall, not aesthetics.
