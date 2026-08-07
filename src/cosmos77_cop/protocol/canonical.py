"""The one canonical serialization under every hash (kit SPEC §2; rule 17's byte layer).

``ensure_ascii=False`` is the single most important fact in the protocol: Hebrew and emoji stay
raw UTF-8. Keys sort by Unicode code point; floats are Python shortest round-trip repr; digests
are lowercase hex. The report consensus signature (``consensus.py``) is the ONE construction that
uses different (spaced) separators.
"""

from __future__ import annotations

import hashlib
import json


def canonical_str(obj: object) -> str:
    """Serialize *obj* to the compact canonical form."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def canonical_bytes(obj: object) -> bytes:
    """UTF-8 bytes of the canonical form — exactly what gets hashed and what gets emailed."""
    return canonical_str(obj).encode("utf-8")


def canonical_hash(obj: object) -> str:
    """Lowercase-hex SHA-256 of the canonical bytes."""
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()
