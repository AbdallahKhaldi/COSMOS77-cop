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

- [x] Phase 3 (2026-08-07): retrograde solver ported from HW6 (orthogonal, barrier configs,
      enlarged rule-46 capture set, boxed terminals; <100 ms, memoized); tracker exact argmax
      inversion + fuzzy fallback; belief map; role brains (cop: two-regime barrier planner with
      reserve + budget guards; thief: max-survival + taboo + rule-47 concession). 87/86 tests.

- [x] Phase 4 (2026-08-07): vendored `protocol/` (canonical, sealing, terms, ids, both scent
      models, outcome, consensus, locks, pairing) + `crypto/` (nonce, step0, 4-layer audit,
      corroboration, settlement); ALL applicable kit vectors replay green in both repos
      (canonical/commit/divergent-forms/terms/uid/pheromone/consensus/locks/declarations/book-scent);
      `sync_protocol.py` trees byte-identical. 158 tests, 92% cov.

- [x] Phase 5 (2026-08-07): four MCP tools (ok:true, message/payload asymmetry), receiver
      contract green vs the delivery_contract vector, handshake N00-N10 with bystander semantics,
      state machine + one-clock deadline + watchdog, PeerClient (held session, reopen-once, hard
      deadlines), probes (406=ready), peer.toml loader with budget reconciliation, and a REAL
      two-process `make smoke`: handshake + one committed turn each way. 214/213 tests.
- [ ] Phase 5 leftover: point `make kill` at `config/peer.toml` port (audit note from Phase 0) —
      fold into Phase 7 CLI `kill`.

- [x] Phase 6 (2026-08-07): ScentFlow (deposit-then-decay trail whose wire argmax is always the
      emitter cell, min-center gating, receiver-side decay, {} for the book model); hint chain
      (seeded bluff policy -> Gemini per cadence -> templates -> lint), 15-word cap, digit-free,
      truthful intents, HintMeter per sub-game/series; liar-score calibration. 231/230 tests.

- [x] Phase 7 (2026-08-07): live turn loop (thief-first, claims/concessions/win-claims,
      message-driven endings), six-window SeriesDriver (role-label alternation, fresh runtimes,
      greeting-preserving drains, re-greeting handshakes), 4-layer audit exchange + settlement,
      counted-format artifacts (canonical bytes+newline). REAL selfplay: 6/6 settled two-process,
      14 artifacts, kit check_artifacts ALL PASS incl. --terms uid derivation. CLI: serve,
      selfplay, kill, compare, doctor.

## Phase 8 — sparring exam (next)

- [ ] 4 role/model combos vs kit sparring peer, `--hint-lang mixed`, `--turn-timeout 30`;
      tracker offset 0 vs audit-revealed trail; freeze capture-rate regression; our thief must
      survive the sparring cop; tune the building regime until our cop beats the sparring thief.

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
