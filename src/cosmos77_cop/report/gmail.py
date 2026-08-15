"""The send-only Gmail interface (rule 30; App. A) — the only module that touches the network.

Scope is ``gmail.send`` and nothing else: a read scope is a code disqualification, and a
send-only scope cannot create drafts, which is exactly why the arming interlock gates on the
RECIPIENT rather than on draft mode. Every send goes through the Gatekeeper first.
"""

from __future__ import annotations

import time
from pathlib import Path

from .gatekeeper import ALLOW, Gatekeeper, SendRefusedError
from .mail import build_message, encode_for_api

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


class GmailUnavailableError(RuntimeError):
    """No usable credentials on this machine (correct on Render; fatal for a counted run)."""


def has_credentials(root: str | Path = ".") -> bool:
    """True when an OAuth client file is present (the token is created on first consent)."""
    return (Path(root) / CREDENTIALS_FILE).exists()


def token_ready(root: str | Path = ".") -> bool:
    """A refresh-capable send-only token exists (no network; the arming gate's check).

    A counted series owes the league a report; discovering a dead mail rail after the
    sixth settle is the worst possible time (kit pairing playbook, stage 0).  On a
    headless hub there is no browser to re-consent with, so an armed run must refuse
    up front unless the stored token can actually mint a send.
    """
    import json

    try:
        doc = json.loads((Path(root) / TOKEN_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return bool(doc.get("refresh_token")) and SCOPES[0] in (doc.get("scopes") or [])


def load_credentials(root: str | Path = ".") -> object:
    """Load or refresh the send-only OAuth credentials (opens a browser on first run)."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    base = Path(root)
    token_path, client_path = base / TOKEN_FILE, base / CREDENTIALS_FILE
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds and creds.valid:
        return creds
    # A refresh CAN fail permanently: a Cloud project in Testing mode expires refresh tokens
    # after ~7 days, and the failure arrives as invalid_grant. Re-consenting is the fix, so fall
    # through to the browser flow instead of crashing a match-day report.
    refreshed = False
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            refreshed = True
        except RefreshError:
            print("gmail: stored token could not be refreshed (expired consent) — re-consenting")
    if not refreshed:
        if not client_path.exists():
            raise GmailUnavailableError(f"{client_path} is missing (App. A step 4)")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
        creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_service(root: str | Path = ".") -> object:
    """The Gmail API client, authorized for sending only."""
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=load_credentials(root), cache_discovery=False)


def send_report(
    *,
    service: object,
    gatekeeper: Gatekeeper,
    sender: str,
    recipients: tuple[str, ...],
    game_id: str,
    canonical: bytes,
    filename: str,
    max_retries: int = 3,
    backoff_base: float = 5.0,
    clock: object = time.monotonic,
    sleep: object = time.sleep,
) -> dict:
    """Send one report through the Gatekeeper, backing off on 429. Returns the API response."""
    verdict = gatekeeper.admit(clock())
    if verdict != ALLOW:
        raise SendRefusedError(verdict)
    message = build_message(
        sender=sender,
        recipients=recipients,
        game_id=game_id,
        canonical=canonical,
        filename=filename,
    )
    body = encode_for_api(message)
    delays = gatekeeper.backoff_delays(max_retries, backoff_base)
    last_error: Exception | None = None
    for attempt, delay in enumerate([0.0, *delays]):
        if delay:
            sleep(delay)
        try:
            return service.users().messages().send(userId="me", body=body).execute()
        except Exception as exc:
            last_error = exc
            if not _is_rate_limited(exc) or attempt == len(delays):
                raise
            gatekeeper.note_rate_limited()
    raise SendRefusedError(f"send failed after {max_retries} retries: {last_error}")


def _is_rate_limited(exc: Exception) -> bool:
    """True for a Gmail 429 (whatever shape the client library gives it)."""
    status = getattr(getattr(exc, "resp", None), "status", None)
    return status == 429 or "429" in str(exc)
