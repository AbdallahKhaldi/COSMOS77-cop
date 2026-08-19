"""CLI wiring + end-to-end probe run (all seams faked) + the friendly-greeting posture."""

import json
from pathlib import Path
from types import SimpleNamespace

from cosmos77_cop import commands
from cosmos77_cop.cli import main
from cosmos77_cop.commands_doctor import build_probe_greeting, doctor_probe_cmd
from cosmos77_cop.net.probes import classify_status
from cosmos77_cop.protocol.terms import terms_from_config, terms_signature

RAW = json.loads(Path("config/game.json").read_text(encoding="utf-8"))


def test_bare_doctor_still_runs_the_local_health_check(monkeypatch):
    called = []
    monkeypatch.setattr(commands, "doctor_cmd", lambda: called.append(True) or 0)
    assert main(["doctor"]) == 0
    assert called == [True]


def test_usage_errors_exit_2(capsys):
    assert main(["doctor", "--url", "https://a/mcp", "--cop-url", "https://b/mcp"]) == 2
    assert main(["doctor", "--cop-url", "https://b/mcp"]) == 2
    assert main(["doctor", "--json"]) == 2
    assert "doctor:" in capsys.readouterr().out


def test_greeting_is_friendly_labeled_truthful_and_signed():
    greeting = build_probe_greeting(RAW, "best2934")
    assert "DIAGNOSTIC PROBE" in greeting["identity"]["note"]
    assert "counted" not in greeting
    assert isinstance(greeting["identity"]["counted_games_played"], int)
    assert greeting["terms"] == terms_from_config(RAW)
    assert terms_signature(greeting["terms"], greeting["nonce"]) == greeting["signature"]
    assert greeting["game_uid"]
    assert "game_uid" not in build_probe_greeting(RAW, None)
    assert greeting["scent_model_sha256"] and greeting["wire_shape_sha256"]


def full_run(capsys, **kwargs):
    base = dict(
        url=None, cop_url=None, thief_url=None, their_config=None, their_gid=None,
        their_greeting=None, public_base="https://arena.example",
    )
    code = doctor_probe_cmd(**{**base, **kwargs})
    out = capsys.readouterr().out.strip()
    return code, json.loads(out)


def test_full_probe_run_is_one_json_line_exit_zero_even_when_red(capsys):
    code, report = full_run(
        capsys,
        cop_url="https://x/cop/mcp", thief_url="https://x/thief/mcp",
        prober=lambda url: (502, classify_status(502)),
        lister=lambda url: [(t, ["message"]) for t in ("negotiate",)],
        caller=lambda url, g: SimpleNamespace(data={"ok": True}),
    )
    assert code == 0
    assert set(report["stages"]) == {
        "reach", "contract", "locks", "handshake", "uid", "forensics", "topology"
    }
    assert report["summary"]["status"] == "red"
    assert report["stages"]["reach"]["status"] == "red"
    # bare {"ok": true} is honestly YELLOW since the MOAAMOHA mute-peer windows
    assert report["stages"]["handshake"]["status"] == "yellow"
    assert report["target"]["mode"] == "per-role"
    assert report["summary"]["next_actions"][0].startswith("[reach]")


def test_offline_run_skips_network_stages_and_diffs_config(capsys, tmp_path):
    theirs = tmp_path / "theirs.json"
    theirs.write_text(json.dumps(RAW), encoding="utf-8")

    def explode(*a):
        raise AssertionError("network seam called in offline mode")

    code, report = full_run(
        capsys, their_config=str(theirs), their_gid="best2934",
        prober=explode, lister=explode, caller=explode,
    )
    assert code == 0
    assert "skipped" in report["stages"]["reach"]["finding"]
    assert "skipped" in report["stages"]["handshake"]["finding"]
    assert report["stages"]["uid"]["status"] == "green"
    assert report["summary"]["status"] == "green"
    assert report["target"]["mode"] == "offline"


def test_their_greeting_file_feeds_locks_and_forensics(capsys, tmp_path):
    terms = terms_from_config(RAW)
    greeting = {
        "terms": terms, "nonce": "ab" * 16,
        "signature": terms_signature(terms, "ab" * 16),
        "scent_model_sha256": "cd" * 32,
    }
    sample = tmp_path / "greeting.json"
    sample.write_text(json.dumps(greeting), encoding="utf-8")
    code, report = full_run(capsys, their_greeting=str(sample))
    assert code == 0
    assert report["stages"]["locks"]["status"] == "red"  # unknown scent hash
    assert report["stages"]["forensics"]["status"] == "green"  # signature verifies


def test_unreadable_inputs_are_usage_errors(capsys, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    arr = tmp_path / "arr.json"
    arr.write_text("[1]", encoding="utf-8")
    base = dict(url="https://a/mcp", cop_url=None, thief_url=None, their_config=None,
                their_gid=None, their_greeting=None, public_base="https://a")
    assert doctor_probe_cmd(**{**base, "their_greeting": str(bad)}) == 2
    assert doctor_probe_cmd(**{**base, "config_path": str(tmp_path / "absent.json")}) == 2
    assert doctor_probe_cmd(**{**base, "config_path": str(arr)}) == 2
    assert doctor_probe_cmd(**{**base, "config_path": None}) == 2
    assert "doctor:" in capsys.readouterr().out


def test_real_network_seams_run_over_inmemory_transport(monkeypatch):
    from fastmcp import Client

    import cosmos77_cop.commands_doctor as cd
    from cosmos77_cop.net.client import PeerClient
    from cosmos77_cop.net.server import PeerInbox, build_server

    server = build_server(PeerInbox(), "probe-target")
    monkeypatch.setattr(
        cd, "PeerClient",
        lambda url: PeerClient(url, transport_factory=lambda: Client(server)),
    )
    tools = dict(cd._list_tools("http://in.memory/mcp", 10.0))
    assert tools["submit_audit"] == ["payload"] and tools["negotiate"] == ["message"]
    result = cd._call_negotiate("http://in.memory/mcp", {"terms": {}}, 10.0)
    assert result.data == {"ok": True}


def test_cli_end_to_end_with_mocked_probe(monkeypatch, capsys):
    import cosmos77_cop.commands_doctor as cd
    monkeypatch.setattr(cd, "probe", lambda url: (406, classify_status(406)))
    monkeypatch.setattr(cd, "_list_tools", lambda url, d: [
        ("negotiate", ["message"]), ("receive_turn", ["message"]),
        ("receive_control", ["message"]), ("submit_audit", ["payload"]),
    ])
    monkeypatch.setattr(
        cd, "_call_negotiate", lambda url, g, d: SimpleNamespace(data={"ok": True})
    )
    assert main(["doctor", "--json", "--url", "https://one.example/mcp"]) == 0
    report = json.loads(capsys.readouterr().out.strip())
    # a bare-ok peer is YELLOW overall now: a probe cannot tell push-dialect from mute
    assert report["summary"]["status"] == "yellow"
    assert report["target"]["mode"] == "single-endpoint-both-roles"
    assert report["stages"]["topology"]["detail"]["their_shape"] == "single-endpoint-both-roles"
