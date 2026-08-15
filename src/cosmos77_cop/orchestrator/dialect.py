"""Negotiate dialect tolerance (kit WARNINGS 2b — two live stalls, one per direction).

``negotiate`` can be built as a PUSH (call theirs, discard the reply, wait for their call)
or as REQUEST/RESPONSE (read the agreement out of the reply).  Each is conformant; a pair
of them is mutually mute with healthy logs on both sides.  The kit's defence is symmetric
and this module is both halves of ours: READ any greeting a reply carries, and ANSWER our
own calls' repliers by carrying our greeting back (wired via ``build_server``'s provider).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..crypto.nonce import new_nonce

if TYPE_CHECKING:  # circular-import guard: gateway imports net, net never imports us
    from .gateway import Gateway


def greeting_from_reply(gateway: Gateway, reply: object) -> bool:
    """Accept a greeting carried in the negotiate RESPONSE body, when one is there.

    Only a reply that VERIFIES as a greeting counts; anything else (our own peers answer
    ``{"ok": true}``) is ignored, never refused — loud refusals stay with the push path,
    so a plain-ok peer is never mistaken for a bad one.
    """
    data = getattr(reply, "data", None)
    if not isinstance(data, dict):
        return False
    candidate = data.get("message") if isinstance(data.get("message"), dict) else data
    if "terms" not in candidate:
        return False
    verdict = gateway.verify(candidate)
    if verdict.ok:
        gateway.peer_greeting = candidate
        return True
    return False


def gateway_greeting(gateway: Gateway | None) -> dict[str, Any] | None:
    """A fresh-nonce greeting for the CURRENT window, or None between windows."""
    return gateway.greeting(new_nonce()) if gateway is not None else None
