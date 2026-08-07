"""Nonce discipline (rule 18): cryptographically random, secret until the audit."""

from __future__ import annotations

import re
import secrets

_NONCE_RE = re.compile(r"^[0-9a-f]{32}$")


def new_nonce() -> str:
    """A fresh 32-lowercase-hex nonce (128 bits) — ``secrets``, never ``random``."""
    return secrets.token_hex(16)


def is_valid_nonce(value: object) -> bool:
    """True for exactly the wire format: 32 lowercase hex chars."""
    return isinstance(value, str) and bool(_NONCE_RE.match(value))
