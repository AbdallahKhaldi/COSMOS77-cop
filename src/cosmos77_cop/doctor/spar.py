"""Handshake stage: one clearly-labeled friendly greeting, every SPAR-Nxx code mapped.

A refusal IS valuable output — the kit sparring peer refuses-with-explanations by design — so a
SPAR code anywhere in the response or the transport error renders as a diagnosis (the
PARTNER-LEAGUE-GUIDE troubleshooting meanings), never as a crash.
"""

from __future__ import annotations

import re
from typing import Any

from .report import GREEN, RED, YELLOW, Stage, skipped
from .stages import Caller

SPAR_DIAGNOSES = {
    "SPAR-N00": "their side read our greeting as a non-object — transport/serialization fault",
    "SPAR-N01": "greeting carried no `terms` — wire-shape fault on the SENDER's side "
    "(a bookletter-shaped greeting under a reference wire)",
    "SPAR-N02": "terms incomplete against the closed 14-key set — extract the flat signed terms",
    "SPAR-N03": "constitutions differ — re-agree config values and compare canonical strings",
    "SPAR-N04": "terms match but the signature does not — a serialization bug "
    "(check ensure_ascii=False and compact separators; see the forensics stage)",
    "SPAR-N05": "locked-model mismatch — both sides declared and the hashes differ; agree one "
    "model (we can switch scent via `serve --scent-model`)",
    "SPAR-N06": "sub-game index mismatch — restart the side that ran ahead",
    "SPAR-N07": "role collision (both declared the same side) — restart exactly one side "
    "with the other role",
    "SPAR-N08": "no group_id anywhere in the greeting — no game_id can be derived",
    "SPAR-N09": "handshake budget exhausted — our counterpart never greeted back",
    "SPAR-N10": "game_uid mismatch — their uid was derived from a WIDER input than the flat "
    "14 signed terms",
}


def handshake_stage(url: str | None, caller: Caller, greeting: dict[str, Any]) -> Stage:
    """Stage 4: send ONE friendly greeting; capture the response or the refusal code."""
    if url is None:
        return skipped("handshake", "no opponent URL given")
    data: dict[str, Any] | None = None
    try:
        raw = caller(url, greeting)
        got = getattr(raw, "data", None)
        data = got if isinstance(got, dict) else None
        text = _describe(raw)
        refused = _spar_code(text)
    except Exception as exc:
        text, refused = str(exc), _spar_code(str(exc))
        if refused is None:
            return Stage("handshake", RED, f"negotiate call failed: {text}",
                         fix_line="confirm the endpoint accepts tools/call for `negotiate` "
                         "with a `message` object argument", detail={"error": text[:800]})
    if refused:
        diagnosis = SPAR_DIAGNOSES.get(refused, "unmapped refusal code")
        return Stage("handshake", YELLOW,
                     f"peer refused with {refused}: {diagnosis} (a refusal IS valuable output)",
                     fix_line=f"{refused}: {diagnosis}",
                     detail={"refusal": refused, "response": text[:800]})
    detail: dict[str, Any] = {"response": text[:800]}
    if data is not None:
        detail["data"] = data
    return Stage("handshake", GREEN,
                 "greeting acknowledged (reference shape returns ok:true immediately; any "
                 "refusal travels back as a ControlMessage, not a return value)", detail=detail)


def _describe(raw: object) -> str:
    data = getattr(raw, "data", None)
    content = getattr(raw, "content", None)
    return repr(data if data is not None else (content if content is not None else raw))


def _spar_code(text: str) -> str | None:
    found = re.search(r"SPAR-N\d\d", text)
    return found.group(0) if found else None
