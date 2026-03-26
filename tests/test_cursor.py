import pytest
from fastapi_cursor.cursor import CursorToken, CursorState


def test_encode_decode_roundtrip():
    token = CursorToken(secret="test-secret")
    cursor_id = "abc-123-def"
    encoded = token.encode(cursor_id)
    decoded = token.decode(encoded)
    assert decoded == cursor_id


def test_tampered_token_raises():
    token = CursorToken(secret="test-secret")
    encoded = token.encode("my-cursor-id")
    # Corrupt the last few chars
    tampered = encoded[:-5] + "XXXXX"
    with pytest.raises(ValueError):
        token.decode(tampered)


def test_wrong_secret_raises():
    token_a = CursorToken(secret="secret-a")
    token_b = CursorToken(secret="secret-b")
    encoded = token_a.encode("my-cursor-id")
    with pytest.raises(ValueError):
        token_b.decode(encoded)


def test_garbage_token_raises():
    token = CursorToken(secret="test-secret")
    with pytest.raises(ValueError):
        token.decode("not-a-real-token!!!")


def test_different_ids_produce_different_tokens():
    token = CursorToken(secret="s")
    assert token.encode("id-1") != token.encode("id-2")


def test_cursor_state_roundtrip():
    state = CursorState(column="id", value=42, direction="asc", page_size=10)
    restored = CursorState.from_dict(state.to_dict())
    assert restored.column == "id"
    assert restored.value == 42
    assert restored.direction == "asc"
    assert restored.page_size == 10


def test_cursor_state_defaults():
    state = CursorState.from_dict({"column": "id", "value": 1})
    assert state.direction == "asc"
    assert state.page_size == 20
