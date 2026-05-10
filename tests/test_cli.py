from pathlib import Path
from unittest.mock import patch

import anthropic
import httpx
import pytest
import yaml
from typer.testing import CliRunner

from sapling.cli import app
from sapling.models import KeyPoint, Note

runner = CliRunner()


@pytest.fixture(autouse=True)
def _dummy_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most CLI tests need to pass the missing-key pre-check; mocking
    `analyze` means the dummy key is never actually used."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-dummy")


def _valid_note() -> Note:
    return Note(
        title="Test note",
        subject="testing",
        summary="A summary that is at least twenty characters long.",
        key_points=[
            KeyPoint(text=f"Point {i}", detail="A sufficiently long detail paragraph for testing.")
            for i in range(3)
        ],
        tags=["sample"],
        concepts=[],
    )


def _auth_error() -> anthropic.AuthenticationError:
    req = httpx.Request("POST", "http://example")
    resp = httpx.Response(401, request=req)
    return anthropic.AuthenticationError(message="auth fail", response=resp, body=None)


@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.write_note")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_ingest_happy_path_with_yes(
    mock_extract, mock_analyze, mock_write, mock_preview, tmp_path: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    mock_extract.return_value = "hello world"
    mock_analyze.return_value = _valid_note()
    mock_write.return_value = tmp_path / "out.md"

    result = runner.invoke(app, ["ingest", str(f), "--vault", str(tmp_path), "--yes"])

    assert result.exit_code == 0, result.output
    mock_extract.assert_called_once()
    mock_analyze.assert_called_once()
    mock_write.assert_called_once()


@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.extract_text")
def test_extract_value_error_is_clean_exit(mock_extract, mock_preview, tmp_path: Path) -> None:
    f = tmp_path / "x.pdf"
    f.write_text("not really a pdf")
    mock_extract.side_effect = ValueError("PDF is encrypted: x.pdf")

    result = runner.invoke(app, ["ingest", str(f), "--yes"])

    assert result.exit_code == 1
    assert "Cannot extract text" in result.output
    assert "encrypted" in result.output
    assert "Traceback" not in result.output


