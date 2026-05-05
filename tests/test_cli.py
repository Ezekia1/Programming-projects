from pathlib import Path
from unittest.mock import patch

import anthropic
import httpx
import pytest
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
