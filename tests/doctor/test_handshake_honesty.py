"""The handshake stage tells 'answered' apart from 'greeted' (the MOAAMOHA lesson).

Two live windows died behind a green light: the peer answered {"ok": true} to every
negotiate and never transmitted a greeting by any path. Green now requires the reply
to CARRY a greeting; a bare acknowledgment is YELLOW with the one question to ask.
"""

from __future__ import annotations

from types import SimpleNamespace

from cosmos77_cop.doctor.spar import handshake_stage

GREETING = {"terms": {"grid_size": 7}, "signature": "ab", "group_id": "probe"}


def _caller(reply):
    return lambda url, greeting: SimpleNamespace(data=reply)


def test_bare_ok_is_yellow_not_green():
    stage = handshake_stage("https://x/mcp", _caller({"ok": True}), GREETING)
    assert stage.status == "yellow"
    assert "NOT returned" in stage.finding


def test_reply_carrying_a_greeting_is_green():
    theirs = {"terms": {"grid_size": 7}, "signature": "cd", "group_id": "MOAAMOHA"}
    stage = handshake_stage("https://x/mcp", _caller({"ok": True, "message": theirs}), GREETING)
    assert stage.status == "green"
    assert stage.detail["their_greeting_gid"] == "MOAAMOHA"
