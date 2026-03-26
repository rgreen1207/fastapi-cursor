from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any


class CursorState:
    """Represents the pagination position stored server-side.

    Attributes:
        column: The column name used for the keyset comparison.
        value: The last seen value of *column* on the current page.
        direction: ``"asc"`` or ``"desc"``.
        page_size: Number of rows per page.
    """

    def __init__(
        self,
        column: str,
        value: Any,
        direction: str = "asc",
        page_size: int = 20,
    ) -> None:
        self.column = column
        self.value = value
        self.direction = direction
        self.page_size = page_size

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "value": self.value,
            "direction": self.direction,
            "page_size": self.page_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CursorState":
        return cls(
            column=data["column"],
            value=data["value"],
            direction=data.get("direction", "asc"),
            page_size=data.get("page_size", 20),
        )


class CursorToken:
    """Encodes/decodes HMAC-SHA256-signed, base64url-encoded cursor tokens.

    The token embeds a ``cursor_id`` (UUID) that maps to a
    :class:`CursorState` in the store. Clients cannot forge or tamper with
    tokens — the signature covers the entire payload.
    """

    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def _sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    def encode(self, cursor_id: str) -> str:
        """Return a signed base64url token for *cursor_id*."""
        payload = json.dumps({"id": cursor_id}, separators=(",", ":"))
        sig = self._sign(payload)
        envelope = json.dumps({"p": payload, "s": sig}, separators=(",", ":"))
        return base64.urlsafe_b64encode(envelope.encode()).decode().rstrip("=")

    def decode(self, token: str) -> str:
        """Verify the token and return the embedded ``cursor_id``.

        Raises:
            ValueError: If the token is malformed or the signature is wrong.
        """
        padding = 4 - len(token) % 4
        if padding != 4:
            token += "=" * padding
        try:
            envelope = json.loads(base64.urlsafe_b64decode(token).decode())
            payload: str = envelope["p"]
            sig: str = envelope["s"]
        except Exception as exc:
            raise ValueError("Invalid cursor token format") from exc

        expected = self._sign(payload)
        if not hmac.compare_digest(sig, expected):
            raise ValueError("Cursor token signature mismatch")

        return json.loads(payload)["id"]