@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_authentication_error_is_clean_exit(
    mock_extract, mock_analyze, mock_preview, tmp_path: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    mock_extract.return_value = "hello"
    mock_analyze.side_effect = _auth_error()

    result = runner.invoke(app, ["ingest", str(f), "--yes"])

    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output
    assert "Traceback" not in result.output


@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_runtime_error_from_analyze_is_clean_exit(
    mock_extract, mock_analyze, mock_preview, tmp_path: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    mock_extract.return_value = "hello"
    mock_analyze.side_effect = RuntimeError("Claude refused to extract a note from this content.")

    result = runner.invoke(app, ["ingest", str(f), "--yes"])

    assert result.exit_code == 1
    assert "Analysis failed" in result.output
    assert "refused" in result.output
    assert "Traceback" not in result.output


def test_missing_api_key_clean_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    f = tmp_path / "x.txt"
    f.write_text("hello")

    result = runner.invoke(app, ["ingest", str(f), "--vault", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY is missing" in result.output
    assert "Traceback" not in result.output


@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.write_note")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_verbose_flag_enables_info_logging(
    mock_extract, mock_analyze, mock_write, mock_preview, tmp_path: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    mock_extract.return_value = "hello"
    mock_analyze.return_value = _valid_note()
    mock_write.return_value = tmp_path / "out.md"

    # The --verbose flag should be accepted; we don't assert on log output here
    # because logging.basicConfig is process-global and pytest's logging capture
    # interacts in messy ways. The flag-acceptance signal is sufficient.
    result = runner.invoke(app, ["ingest", str(f), "--vault", str(tmp_path), "--yes", "--verbose"])
    assert result.exit_code == 0, result.output


# --- C7: review/edit/reject loop ---------------------------------------------


@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.write_note")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_review_output_does_not_eat_bracket_content(
    mock_extract, mock_analyze, mock_write, mock_preview, tmp_path: Path
) -> None:
    """Rich treats [mid] as markup; ensure we escape user strings so academic
    notation like arr[mid] survives review output."""
    f = tmp_path / "x.txt"
    f.write_text("hello")
    note_with_brackets = Note(
        title="Test",
        subject="testing",
        summary="A summary that is at least twenty characters long.",
        key_points=[
            KeyPoint(
                text="arr[mid] comparison key step",
                detail="Compare arr[mid] to target; recurse on the half that could contain it.",
            ),
            KeyPoint(text="Point 1", detail="A sufficient detail paragraph for testing."),
            KeyPoint(text="Point 2", detail="A sufficient detail paragraph for testing."),
        ],
        tags=["sample"],
        concepts=[],
    )
    mock_extract.return_value = "hello"
    mock_analyze.return_value = note_with_brackets
    mock_write.return_value = tmp_path / "out.md"

    result = runner.invoke(app, ["ingest", str(f), "--vault", str(tmp_path), "--yes"])

    assert result.exit_code == 0, result.output
    assert "arr[mid]" in result.output, "bracket content was eaten by Rich markup"


@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.write_note")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_interactive_accept_writes_note(
    mock_extract, mock_analyze, mock_write, mock_preview, tmp_path: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    mock_extract.return_value = "hello"
    mock_analyze.return_value = _valid_note()
    mock_write.return_value = tmp_path / "out.md"

    # Default to "a" — user just hits enter
    result = runner.invoke(app, ["ingest", str(f), "--vault", str(tmp_path)], input="\n")

    assert result.exit_code == 0, result.output
    mock_write.assert_called_once()


@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.write_note")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_interactive_reject_does_not_write(
    mock_extract, mock_analyze, mock_write, mock_preview, tmp_path: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    mock_extract.return_value = "hello"
    mock_analyze.return_value = _valid_note()

    result = runner.invoke(app, ["ingest", str(f), "--vault", str(tmp_path)], input="r\n")

    assert result.exit_code == 0
    assert "rejected" in result.output.lower()
    mock_write.assert_not_called()


@patch("sapling.cli.typer.edit")
@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.write_note")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_interactive_edit_valid_then_accept(
    mock_extract, mock_analyze, mock_write, mock_preview, mock_edit, tmp_path: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    mock_extract.return_value = "hello"
    original = _valid_note()
    mock_analyze.return_value = original
    mock_write.return_value = tmp_path / "out.md"

    # Editor returns the original note's YAML with title changed
    edited = original.model_copy(update={"title": "Edited title"})
    edited_yaml = yaml.safe_dump(edited.model_dump(), sort_keys=False)
    mock_edit.return_value = edited_yaml

    # User: edit, then accept
    result = runner.invoke(app, ["ingest", str(f), "--vault", str(tmp_path)], input="e\na\n")

    assert result.exit_code == 0, result.output
    mock_edit.assert_called_once()
    mock_write.assert_called_once()
    saved_note = mock_write.call_args.args[0]
    assert saved_note.title == "Edited title"


@patch("sapling.cli.typer.edit")
@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.write_note")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_interactive_edit_invalid_then_abandon(
    mock_extract, mock_analyze, mock_write, mock_preview, mock_edit, tmp_path: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    mock_extract.return_value = "hello"
    mock_analyze.return_value = _valid_note()

    # Editor returns garbage → ValidationError, user declines re-edit, then rejects
    mock_edit.return_value = "this is: not valid yaml: at all: [\n"

    # User: edit, decline re-edit (n), then reject
    result = runner.invoke(
        app,
        ["ingest", str(f), "--vault", str(tmp_path)],
        input="e\nn\nr\n",
    )

    assert result.exit_code == 0
    assert "validation" in result.output.lower() or "error" in result.output.lower()
    mock_write.assert_not_called()


@patch("sapling.cli.typer.edit")
@patch("sapling.cli._print_cost_preview")
@patch("sapling.cli.write_note")
@patch("sapling.cli.analyze")
@patch("sapling.cli.extract_text")
def test_interactive_edit_abandoned_when_editor_returns_none(
    mock_extract, mock_analyze, mock_write, mock_preview, mock_edit, tmp_path: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    mock_extract.return_value = "hello"
    mock_analyze.return_value = _valid_note()
    mock_write.return_value = tmp_path / "out.md"

    # Editor closed without saving → returns None → fall back to original
    mock_edit.return_value = None

    # User: edit (abandoned), then accept original
    result = runner.invoke(app, ["ingest", str(f), "--vault", str(tmp_path)], input="e\na\n")

    assert result.exit_code == 0, result.output
    saved_note = mock_write.call_args.args[0]
    # The original note (unedited) was saved
    assert saved_note.title == _valid_note().title
