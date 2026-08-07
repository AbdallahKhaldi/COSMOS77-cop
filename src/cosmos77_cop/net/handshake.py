"""Greeting construction + peer verification with the kit's refusal codes (SPEC §7).

Validation order and diagnoses follow ``sparring/negotiate.py::verify_peer`` — N01 (terms absent,
a wire-shape fault on the SENDER) is a different diagnosis from N03 (terms differ, a constitution
disagreement). N06/N07 are bystander-class: refuse on the record and keep waiting. Omission never
refuses, anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..protocol.canonical import canonical_str
from ..protocol.locks import lock_conflicts
from ..protocol.pairing import REFUSE_UID, pairing_decision, uid_decision
from ..protocol.terms import terms_signature, validate_terms


@dataclass(frozen=True)
class Verdict:
    """The handshake decision for one inbound greeting."""

    ok: bool
    code: str | None = None
    detail: str = ""
    bystander: bool = False


def build_greeting(
    *,
    terms: dict[str, Any],
    nonce: str,
    group_id: str,
    role: str,
    sub_game_number: int,
    identity: dict[str, Any],
    locks: dict[str, str],
    game_uid: str | None,
) -> dict[str, Any]:
    """Our negotiate message: signed terms + pairing + locks + uid (None fields dropped)."""
    greeting: dict[str, Any] = {
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        "group_id": group_id,
        "role": role,
        "sub_game_number": sub_game_number,
        "identity": identity,
        "game_uid": game_uid,
    }
    for family, digest in locks.items():
        greeting[f"{family}_sha256"] = digest
    return {k: v for k, v in greeting.items() if v is not None}


def verify_peer(
    *,
    ours: dict[str, Any],
    theirs: object,
    our_uid: str | None,
) -> Verdict:
    """Validate an inbound greeting against our own, in the kit's order (SPAR-N00..N10)."""
    if not isinstance(theirs, dict):
        return Verdict(False, "SPAR-N00", f"greeting is {type(theirs).__name__}, not an object")
    if "terms" not in theirs:
        keys = sorted(theirs)
        return Verdict(False, "SPAR-N01", f"no terms key — sender wire-shape fault; got {keys}")
    their_terms = theirs["terms"]
    if not isinstance(their_terms, dict) or validate_terms(their_terms):
        missing = validate_terms(their_terms) if isinstance(their_terms, dict) else ["<not a dict>"]
        return Verdict(False, "SPAR-N02", f"opponent terms incomplete; missing {missing}")
    if their_terms != ours["terms"]:
        diff = [
            f"{k}: ours={ours['terms'].get(k)!r} theirs={their_terms.get(k)!r}"
            for k in ours["terms"]
            if their_terms.get(k) != ours["terms"].get(k)
        ]
        detail = (
            f"terms differ: {diff}; ours={canonical_str(ours['terms'])} "
            f"theirs={canonical_str(their_terms)}"
        )
        return Verdict(False, "SPAR-N03", detail)
    nonce, signature = theirs.get("nonce"), theirs.get("signature")
    if not nonce or not signature or terms_signature(their_terms, str(nonce)) != signature:
        return Verdict(
            False,
            "SPAR-N04",
            "terms matched, so the difference is serialization — check ensure_ascii=False "
            "and compact separators",
        )
    conflicts = lock_conflicts(_locks_of(ours), _locks_of(theirs))
    if conflicts:
        return Verdict(False, "SPAR-N05", f"locked-model mismatch on {conflicts}")
    pairing = pairing_decision(ours, theirs)
    if pairing == "refuse:sub_game":
        return Verdict(False, "SPAR-N06", "one game cannot carry two indices", bystander=True)
    if pairing == "refuse:role":
        return Verdict(False, "SPAR-N07", "two of the same side can only deadlock", bystander=True)
    identity = theirs.get("identity") or {}
    if not (theirs.get("group_id") or identity.get("group_id")):
        return Verdict(False, "SPAR-N08", "no group_id anywhere — no game_id can be derived")
    if uid_decision(our_uid, theirs.get("game_uid")) == REFUSE_UID:
        return Verdict(
            False,
            "SPAR-N10",
            "uid mismatch — their derive step likely consumed a WIDER input than the flat terms",
        )
    return Verdict(True)


def _locks_of(greeting: dict[str, Any]) -> dict[str, object]:
    return {
        family: greeting.get(f"{family}_sha256")
        for family in ("scent_model", "wire_shape", "info_mode", "smell_binding")
    }


def peer_group_id(theirs: dict[str, Any]) -> str:
    """The opponent's group id from a verified greeting (top-level wins over identity)."""
    identity = theirs.get("identity") or {}
    return str(theirs.get("group_id") or identity.get("group_id"))
