import logging
import os
from pathlib import Path

import anthropic
import typer
import yaml
from dotenv import find_dotenv, load_dotenv
from pydantic import ValidationError
from rich.console import Console
from rich.markup import escape
from rich.prompt import Prompt

from .analyze import PROMPT_VERSION, SYSTEM_PROMPT, _build_user_message, analyze
from .extract import extract_text
from .models import Note
from .vault import existing_tags, write_note

# Opus 4.7 pricing — $5/M input, $25/M output. Update if model or pricing changes.
_INPUT_USD_PER_M = 5.0
_OUTPUT_USD_PER_M = 25.0
_MAX_OUTPUT_TOKENS = 16_000

app = typer.Typer(help="Sapling — ingest readings, build a knowledge tree.", no_args_is_help=True)
console = Console()


@app.callback()
def _root() -> None:
    """Anchor for subcommand mode (so the CLI exposes `sapling <command>`)."""


@app.command()
def ingest(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="File to ingest (.txt, .md, .pdf, .epub, .html).",
    ),
    vault: Path = typer.Option(Path("vault"), help="Vault directory."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the review prompt and auto-accept the note."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show INFO logs from analyze/extract/vault."
    ),
) -> None:
    """Extract a structured note from a reading and save it to the vault."""
    # find_dotenv(usecwd=True) walks UP from cwd looking for .env; the
    # default load_dotenv() walks up from this module's location, which is
    # wrong for an installed CLI.
    load_dotenv(find_dotenv(usecwd=True))
    if verbose:
        logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

    # The Anthropic SDK raises a bare TypeError at client construction time
    # when no auth is set, which doesn't get caught by AuthenticationError
    # below. Fail fast with a clean message instead.
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        console.print(
            "[red]ANTHROPIC_API_KEY is missing.[/red] "
            "Set it in your shell or in a .env file in this directory."
        )
        raise typer.Exit(code=1)

    console.print(f"[dim]Reading[/dim] {path}")
    try:
        text = extract_text(path)
    except ValueError as e:
        console.print(f"[red]Cannot extract text:[/red] {e}")
        raise typer.Exit(code=1) from None
    console.print(f"[dim]Extracted[/dim] {len(text):,} characters")

    tags = existing_tags(vault)
    console.print(f"[dim]Existing tags:[/dim] {len(tags)}")

    _print_cost_preview(text, tags)

    try:
        with console.status(
            "[dim]Analyzing… (30-60s with adaptive thinking)[/dim]", spinner="dots"
        ):
            note = analyze(text, tags)
    except anthropic.AuthenticationError:
        console.print(
            "[red]ANTHROPIC_API_KEY is missing or invalid.[/red] "
            "Set it in your shell or in a .env file in this directory."
        )
        raise typer.Exit(code=1) from None
    except anthropic.APIError as e:
        console.print(f"[red]API error:[/red] {e}")
        raise typer.Exit(code=1) from None
    except RuntimeError as e:
        console.print(f"[red]Analysis failed:[/red] {e}")
        raise typer.Exit(code=1) from None

    _print_note_review(note)

    final_note = _review_loop(note, yes=yes)
    if final_note is None:
        console.print("[yellow]Note rejected, nothing saved.[/yellow]")
        raise typer.Exit(code=0)

    out = write_note(final_note, vault, source=str(path.resolve()), prompt_version=PROMPT_VERSION)
    console.print(f"[green]Saved[/green] {out}")


def _print_cost_preview(text: str, tags: list[str]) -> None:
    """Best-effort input-token + cost preview. Silently skips on any failure
    (auth, network) — the actual analyze() call has its own error handling."""
    try:
        client = anthropic.Anthropic()
        result = client.messages.count_tokens(
            model="claude-opus-4-7",
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_message(text, tags)}],
        )
        in_tokens = result.input_tokens
        in_cost = in_tokens * _INPUT_USD_PER_M / 1_000_000
        out_max_cost = _MAX_OUTPUT_TOKENS * _OUTPUT_USD_PER_M / 1_000_000
        console.print(
            f"[dim]Input: {in_tokens:,} tokens (~${in_cost:.2f}). "
            f"Output: typical $0.10–$0.20, max ~${out_max_cost:.2f}.[/dim]"
        )
    except Exception:
        # Any failure here is non-fatal — the real analyze call will surface it.
        console.print("[dim]Cost preview unavailable.[/dim]")


def _print_note_review(note: Note) -> None:
    """Print the full note for human review before save.

    All interpolated user-content strings are passed through `rich.markup.escape`
    because brackets in academic prose ('arr[mid]', '[1, 2, 3]') get interpreted
    as Rich markup tags otherwise and silently swallow content.
    """
    console.rule(escape(note.title))
    console.print(f"[dim]subject:[/dim] {escape(note.subject)}")
    console.print(f"[dim]tags:[/dim] {escape(', '.join(note.tags))}")
    if note.concepts:
        console.print(f"[dim]concepts:[/dim] {escape(', '.join(note.concepts))}")
    console.print(f"\n[bold]Summary[/bold]\n{escape(note.summary)}\n")
    console.print("[bold]Key points[/bold]")
    for kp in note.key_points:
        console.print(f"\n  [bold]• {escape(kp.text)}[/bold]")
        console.print(f"    [dim]{escape(kp.detail)}[/dim]")
    console.rule()


_EDIT_HEADER = """\
# Edit the note below in YAML. Lines starting with '#' are stripped on save.
# Save and exit to apply, or close without saving / wipe contents to abandon.
#
"""


def _review_loop(note: Note, *, yes: bool) -> Note | None:
    """Three-way review: accept / edit / reject.

    Returns the (possibly edited) Note on accept, or None on reject.
    With yes=True, auto-accepts without prompting.
    """
    if yes:
        return note

    while True:
        choice = Prompt.ask(
            "Save this note?",
            choices=["a", "e", "r"],
            default="a",
        )
        if choice == "a":
            return note
        if choice == "r":
            return None
        # 'e' — edit
        edited = _edit_note(note)
        if edited is None:
            console.print("[dim]Edit abandoned. Reverting to the original note.[/dim]")
            continue
        note = edited
        _print_note_review(note)


def _edit_note(note: Note) -> Note | None:
    """Open the note as YAML in $EDITOR; loop on validation failure.

    Returns the validated edited Note, or None if the user gives up.
    """
    initial_yaml = yaml.safe_dump(note.model_dump(), sort_keys=False, allow_unicode=True)
    text_for_editor = _EDIT_HEADER + initial_yaml

    while True:
        edited_text = typer.edit(text_for_editor, extension=".yaml")
        if edited_text is None:
            return None  # editor exited without saving
        clean_text = "\n".join(
            line for line in edited_text.splitlines() if not line.lstrip().startswith("#")
        ).strip()
        if not clean_text:
            return None  # contents wiped → treat as abandon

        try:
            data = yaml.safe_load(clean_text)
            return Note.model_validate(data)
        except (yaml.YAMLError, ValidationError) as e:
            console.print(f"[red]Edit failed validation:[/red]\n{e}")
            if not Prompt.ask("Re-edit?", choices=["y", "n"], default="y") == "y":
                return None
            text_for_editor = (
                f"# VALIDATION ERROR — fix the YAML below and save.\n"
                f"# {str(e).splitlines()[0]}\n#\n" + clean_text
            )


if __name__ == "__main__":
    app()
