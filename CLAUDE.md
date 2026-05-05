# Sapling — context for Claude

Personal study tool. Ingest a reading, extract a structured note via the Claude API, write it to a markdown vault. Project goals and checkpoints are in `GOALS.md` — read that first.

## Stack

- Python 3.11+, managed with `uv`
- Anthropic SDK (`claude-opus-4-7`, adaptive thinking, structured outputs via `messages.parse` + Pydantic)
- pypdf for PDFs
- Typer + Rich for the CLI
- pytest + ruff

## Commands

| Task | Command |
|---|---|
| Install / update deps | `uv sync` |
| Run tests | `uv run pytest` |
| Lint | `uv run ruff check` |
| Format | `uv run ruff format` |
| CLI help | `uv run sapling --help` |
| Ingest a reading | `uv run sapling ingest path/to/file.pdf` |
| Ingest with verbose logs | `uv run sapling ingest path/to/file.pdf -v` |

The CLI loads `ANTHROPIC_API_KEY` from a project-local `.env` automatically (via `python-dotenv`); `export`ing it in the shell also works.

## Layout

```
src/sapling/
  models.py    # Pydantic Note + KeyPoint
  extract.py   # PDF/MD/TXT → text
  analyze.py   # text + existing tags → Note (Claude API)
  vault.py     # Note → markdown file; tag scanning
  cli.py       # Typer entrypoint
tests/         # pytest, no API calls in default suite
vault/         # the user's notes (gitignored)
```

## Conventions

- Default model is `claude-opus-4-7`. Don't downgrade for cost without asking.
- Use `messages.parse(output_format=Note)` for structured extraction. Don't hand-write JSON schemas.
- Don't add error handling for things that can't happen on internal paths. Validate at the user-input boundary (CLI args, file existence, API errors).
- Don't add comments that restate the code. A comment earns its place by explaining a non-obvious *why*.
- Tests don't hit the network by default. Real-API smoke tests are gated by `RUN_API_TESTS=1` and skipped otherwise.
- The vault under `vault/` is the user's personal data — never commit its contents.
- Cost note: each `analyze()` call is roughly $0.05–$0.20 on Opus 4.7 with adaptive thinking + high effort. Long readings (≥30 pages) can hit ~$0.40. The `PROMPT_VERSION` constant in `analyze.py` should be bumped whenever `SYSTEM_PROMPT` changes — that's how a future C6 audit will be able to identify which prompt produced which note.

## Working on this project

- Read `GOALS.md` to understand which checkpoint is in flight.
- Don't start C8 (visualization) until C5–C7 are real.
- Before claiming a checkpoint done, run its pass criteria, not just "the code looks right."
