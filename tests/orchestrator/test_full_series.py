"""Full in-memory series: our SeriesDriver (police) vs a scripted solver-evader thief.

Two gateways cross-wired through in-memory clients (zero sockets); the stub opponent runs the
SHARED thief loop machinery with a test-local brain, so both halves of the protocol are real.
"""

import json
import threading
import types
from pathlib import Path

from cosmos77_cop.crypto.nonce import new_nonce
from cosmos77_cop.crypto.step0 import build_step0
from cosmos77_cop.engine.config import from_dict
from cosmos77_cop.engine.rules import token_between
from cosmos77_cop.net.server import KIND_AUDIT, KIND_CONTROL, KIND_NEGOTIATE, KIND_TURN, PeerInbox
from cosmos77_cop.orchestrator.gateway import Gateway
from cosmos77_cop.orchestrator.peerconf import PeerConfig
from cosmos77_cop.orchestrator.series import SeriesDriver, window_groups
from cosmos77_cop.orchestrator.turnloop import play_sub_game
from cosmos77_cop.orchestrator.turnstate import SideKit, fresh_state
from cosmos77_cop.protocol.sealing import commit
from cosmos77_cop.report.artifacts import ArtifactWriter
from cosmos77_cop.report.compare import compare_results
from cosmos77_cop.report.finish import finish_series
from cosmos77_cop.strategy import solver

REPO = Path(__file__).resolve().parents[2]
KIND = {
    "negotiate": KIND_NEGOTIATE,
    "receive_turn": KIND_TURN,
    "receive_control": KIND_CONTROL,
    "submit_audit": KIND_AUDIT,
}


class InMemoryClient:
    def __init__(self, target: PeerInbox):
        self.target = target

    def call(self, tool, args, *, deadline_s):
        self.target.push(KIND[tool], args.get("message") or args.get("payload"))
        return {"ok": True}

    def close(self):
        return None


class EvaderBridge:
    def decide(self, state, kit):
        cell, confidence = kit.tracker.estimate()
        if confidence == "exact" and cell is not None and state.board.in_bounds(cell):
            dest, _ = solver.best_thief_move(state.board, cell, state.my_pos)
            return types.SimpleNamespace(kind="move", move_token=token_between(state.my_pos, dest))
        return types.SimpleNamespace(kind="move", move_token="STAY")


def game_cfg():
    raw = json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8"))
    return from_dict(raw), raw


def sealed_step0(window, gid):
    payload = build_step0(
        sub_game_number=window,
        group_name=gid,
        model="template",
        code_version="b" * 40,
        num_games_declared=None,
        spec={"os": "test"},
    )
    nonce = new_nonce()
    return {"payload": payload, "nonce": nonce, "commit": commit(payload, nonce)}


def stub_thief_series(cfg, peer_cfg, inbox, client, windows, gid_a, gid_b):
    for window in range(1, windows + 1):
        police_gid, thief_gid = window_groups(window, gid_a, gid_b)
        gateway = Gateway(
            game_cfg=cfg,
            peer_cfg=peer_cfg,
            role="thief",
            group_id=thief_gid,
            group_name=thief_gid,
            sub_game_number=window,
            opponent_group_id=police_gid,
            client=client,
            inbox=inbox,
        )
        state = fresh_state(cfg, "thief")
        kit = SideKit.fresh(cfg, "thief", seed=2000 + window)
        play_sub_game(gateway, state, kit, EvaderBridge(), sealed_step0(window, thief_gid))


def test_two_window_series_settles_with_clean_audits(tmp_path):
    solver.clear_cache()
    cfg, raw = game_cfg()
    fast = {"turn_timeout_s": 15.0, "watchdog_s": 30.0, "handshake_budget_s": 15.0}
    gid_a, gid_b = "cosmos77", "cosmos77-mirror"
    driver = SeriesDriver(
        game_cfg=cfg,
        peer_cfg=PeerConfig(**fast),
        gid_a=gid_a,
        gid_b=gid_b,
        out_dir=tmp_path / "ours",
        code_version="a" * 40,
        hardware={"os": "test"},
    )
    writer = ArtifactWriter(
        tmp_path / "ours", gid=driver.gid, uid="uid-x", github={}, counted=False, reason="friendly"
    )
    driver.writer = writer
    stub_inbox = PeerInbox()
    driver.client = InMemoryClient(stub_inbox)
    stub_client = InMemoryClient(driver.inbox)
    thread = threading.Thread(
        target=stub_thief_series,
        args=(cfg, PeerConfig(**fast), stub_inbox, stub_client, 2, gid_a, gid_b),
        daemon=True,
    )
    thread.start()
    first = driver.play_window(1)
    second = driver.play_window(2)
    thread.join(timeout=60)
    for report in (first, second):
        assert report.result in ("capture", "survival"), report.reason
        assert report.settlement is not None and report.settlement.settled
        assert report.settlement.log_verified and not report.settlement.tampered
        assert report.my_audit is not None and report.my_audit.clean
    assert (tmp_path / "ours" / f"log_{driver.gid}_g01.json").exists()
    summary = finish_series(
        driver,
        writer,
        raw_cfg=raw,
        my_gid=gid_a,
        my_identity={"group_name": gid_a, "members": [], "repos": {}, "mcp_servers": {}},
        peer_identity=driver.peer_identity,
        expected_windows=2,
    )
    assert summary["settled"]
    result_path = tmp_path / "ours" / f"result_{driver.gid}.json"
    assert result_path.exists()
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["mutual_agreement"]["sha256"]
    assert compare_results(result, result) == []
    scores = {tuple(sorted(r["score"].values())) for r in result["sub_games"]}
    assert scores <= {(5, 20), (5, 10)}
    # Rule 49: the peer's gid maps to the repos THEY declared in their greeting — never
    # invented for them. The stub greets with this repo's identity constants.
    from cosmos77_cop.orchestrator.identity import TEAM_REPOS

    assert result["links"]["github"] == {"cosmos77-mirror": dict(TEAM_REPOS)}


def test_seed_github_never_claims_our_repos_for_a_real_opponent():
    from cosmos77_cop.commands_play import seed_github
    from cosmos77_cop.orchestrator.identity import TEAM_REPOS

    assert seed_github("cosmos77", "rival", selfplay=False) == {"cosmos77": dict(TEAM_REPOS)}
    both = seed_github("cosmos77", "cosmos77-mirror", selfplay=True)
    assert set(both) == {"cosmos77", "cosmos77-mirror"}
