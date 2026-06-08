"""Tests for _sanitize_all_tool_ids defensive pass."""

from nanobot.providers.anthropic_provider import _sanitize_all_tool_ids, _VALID_ID_RE


def test_valid_ids_unchanged():
    """IDs that already match the pattern should not be modified."""
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "toolu_abc123", "name": "grep", "input": {}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "toolu_abc123", "content": "ok"},
            ],
        },
    ]
    result = _sanitize_all_tool_ids(msgs)
    assert result[0]["content"][0]["id"] == "toolu_abc123"
    assert result[1]["content"][0]["tool_use_id"] == "toolu_abc123"


def test_pipe_in_tool_use_id_sanitized():
    """Pipe characters from OpenAI Responses IDs should be replaced."""
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "call_abc|item_xyz", "name": "grep", "input": {}},
            ],
        },
    ]
    result = _sanitize_all_tool_ids(msgs)
    sanitized_id = result[0]["content"][0]["id"]
    assert _VALID_ID_RE.match(sanitized_id)
    assert "|" not in sanitized_id


def test_pipe_in_tool_result_id_sanitized():
    """Pipe characters in tool_result IDs should be replaced."""
    msgs = [
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_abc|item_xyz", "content": "ok"},
            ],
        },
    ]
    result = _sanitize_all_tool_ids(msgs)
    sanitized_id = result[0]["content"][0]["tool_use_id"]
    assert _VALID_ID_RE.match(sanitized_id)
    assert "|" not in sanitized_id


def test_dots_in_id_sanitized():
    """Dots in IDs should be replaced."""
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "call.abc.123", "name": "test", "input": {}},
            ],
        },
    ]
    result = _sanitize_all_tool_ids(msgs)
    sanitized_id = result[0]["content"][0]["id"]
    assert _VALID_ID_RE.match(sanitized_id)
    assert "." not in sanitized_id


def test_text_blocks_untouched():
    """Non-tool blocks should pass through unchanged."""
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "hello"},
                {"type": "tool_use", "id": "valid_id", "name": "test", "input": {}},
            ],
        },
    ]
    result = _sanitize_all_tool_ids(msgs)
    assert result[0]["content"][0] == {"type": "text", "text": "hello"}
    assert result[0]["content"][1]["id"] == "valid_id"


def test_string_content_untouched():
    """Messages with string content should pass through unchanged."""
    msgs = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},
    ]
    result = _sanitize_all_tool_ids(msgs)
    assert result[0]["content"] == "hello"
    assert result[1]["content"] == "world"


def test_empty_id_gets_generated():
    """Empty IDs should get a fresh generated ID."""
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "", "name": "test", "input": {}},
            ],
        },
    ]
    result = _sanitize_all_tool_ids(msgs)
    sanitized_id = result[0]["content"][0]["id"]
    assert _VALID_ID_RE.match(sanitized_id)
    assert len(sanitized_id) > 0


def test_multiple_invalid_ids_all_sanitized():
    """All invalid IDs across multiple messages should be sanitized."""
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "id.with.dots", "name": "a", "input": {}},
                {"type": "tool_use", "id": "id|with|pipes", "name": "b", "input": {}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "id.with.dots", "content": "ok"},
                {"type": "tool_result", "tool_use_id": "id|with|pipes", "content": "ok"},
            ],
        },
    ]
    result = _sanitize_all_tool_ids(msgs)
    for block in result[0]["content"]:
        assert _VALID_ID_RE.match(block["id"]), f"Invalid ID: {block['id']}"
    for block in result[1]["content"]:
        assert _VALID_ID_RE.match(block["tool_use_id"]), f"Invalid ID: {block['tool_use_id']}"
