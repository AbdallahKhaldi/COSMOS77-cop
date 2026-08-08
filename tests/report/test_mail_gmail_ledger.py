"""MIME byte-fidelity (rules 33-34), the mocked send path (rule 30), and the rule-52 ledger."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from cosmos77_cop.protocol.canonical import canonical_bytes
from cosmos77_cop.report.gatekeeper import Gatekeeper, SendRefusedError
from cosmos77_cop.report.gmail import SCOPES, has_credentials, send_report
from cosmos77_cop.report.ledger import MAX_GAMES, Ledger, LedgerError
from cosmos77_cop.report.mail import (
    BodyMismatchError,
    attachment_bytes,
    body_bytes,
    build_message,
    encode_for_api,
    load_result_bytes,
    subject_for,
)

REPORT = {"game_id": "a-vs-b", "hint": "אני ליד הכיכר 🙂", "score": {"a": 20, "b": 5}}


def message_for(canonical: bytes):
    return build_message(
        sender="agent@example.com",
        recipients=("someone@example.com",),
        game_id="a-vs-b",
        canonical=canonical,
        filename="result_a-vs-b.json",
    )


def test_body_and_attachment_are_the_exact_hashed_bytes():
    canonical = canonical_bytes(REPORT)
    message = message_for(canonical)
    assert body_bytes(message) == canonical
    assert attachment_bytes(message).rstrip(b"\n") == canonical
    assert message["Subject"] == subject_for("a-vs-b")
    assert "🙂" in body_bytes(message).decode("utf-8")


def test_a_pretty_printed_body_is_refused():
    canonical = canonical_bytes(REPORT)
    pretty = json.dumps(REPORT, indent=2, ensure_ascii=False).encode("utf-8")
    message = message_for(canonical)
    with pytest.raises(BodyMismatchError, match="body is not the exact canonical bytes"):
        from cosmos77_cop.report.mail import verify_message

        verify_message(message, pretty)


def test_trailing_newline_on_disk_still_matches(tmp_path):
    path = tmp_path / "result_a-vs-b.json"
    path.write_bytes(canonical_bytes(REPORT) + b"\n")
    raw, name = load_result_bytes(path)
    assert name == "result_a-vs-b.json"
    message = message_for(raw)
    assert attachment_bytes(message).rstrip(b"\n") == raw.rstrip(b"\n")


def test_api_encoding_is_urlsafe_base64():
    blob = encode_for_api(message_for(canonical_bytes(REPORT)))
    assert set(blob) == {"raw"}
    assert "+" not in blob["raw"] and "/" not in blob["raw"]


def test_scope_is_send_only():
    assert SCOPES == ["https://www.googleapis.com/auth/gmail.send"]
    assert not any("readonly" in s or "modify" in s for s in SCOPES)


def test_has_credentials_is_false_without_a_client_file(tmp_path):
    assert not has_credentials(tmp_path)
    (tmp_path / "credentials.json").write_text("{}", encoding="utf-8")
    assert has_credentials(tmp_path)


def fake_service(side_effects):
    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
        side_effects
    )
    return service


def rate_limited():
    error = Exception("HttpError 429 rate limit")
    error.resp = MagicMock(status=429)
    return error


def test_send_goes_through_the_gatekeeper_and_returns_the_response():
    service = fake_service([{"id": "m1"}])
    keeper = Gatekeeper()
    slept = []
    response = send_report(
        service=service, gatekeeper=keeper, sender="me", recipients=("x@example.com",),
        game_id="a-vs-b", canonical=canonical_bytes(REPORT), filename="r.json",
        clock=lambda: 0.0, sleep=slept.append,
    )
    assert response == {"id": "m1"}
    assert slept == []
    assert keeper.sent_today == 1


def test_a_429_backs_off_exponentially_then_succeeds():
    service = fake_service([rate_limited(), rate_limited(), {"id": "m2"}])
    slept = []
    response = send_report(
        service=service, gatekeeper=Gatekeeper(), sender="me", recipients=("x@example.com",),
        game_id="a-vs-b", canonical=canonical_bytes(REPORT), filename="r.json",
        max_retries=3, backoff_base=5.0, clock=lambda: 0.0, sleep=slept.append,
    )
    assert response == {"id": "m2"}
    assert slept == [5.0, 10.0]


def test_a_refusing_gatekeeper_blocks_the_send_entirely():
    service = fake_service([{"id": "never"}])
    keeper = Gatekeeper(daily_cap=0)
    with pytest.raises(SendRefusedError, match="quota"):
        send_report(
            service=service, gatekeeper=keeper, sender="me", recipients=("x@example.com",),
            game_id="a-vs-b", canonical=canonical_bytes(REPORT), filename="r.json",
            clock=lambda: 0.0, sleep=lambda _s: None,
        )
    assert not service.users.return_value.messages.return_value.send.called


def test_a_non_429_error_is_raised_not_retried():
    boom = Exception("HttpError 500 server error")
    service = fake_service([boom, {"id": "never"}])
    with pytest.raises(Exception, match="500"):
        send_report(
            service=service, gatekeeper=Gatekeeper(), sender="me", recipients=("x@example.com",),
            game_id="a-vs-b", canonical=canonical_bytes(REPORT), filename="r.json",
            clock=lambda: 0.0, sleep=lambda _s: None,
        )


def test_ledger_records_one_counted_game_per_opponent(tmp_path):
    path = tmp_path / "artifacts" / "league_ledger.json"
    ledger = Ledger.load(path)
    assert ledger.counted_games_played == 0 and not ledger.passes_minimum
    ledger.record(opponent="rival", game_id="cosmos77-vs-rival", game_uid="u", won=True,
                  settled_at="t")
    assert ledger.counted_games_played == 1
    assert not ledger.first_meeting("rival")
    with pytest.raises(LedgerError, match="rule 52"):
        ledger.record(opponent="rival", game_id="again", game_uid="u2", won=True, settled_at="t")
    ledger.record(opponent="other", game_id="cosmos77-vs-other", game_uid="u3", won=False,
                  settled_at="t")
    assert ledger.passes_minimum
    assert Ledger.load(path).counted_games_played == 2


def test_ledger_enforces_the_league_cap(tmp_path):
    ledger = Ledger.load(tmp_path / "l.json")
    for index in range(MAX_GAMES):
        ledger.record(opponent=f"team{index}", game_id="g", game_uid="u", won=False, settled_at="t")
    with pytest.raises(LedgerError, match="rule 31"):
        ledger.record(opponent="overflow", game_id="g", game_uid="u", won=False, settled_at="t")


@patch("cosmos77_cop.report.gmail.build_service")
def test_report_cmd_dry_run_never_touches_gmail(build, tmp_path, capsys):
    from cosmos77_cop.commands import report_cmd

    body = {"game_id": "a-vs-b", "league": {"counted": False}, "mutual_agreement": {"sha256": "x"}}
    path = tmp_path / "result_a-vs-b.json"
    path.write_bytes(canonical_bytes(body) + b"\n")
    assert report_cmd(str(path), counted=False, dry_run=True) == 0
    out = capsys.readouterr().out
    assert "posture=friendly" in out and "DRY RUN" in out
    assert "rmisegal" not in out
    assert not build.called


def test_report_cmd_refuses_a_half_armed_run(tmp_path, capsys):
    from cosmos77_cop.commands import report_cmd

    body = {"game_id": "a-vs-b", "league": {"counted": True}, "mutual_agreement": {"sha256": "x"}}
    path = tmp_path / "result_a-vs-b.json"
    path.write_bytes(canonical_bytes(body) + b"\n")
    assert report_cmd(str(path), counted=False, dry_run=True) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_an_expired_consent_falls_back_to_re_consent_not_a_crash(tmp_path, monkeypatch, capsys):
    """A Testing-mode project expires refresh tokens after ~7 days; that must not crash a
    match-day report — it must re-consent."""
    from google.auth.exceptions import RefreshError

    from cosmos77_cop.report import gmail

    (tmp_path / "credentials.json").write_text("{}", encoding="utf-8")
    (tmp_path / "token.json").write_text("{}", encoding="utf-8")
    dead = MagicMock(valid=False, expired=True, refresh_token="r")
    dead.refresh.side_effect = RefreshError("invalid_grant")
    fresh = MagicMock(valid=True)
    fresh.to_json.return_value = "{}"

    creds_module = MagicMock()
    creds_module.Credentials.from_authorized_user_file.return_value = dead
    flow_module = MagicMock()
    installed = flow_module.InstalledAppFlow.from_client_secrets_file.return_value
    installed.run_local_server.return_value = fresh
    monkeypatch.setitem(sys.modules, "google.oauth2.credentials", creds_module)
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib.flow", flow_module)

    assert gmail.load_credentials(tmp_path) is fresh
    assert "re-consenting" in capsys.readouterr().out
