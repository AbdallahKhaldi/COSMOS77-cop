"""Outgoing-hint lint: hard 15-word cap, zero digits (rule 27 — never a coordinates protocol)."""

from __future__ import annotations

import re

_DIGIT = re.compile(r"\d")


def truncate_words(text: str, max_words: int) -> str:
    """Hard-cap *text* at *max_words* words."""
    words = text.split()
    return " ".join(words[:max_words])


def is_coordinate_free(text: str) -> bool:
    """True when nothing in *text* could read as a coordinate (we ban all digits outright)."""
    return not _DIGIT.search(text)


def enforce(text: str, *, max_words: int, fallback: str) -> str:
    """Truncate, then replace with *fallback* if any digit survives or nothing is left."""
    cut = truncate_words(text.strip(), max_words)
    if not cut or not is_coordinate_free(cut):
        return truncate_words(fallback, max_words)
    return cut
