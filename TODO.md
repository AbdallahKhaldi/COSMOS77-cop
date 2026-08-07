# TODO.md — living checklist (COSMOS77-cop)

Working list per phase; checked items stay as the development story (rule 50). Cross-repo items
are mirrored in `../COSMOS77-thief/TODO.md`.

## Done

- [x] Phase 0 (2026-08-07): workspace + kit clone verified (113/113 vectors, 6/6 selfplay), both
      repos scaffolded (uv/py3.12, §3 skeleton, seed tests 100% cov, ruff strict), 3-agent
      bootstrap audit clean, pushed to GitHub, Tasneem invited as collaborator.
- [x] Phase 1 (2026-08-07): PRD-1…7 + PLAN.md + this file, role-adapted in both repos.
- [x] Phase 2 (2026-08-07): `config/game.json` constitution + rule-12 loader (FIXED/MINIMUM),
      `engine/` board/rules/capture/subgame — 55 tests incl. rule-47 brute-force sweep, 99% cov.

## Phase 3 — strategy (next)

- [ ] Read HW6 `strategy/pursuit.py`; port retrograde technique (orthogonal + enlarged capture set).
- [ ] `solver.py` <100 ms; empty-board ∞ check; trap conversion check.
- [ ] `tracker.py` exact argmax + degraded Bayesian; role brain per PRD-3 acceptance list
      (cop: two-regime barrier planner, reserve 2; thief: max-survival, distance-1 taboo,
      rule-47 self-check + concession).

## Phase 4 — protocol

- [ ] Vendor `protocol/` (canonical/sealing/terms/ids/scent/outcome/consensus) + `crypto/`.
- [ ] Copy kit vectors into `tests/vectors/`; conformance replay for every fixture.
- [ ] `scripts/sync_protocol.py` + identity test (byte-equal trees in both repos).

## Phase 5 — net

- [ ] Four MCP tools (`message`×3 + `payload` for submit_audit), validate→enqueue→`{"ok": True}`.
- [ ] Receiver contract decision table; handshake refusals N00–N10; state machine + deadline +
      watchdog; fault-injection ledger byte-equality; `make smoke` real.
- [ ] Re-point `make kill` port at `config/peer.toml` once it exists (audit note from Phase 0).

## Phase 6 — hints/scent · Phase 7 — series/artifacts · Phase 8 — sparring exam

- [ ] Per PRD-4 / PRD-7 acceptance lists; sparring gate: 4 role/model combos, `--hint-lang mixed`,
      `--turn-timeout 30`, tracker offset 0 vs audit-revealed trail; freeze capture-rate regression.

## Phase 9–12 — GUI/replay · Gmail/Gatekeeper · deploy · console · README/tag

- [ ] Per PRD-5/PRD-7; screenshots (incl. one DEGRADED/fuzzy heatmap + captioned exact-mode shot);
      `docs/DECISIONS.md` ADRs (App-F#5 commit-mail reading, friendly-report recipients, SHA-256
      "signatures", rate-limits location); docx from TEAM.env.md (self-score 90, bonus No).

## Phase 13 — league (per opponent)

- [ ] Outreach → constitution → F1 → F2 → F3 → counted confirmation (commits exchanged, truthful
      counts) → armed run → settle → BOTH reports → artifacts committed → ledger +1 → de-arm →
      archive.

## Standing items (every phase)

- [ ] Mirror into thief repo; alternate commit authors; no AI trailers; push branch + main.
- [ ] ruff zero / cov ≥85% / ≤150 lines per file / no secrets tracked.

## Human-input queue (blocked on Abdallah/Tasneem)

- [ ] `agent_gmail` in TEAM.env.md (needed by Phase 10 OAuth + Moodle form).
- [ ] Gemini API key into `.env` both repos (needed for LIVE hints only — tests stay mocked).
- [ ] Gmail Cloud project + `credentials.json` (Phase 10); Render services + env vars (Phase 11);
      cloudflared install (Phase 11).
