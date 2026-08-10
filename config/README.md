# config/

Zero hardcoded tunables: every knob the code reads comes from files in this directory
(playbook §0.14).

- `game.json` — the shared pairing constitution (the flat 14 signed terms + extended blocks such
  as `movement_and_barriers` and `rate_limiter_gatekeeper`). Lands in Phase 2 with the engine that
  reads it; per-game crypto-locked copies are committed as `config_<game_id>_g<NN>.json` under
  `artifacts/`.
- `peer.toml` — PRIVATE per-machine runtime config (our ports, opponent URLs, `[strategy]`
  overlay, trash-talk provider, email arming). Gitignored, so copy `peer.example.toml` onto every
  machine that plays: without it `[league] counted` can never be true and `serve --counted` can
  only refuse "half-armed".

Resolution order, tightest last — **dataclass default < environment variable < `peer.toml` <
the signed `game.json`** (`orchestrator/peerlayers.py`). A deployed image clones from GitHub and
so has no `peer.toml`; there `COSMOS_TRASH_PROVIDER`, `COSMOS_TRASH_MODEL` and
`COSMOS_LEAGUE_COUNTED` stand in for it. The signed file then wins on the three parallel keys
both teams agreed (`response_timeout_sec`, `watchdog_timeout_sec`, `queue_depth`) — a negotiated
deadline is the opponent's entitlement, not our preference.
