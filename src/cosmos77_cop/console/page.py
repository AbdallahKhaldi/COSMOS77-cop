"""Loads the console page from its HTML asset (kept out of Python so it stays editable)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def page_html() -> str:
    """The console's single page."""
    return (Path(__file__).parent / "page.html").read_text(encoding="utf-8")
