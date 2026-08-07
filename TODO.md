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

- [x] Phase 8 (2026-08-08): sparring exam green — 4 combos over real HTTP, all 6/6 settled with
      clean audits both sides and `check_artifacts` ALL PASS (+ cross-team join). Scores 90-30
      (greedy both directions, random) and 47-47 (book model). Inversion MEASURED 159/159 at
      offset 0. Three defects found and fixed: exact mode must be gated on the locked scent model
      (a book-model peer's grid does not invert — cost us 30-90 before the fix), barrier cuts must
      never seal the cop out of the thief's region, and barrier declarations pin the cop to five
      cells. Duel regression frozen. Full record: `docs/SPARRING.md`.

- [x] Phase 9 (2026-08-08): local-truth live view (pure render model + Tk window + dependency-free
      SVG renderer), replay verification/viewer with per-step FULL commit recompute, `replay` and
      `--gui`/`--snapshots` CLI. Screenshots committed under `docs/img` (exact + degraded heatmap,
      Verified OK + TAMPERED). Legality pinned by tests: no GUI module can reach the rival's
      position. Two live-ops bugs found by the gate: selfplay's sibling lookup inverted under the
      mirror swap (spawned a second peer of our own role) and a series of technical losses exited
      0 — both fixed and pinned.

- [x] Phase 10 (2026-08-08): send-only Gmail (scope-asserted, all I/O mocked), Gatekeeper
      (daily quota + token bucket whose rate DERIVES from the signed requests_per_minute + DOS
      lock + exponential 429 backoff), MIME whose body and attachment are byte-identical to the
      hashed canonical bytes, doubly-armed recipient gating with the lecturer alias appearing in
      exactly one module, rule-52 ledger (committed), five ADRs in `docs/DECISIONS.md`.

- [x] Phase 11 code side (2026-08-08): `deploy/render.yaml` (editable install, blank health path,
      env vars), `scripts/warmup.py` (exits 0 ONLY on 406 — never on a 200), `docs/DEPLOY.md`
      (status-code table, cloudflared 421 host-header fix, loopback proof, T-protocol).
- [ ] **HUMAN**: create the two Render web services, set env vars, `brew install cloudflared`,
      then confirm 406 on both `/mcp` URLs + a cross-machine F1 + `netcheck --loopback`.

- [x] Phase 12 (2026-08-08): both READMEs rewritten as the academic report (Dec-POMDP model +
      the inversion contribution AND its measured limit, FastMCP dilemmas, honest game theory,
      why-no-RL, screenshots, ledger table, ADR/sparring links); `scripts/gen_submission.py`
      fills the Moodle form from TEAM.env.md and flags what a human still owes;
      `scripts/preflight.py` runs the §11.5 checklist as code — **17/17 mechanical checks pass in
      both repos**. The checklist caught six files that had drifted past the 150-line cap; all
      split into cohesive modules rather than weakening the rule.

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
