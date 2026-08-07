"""Warm-up polling (406 is ready) and the Render service definition."""

import sys
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from warmup import warm  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@patch("warmup.probe")
def test_warm_exits_zero_only_on_406(mock_probe, capsys):
    clock = FakeClock()
    mock_probe.side_effect = [(502, "edge-up-nothing-behind"), (406, "ready")]
    assert warm("http://x/mcp", budget_s=60, interval_s=5, clock=clock, sleep=clock.sleep) == 0
    assert "READY" in capsys.readouterr().out


@patch("warmup.probe")
def test_warm_never_reports_success_on_a_200(mock_probe, capsys):
    clock = FakeClock()
    mock_probe.return_value = (200, "unexpected-200")
    assert warm("http://x/mcp", budget_s=20, interval_s=5, clock=clock, sleep=clock.sleep) == 1
    assert "never became ready" in capsys.readouterr().out


@patch("warmup.probe")
def test_warm_gives_up_within_its_budget(mock_probe):
    clock = FakeClock()
    mock_probe.return_value = (None, "unreachable: ConnectError")
    assert warm("http://x/mcp", budget_s=30, interval_s=10, clock=clock, sleep=clock.sleep) == 1
    assert clock.now >= 30


def test_render_definition_carries_the_load_bearing_settings():
    text = (REPO / "deploy" / "render.yaml").read_text(encoding="utf-8")
    assert "pip install -e ." in text, "a plain install orphans config/"
    assert 'healthCheckPath: ""' in text, "an MCP server has no GET /"
    assert "net.asgi:app" in text
    assert "PYTHON_VERSION" in text and "GEMINI_API_KEY" in text


def test_deploy_runbook_documents_the_status_codes():
    text = (REPO / "docs" / "DEPLOY.md").read_text(encoding="utf-8")
    for token in ("406", "421", "502", "httpHostHeader", "loopback", "T-protocol"):
        assert token in text
