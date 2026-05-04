from pathlib import Path

import typer
from rich.console import Console

from .analyze import analyze
from .extract import extract_text
from .vault import existing_tags, write_note

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
) -> None:
    """Extract a structured note from a reading and save it to the vault."""
    console.print(f"[dim]Reading[/dim] {path}")
    text = extract_text(path)
    console.print(f"[dim]Extracted[/dim] {len(text):,} characters")

    tags = existing_tags(vault)
    console.print(f"[dim]Existing tags:[/dim] {len(tags)}")

    console.print("[dim]Analyzing…[/dim]")
    note = analyze(text, tags)

    console.rule(note.title)
    console.print(f"[dim]subject:[/dim] {note.subject}")
    console.print(f"[dim]tags:[/dim] {', '.join(note.tags)}")
    console.print(f"\n{note.summary}\n")
    for kp in note.key_points:
        console.print(f"  • {kp.text}")
    console.rule()

    if not yes and not typer.confirm("Save this note?", default=True):
        raise typer.Abort()

    out = write_note(note, vault, source=str(path.resolve()))
    console.print(f"[green]Saved[/green] {out}")


if __name__ == "__main__":
    app()
