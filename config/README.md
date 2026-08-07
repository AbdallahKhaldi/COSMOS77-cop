# config/

Zero hardcoded tunables: every knob the code reads comes from files in this directory
(playbook §0.14).

- `game.json` — the shared pairing constitution (the flat 14 signed terms + extended blocks such
  as `movement_and_barriers` and `rate_limiter_gatekeeper`). Lands in Phase 2 with the engine that
  reads it; per-game crypto-locked copies are committed as `config_<game_id>_g<NN>.json` under
  `artifacts/`.
- `peer.toml` — PRIVATE per-machine runtime config (our ports, opponent URLs, strategy class,
  trash-talk provider, email arming). Gitignored; a `peer.example.toml` template ships in Phase 5.
