"""MIME assembly for the one email a counted series owes (rules 33-34).

Rule 33 wants JSON; rule 34 forbids free text and wants an attached JSON file. We over-satisfy
both: the body IS the exact canonical bytes that were hashed, and the identical bytes ride as the
single named attachment. Pretty-printing the body is what nearly zeroed a team in ex06 — so the
bytes are never re-serialized here, only carried.
"""

from __future__ import annotations

import base64
from email.message import EmailMessage
from pathlib import Path

SUBJECT_PREFIX = "[cosmos77] final_game_result"


class BodyMismatchError(RuntimeError):
    """The body and the attachment are not the same bytes — refuse to send."""


def subject_for(game_id: str) -> str:
    """The subject line for a counted series report."""
    return f"{SUBJECT_PREFIX} {game_id}"


def build_message(
    *,
    sender: str,
    recipients: tuple[str, ...],
    game_id: str,
    canonical: bytes,
    filename: str,
) -> EmailMessage:
    """Assemble the report email; the body and attachment carry identical bytes."""
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject_for(game_id)
    message.set_content(canonical.decode("utf-8"))
    message.add_attachment(
        canonical, maintype="application", subtype="json", filename=filename
    )
    verify_message(message, canonical)
    return message


def body_bytes(message: EmailMessage) -> bytes:
    """The bytes actually carried in the text body."""
    body = message.get_body(preferencelist=("plain",))
    return body.get_content().encode("utf-8").rstrip(b"\n")


def attachment_bytes(message: EmailMessage) -> bytes:
    """The bytes actually carried in the single attachment."""
    for part in message.iter_attachments():
        return part.get_content()
    raise BodyMismatchError("the report has no attachment")


def verify_message(message: EmailMessage, canonical: bytes) -> None:
    """Refuse a message whose body and attachment are not the hashed bytes."""
    expected = canonical.rstrip(b"\n")
    if body_bytes(message) != expected:
        raise BodyMismatchError("body is not the exact canonical bytes that were hashed")
    if attachment_bytes(message).rstrip(b"\n") != expected:
        raise BodyMismatchError("attachment is not the exact canonical bytes that were hashed")


def encode_for_api(message: EmailMessage) -> dict[str, str]:
    """The Gmail ``users.messages.send`` request body."""
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")}


def load_result_bytes(path: str | Path) -> tuple[bytes, str]:
    """Read a result artifact as raw bytes plus its filename (never re-serialize it)."""
    target = Path(path)
    return target.read_bytes(), target.name
