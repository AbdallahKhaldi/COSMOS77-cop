"""Reach + contract stages: warmup/probe semantics and the four-tool contract, no sockets."""

from fastmcp import Client

from cosmos77_cop.doctor.stages import EXPECTED_TOOLS, contract_stage, reach_stage
from cosmos77_cop.net.client import PeerClient
from cosmos77_cop.net.probes import classify_status
from cosmos77_cop.net.server import PeerInbox, build_server


def prober_for(table):
    def prober(url):
        code = table[url]
        if code is None:
            return None, "unreachable: ConnectTimeout"
        return code, classify_status(code)
    return prober


def test_reach_406_both_roles_is_green_ready():
    urls = {"cop_role": "https://a/mcp", "thief_role": "https://b/mcp"}
    stage = reach_stage(urls, prober_for({"https://a/mcp": 406, "https://b/mcp": 406}))
    assert stage.status == "green"
    assert stage.fix_line is None
    assert [r["classification"] for r in stage.detail["probes"]] == ["ready", "ready"]


def test_reach_400_is_yellow_server_no_session():
    stage = reach_stage({"single": "https://x/mcp"}, prober_for({"https://x/mcp": 400}))
    assert stage.status == "yellow"
    assert "server-no-session" in stage.fix_line


def test_reach_redirect_502_200_timeout_are_red_with_fixes():
    table = {"a": 302, "b": 502, "c": 200, "d": None, "e": 421}
    for url, needle in [
        ("a", "no redirects"), ("b", "no agent behind"), ("c", "/mcp path"),
        ("d", "unreachable"), ("e", "Host header"),
    ]:
        stage = reach_stage({"single": url}, prober_for(table))
        assert stage.status == "red", url
        assert needle in stage.fix_line, url


def test_reach_skips_without_urls():
    stage = reach_stage({}, prober_for({}))
    assert stage.status == "green" and "skipped" in stage.finding


def _real_lister(url):
    """Our own reference server through the real held-session machinery — in-memory."""
    server = build_server(PeerInbox(), "probe-target")
    client = PeerClient(url, transport_factory=lambda: Client(server))
    try:
        tools = client.session(lambda c: c.list_tools(), deadline_s=10)
        return [
            (t.name, sorted((t.inputSchema or {}).get("properties") or {})) for t in tools
        ]
    finally:
        client.close()


def test_contract_green_against_our_own_reference_server():
    stage = contract_stage({"single": "inmemory://peer"}, _real_lister)
    assert stage.status == "green"
    assert "all four reference tools" in stage.finding
    tools = stage.detail["endpoints"][0]["tools"]
    assert {t: [p] for t, p in EXPECTED_TOOLS.items()} == tools


def test_contract_missing_tool_is_red_with_add_fix():
    def lister(url):
        return [("negotiate", ["message"]), ("receive_turn", ["message"]),
                ("receive_control", ["message"])]
    stage = contract_stage({"single": "u"}, lister)
    assert stage.status == "red"
    assert "missing tool `submit_audit`" in stage.finding
    assert "add tool `submit_audit(payload: dict)`" in stage.fix_line


def test_contract_wrong_param_name_is_red_with_rename_fix():
    def lister(url):
        return [("negotiate", ["msg"]), ("receive_turn", ["message"]),
                ("receive_control", ["message"]), ("submit_audit", ["payload"])]
    stage = contract_stage({"single": "u"}, lister)
    assert stage.status == "red"
    assert "`negotiate` takes (msg) not `message`" in stage.finding
    assert "rename `negotiate`'s parameter to `message`" in stage.fix_line


def test_contract_session_failure_is_red_and_names_transport():
    def lister(url):
        raise RuntimeError("All connection attempts failed")
    stage = contract_stage({"cop_role": "u1", "thief_role": "u2"}, lister)
    assert stage.status == "red"
    assert "could not open an MCP session" in stage.fix_line
    assert stage.detail["endpoints"][0]["error"] == "All connection attempts failed"


def test_contract_extra_tools_are_noted_not_flagged():
    def lister(url):
        return [(t, [p]) for t, p in EXPECTED_TOOLS.items()] + [("ping", [])]
    stage = contract_stage({"single": "u"}, lister)
    assert stage.status == "green"
    assert stage.detail["endpoints"][0]["extra_tools"] == ["ping"]
