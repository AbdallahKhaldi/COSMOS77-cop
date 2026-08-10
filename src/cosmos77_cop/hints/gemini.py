"""Gemini bluff author (rule 25: text only, never moves) with token metering (rule 54).

Any failure of any kind — missing key, import error, timeout, quota, malformed reply — returns
``None`` and the zero-token template layer takes over. Live calls never happen in tests.
"""

from __future__ import annotations

import os
from pathlib import Path

_SYSTEM = (
    "You write ONE short in-character taunt for a pursuit game set in {arena}. "
    "Persona: the {persona}. The line must be under {max_words} words, natural language, "
    "no numbers of any kind, no coordinates, no quotes. Intent: {intent_note}."
)
#: The endpoint REFUSES a shorter deadline outright — ``400 INVALID_ARGUMENT: Manually set
#: deadline Ns is too short. Minimum allowed deadline is 10s.`` A shorter value does not make the
#: call fast, it makes every call fail into the template fallback, silently and forever. Any
#: configured timeout is clamped up to this floor rather than quietly disabling the whole feature.
API_MIN_TIMEOUT_S = 10.0

_PERSONA = {"police": "confident street cop", "thief": "slippery night thief"}
_INTENT_NOTE = {
    "truth": "an honest, unrevealing remark",
    "lie": "misdirection — imply a part of town you are NOT in",
}


def load_env_key(env_path: str | Path = ".env") -> str | None:
    """GEMINI_API_KEY from the process env or a local (gitignored) .env file."""
    if key := os.environ.get("GEMINI_API_KEY"):
        return key
    path = Path(env_path)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            name, _, value = line.strip().partition("=")
            if name == "GEMINI_API_KEY" and value:
                return value.strip().strip('"')
    return None


class HintMeter:
    """Token usage for ONE sub-game, plus what the series spent before it (rule 54).

    ``SideKit.fresh`` builds a new meter per sub-game (the fresh-runtime rule), so this object's
    own totals are per-sub-game — hence the name. ``carried`` is the series spend that precedes
    it, and ``series_total`` is the only figure the negotiated budget may be measured against.
    """

    def __init__(self, carried: int = 0) -> None:
        """Zeroed counters, seeded with the series spend preceding this sub-game."""
        self.per_sub_game: dict[int, int] = {}
        self.total_sub_game = 0
        self.carried = carried

    def add(self, sub_game: int, tokens: int) -> None:
        """Record *tokens* consumed while playing *sub_game*."""
        self.per_sub_game[sub_game] = self.per_sub_game.get(sub_game, 0) + tokens
        self.total_sub_game += tokens

    @property
    def series_total(self) -> int:
        """Everything this series has spent, this sub-game included."""
        return self.carried + self.total_sub_game


class GeminiHinter:
    """One configured Gemini client; ``hint()`` never raises."""

    def __init__(
        self, api_key: str | None, model: str, meter: HintMeter, timeout_s: float = 12.0
    ) -> None:
        """Store config; the client is built lazily on first use."""
        self.api_key = api_key
        self.model = model
        self.meter = meter
        self.timeout_s = max(float(timeout_s), API_MIN_TIMEOUT_S)
        self._client: object | None = None

    def _get_client(self) -> object | None:
        if self._client is None and self.api_key:
            from google import genai

            self._client = genai.Client(
                api_key=self.api_key,
                http_options={"timeout": int(self.timeout_s * 1000)},
            )
        return self._client

    def hint(
        self, *, role: str, arena: str, intent: str, sub_game: int, max_words: int = 15
    ) -> str | None:
        """One generated line, or ``None`` on ANY failure (the caller falls back)."""
        try:
            client = self._get_client()
            if client is None:
                return None
            prompt = _SYSTEM.format(
                arena=arena,
                persona=_PERSONA.get(role, "player"),
                intent_note=_INTENT_NOTE.get(intent, "an unrevealing remark"),
                max_words=max_words,
            )
            response = client.models.generate_content(model=self.model, contents=prompt)
            usage = getattr(response, "usage_metadata", None)
            if usage is not None:
                self.meter.add(sub_game, int(getattr(usage, "total_token_count", 0) or 0))
            text = getattr(response, "text", None)
            return str(text).strip() if text else None
        except Exception:
            return None
