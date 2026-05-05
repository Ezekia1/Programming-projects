import logging
import os
from pathlib import Path

import anthropic
import typer
from dotenv import find_dotenv, load_dotenv
from rich.console import Console

from .analyze import PROMPT_VERSION, SYSTEM_PROMPT, _build_user_message, analyze
from .extract import extract_text
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
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
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

    console.rule(note.title)
    console.print(f"[dim]subject:[/dim] {note.subject}")
    console.print(f"[dim]tags:[/dim] {', '.join(note.tags)}")
    console.print(f"\n{note.summary}\n")
    for kp in note.key_points:
        console.print(f"  • {kp.text}")
    console.rule()

    if not yes and not typer.confirm("Save this note?", default=True):
        raise typer.Abort()

    out = write_note(note, vault, source=str(path.resolve()), prompt_version=PROMPT_VERSION)
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


if __name__ == "__main__":
    app()
