from unittest.mock import MagicMock, patch

import pytest

from sapling.analyze import PROMPT_VERSION, SYSTEM_PROMPT, analyze
from sapling.models import KeyPoint, Note


def _valid_note(**overrides) -> Note:
    base = dict(
        title="Sample title",
        subject="testing",
        summary="A summary that is at least twenty characters long.",
        key_points=[
            KeyPoint(text=f"Point {i}", detail="A sufficiently long detail paragraph for testing.")
            for i in range(3)
        ],
        tags=["sample"],
        concepts=[],
    )
    base.update(overrides)
    return Note(**base)


def _mock_anthropic(parsed=None, stop_reason="end_turn"):
    client = MagicMock()
    response = MagicMock()
    response.parsed_output = parsed if parsed is not None else _valid_note()
    response.stop_reason = stop_reason
    client.messages.parse.return_value = response
    return client


@patch("sapling.analyze.anthropic.Anthropic")
def test_returns_note(mock_cls):
    mock_cls.return_value = _mock_anthropic()
    note = analyze("text", ["existing-tag"])
    assert isinstance(note, Note)


@patch("sapling.analyze.anthropic.Anthropic")
def test_passes_text_and_tags_in_user_message(mock_cls):
    client = _mock_anthropic()
    mock_cls.return_value = client
    analyze("THE READING TEXT", ["tag-one", "tag-two"])
    user_msg = client.messages.parse.call_args.kwargs["messages"][0]["content"]
    assert "THE READING TEXT" in user_msg
    assert "tag-one" in user_msg
    assert "tag-two" in user_msg
    assert "EXISTING TAG VOCABULARY" in user_msg


@patch("sapling.analyze.anthropic.Anthropic")
def test_handles_empty_existing_tags(mock_cls):
    client = _mock_anthropic()
    mock_cls.return_value = client
    analyze("text", [])
    user_msg = client.messages.parse.call_args.kwargs["messages"][0]["content"]
    assert "NO EXISTING TAGS" in user_msg


@patch("sapling.analyze.anthropic.Anthropic")
def test_uses_opus_47_by_default(mock_cls):
    client = _mock_anthropic()
    mock_cls.return_value = client
    analyze("text", [])
    assert client.messages.parse.call_args.kwargs["model"] == "claude-opus-4-7"


@patch("sapling.analyze.anthropic.Anthropic")
def test_uses_adaptive_thinking_and_high_effort(mock_cls):
    client = _mock_anthropic()
    mock_cls.return_value = client
    analyze("text", [])
    kwargs = client.messages.parse.call_args.kwargs
    assert kwargs["thinking"] == {"type": "adaptive"}
    assert kwargs["output_config"] == {"effort": "high"}


@patch("sapling.analyze.anthropic.Anthropic")
def test_raises_with_refusal_message_on_refusal(mock_cls):
    client = _mock_anthropic(stop_reason="refusal")
    client.messages.parse.return_value.parsed_output = None
    mock_cls.return_value = client
    with pytest.raises(RuntimeError, match="refused"):
        analyze("text", [])


@patch("sapling.analyze.anthropic.Anthropic")
def test_raises_on_none_parsed_non_refusal(mock_cls):
    client = _mock_anthropic(stop_reason="max_tokens")
    client.messages.parse.return_value.parsed_output = None
    mock_cls.return_value = client
    with pytest.raises(RuntimeError, match="max_tokens"):
        analyze("text", [])


def test_prompt_version_is_set():
    assert PROMPT_VERSION


def test_system_prompt_includes_quality_bar_and_anti_patterns():
    assert "QUALITY BAR" in SYSTEM_PROMPT
    assert "ANTI-PATTERNS" in SYSTEM_PROMPT
