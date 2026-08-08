"""``serve``/``selfplay`` wiring: arming refusals, counted artifacts, event-sink plumbing."""

import dataclasses
from types import SimpleNamespace
from unittest.mock import patch

from cosmos77_cop.commands_play import serve_cmd
from cosmos77_cop.commands_selfplay import selfplay_cmd
from cosmos77_cop.gui.stream import EventSink
from cosmos77_cop.orchestrator.peerconf import PeerConfig


def fake_report():
    return SimpleNamespace(
        result="capture", reason="capture", sub_game_number=1,
        settlement=SimpleNamespace(settled=True),
    )


def run_serve(tmp_path, calls, **kwargs):
    report = fake_report()

    def fake_driver(**driver_kwargs):
        calls["driver"] = driver_kwargs
        return SimpleNamespace(
            mcp=object(), client=SimpleNamespace(close=lambda: None),
            play_window=lambda w: report, reports=[report],
            gateway_for=lambda w: SimpleNamespace(identity={}), peer_identity=None,
        )

    with (
        patch("cosmos77_cop.commands_play.SeriesDriver", side_effect=fake_driver),
        patch(
            "cosmos77_cop.commands_play.start_server",
            return_value=SimpleNamespace(should_exit=False),
        ) as server,
        patch("cosmos77_cop.commands_play.finish_series", return_value={"settled": True}),
        patch("cosmos77_cop.commands_play.declared_count", return_value=3),
    ):
        rc = serve_cmd(
            port=8801, peer_url="http://127.0.0.1:8802/mcp", gid_a="cosmos77", gid_b="zulu",
            windows=1, out=str(tmp_path / "out"), **kwargs,
        )
    calls["server"] = server
    return rc


def test_half_armed_serve_hard_refuses_before_binding_a_port(tmp_path, capsys):
    calls = {}
    armed_cfg = dataclasses.replace(PeerConfig(), league_counted=True)
    with (
        patch("cosmos77_cop.commands_play.load_peer_config", return_value=armed_cfg),
        patch("cosmos77_cop.arming.has_credentials", return_value=True),
    ):
        assert run_serve(tmp_path, calls) == 2
    assert "REFUSED" in capsys.readouterr().out
    assert "driver" not in calls and not calls["server"].called
    calls = {}
    with (
        patch("cosmos77_cop.commands_play.load_peer_config", return_value=PeerConfig()),
        patch("cosmos77_cop.arming.has_credentials", return_value=True),
    ):
        assert run_serve(tmp_path, calls, counted=True) == 2
    assert "half-armed" in capsys.readouterr().out


def test_fully_armed_serve_writes_a_counted_artifact_set(tmp_path):
    calls = {}
    armed_cfg = dataclasses.replace(PeerConfig(), league_counted=True)
    with (
        patch("cosmos77_cop.commands_play.load_peer_config", return_value=armed_cfg),
        patch("cosmos77_cop.arming.has_credentials", return_value=True),
    ):
        assert run_serve(tmp_path, calls, counted=True) == 0
    writer = calls["driver"]["writer"]
    assert writer.league["counted"] is True and writer.league["reason"] == "counted"
    assert calls["driver"]["num_games_declared"] == 3


def test_friendly_serve_stays_exactly_disarmed_but_declares_truthfully(tmp_path):
    calls = {}
    with patch("cosmos77_cop.commands_play.load_peer_config", return_value=PeerConfig()):
        assert run_serve(tmp_path, calls) == 0
    writer = calls["driver"]["writer"]
    assert writer.league["counted"] is False and writer.league["reason"] == "friendly"
    assert calls["driver"]["num_games_declared"] == 3


def test_events_flag_wires_the_sink_with_no_gui(tmp_path):
    calls = {}
    with patch("cosmos77_cop.commands_play.load_peer_config", return_value=PeerConfig()):
        assert run_serve(tmp_path, calls, events=True) == 0
    attachment = calls["driver"]["view_attachment"]
    assert attachment is not None and attachment.window is None
    assert isinstance(attachment.extra, EventSink)
    assert attachment.extra.path.parent == tmp_path / "out"
    calls = {}
    with patch("cosmos77_cop.commands_play.load_peer_config", return_value=PeerConfig()):
        assert run_serve(tmp_path, calls) == 0
    assert calls["driver"]["view_attachment"] is None


def run_selfplay(tmp_path, **kwargs):
    with (
        patch("cosmos77_cop.commands_selfplay.subprocess.Popen") as popen,
        patch("cosmos77_cop.commands_selfplay.serve_cmd", return_value=0) as serve,
    ):
        popen.return_value.wait.return_value = 0
        rc = selfplay_cmd(out=str(tmp_path / "run"), windows=1, **kwargs)
    return rc, popen.call_args.args[0], serve.call_args.kwargs


def test_selfplay_forwards_events_to_both_processes(tmp_path):
    rc, argv, serve_kwargs = run_selfplay(tmp_path, events=True)
    assert rc == 0
    assert "--events" in argv and serve_kwargs["events"] is True


def test_selfplay_defaults_leave_events_off(tmp_path):
    rc, argv, serve_kwargs = run_selfplay(tmp_path)
    assert rc == 0
    assert "--events" not in argv and serve_kwargs["events"] is False
