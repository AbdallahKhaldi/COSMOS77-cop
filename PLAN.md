# PLAN.md — COSMOS77-cop build plan (phase map)

The master spec is `../../CLAUDE_CODE_PLAYBOOK.md`; this file is the repo-local map of its §5
phases to PRDs, gates, and branches. One phase per branch (`phase-N-<slug>`), merged to main at
gate-green; every phase mirrors into `../COSMOS77-thief` (role code differs, `protocol/` synced
verbatim). Never advance on a red gate; never weaken a gate to pass it.

| Phase | Branch | PRD | Deliverable | Gate (must be green) | Status |
|---|---|---|---|---|---|
| 0 | main (bootstrap) | — | Repos, uv/py3.12, skeletons, kit verified | uv sync + pytest + ruff clean ×2; kit 113/113 vectors + 6/6 selfplay | ✅ 2026-08-07 |
| 1 | phase-1-prds | all | Seven PRDs + PLAN + TODO (development story, rule 50) | 7 PRDs with acceptance criteria + PLAN + TODO in both repos | ✅ 2026-08-07 |
| 2 | phase-2-engine | PRD-1 | Board physics, endings 46/47, scoring | engine tests green, cov ≥85%, ≤150 lines/file | ✅ 2026-08-07 |
| 3 | phase-3-strategy | PRD-3 | Retrograde solver, tracker, cop brain | property tests: empty-board ∞, trap conversion, 35-step survival floor | ✅ 2026-08-07 |
| 4 | phase-4-protocol | PRD-6 | Kit-conformant crypto + vendored protocol | ALL kit vectors green in both repos; sync identity test | ✅ 2026-08-07 |
| 5 | phase-5-net | PRD-2 | MCP peer, receiver contract, state machine | fault-injection ledger byte-identical; `make smoke` green | ✅ 2026-08-07 |
| 6 | phase-6-hints | PRD-4 | Scent wiring, Gemini hints, liar-score | seeded selfplay hints ≤15 words, 0 coordinates, intents true | ✅ 2026-08-07 |
| 7 | phase-7-series | PRD-7 | Six-window driver + counted-format artifacts | selfplay 6/6 settled; `check_artifacts.py` + `--terms` pass | ✅ 2026-08-07 |
| 8 | phase-8-sparring | — | Interop exam vs kit sparring peer | 4 combos × both scent models green; thief survives; cop converts; tracker offset 0 | ✅ 2026-08-08 |
| 9 | phase-9-ui | PRD-7 | Live GUI + replay viewer | live GUI in selfplay; replay Verified OK + TAMPERED on corruption | ✅ 2026-08-08 |
| 10 | phase-10-report | PRD-7 | Gmail + Gatekeeper + counted reporting | byte-exact dry-run; gatekeeper matrix; armed-path proof | ✅ 2026-08-08 |
| 11 | phase-11-deploy | PRD-5 | Render + cloudflared runbooks | code side done; **406 / F1 / loopback need the human to deploy** | ⏳ 2026-08-08 |
| 11B | phase-11b-console | PRD-7 | Local challenge console | pairing uid matches the wire derivation; web-cannot-arm; page shows no board | ✅ 2026-08-09 |
| 12 | phase-12-readme | — | Academic README, tag, submission pack | 17/17 mechanical checks; README complete; submission form generated | ✅ 2026-08-08 |
| 13 | phase-13-league (per opponent) | — | F1→F2→F3→counted→settle→report | compare ritual both directions; consensus hash byte-equal; both reports delivered | — |

## Strategy thesis (why we expect to win — playbook §4)

Provable floor: the bare 4-neighbor board is thief-win (C4 retract ⇒ cop number ≥2), so our thief's
35-step survival is guaranteed vs any single cop. Constructed upside: our cop turns the transmitted
scent grid into an exact position oracle (argmax inversion, kit-measured 224/224) and wins by
barrier region-shrinking against imperfect thieves. Expected series: ~90–30 vs belief-based teams;
47–47 (`series_add`) vs kit-grade optimal teams. Every friendly measures which bucket the opponent
is in before the counted run.

## Working agreements

- TDD; all LLM/MCP/network/Gmail I/O mocked in tests; deterministic seeds.
- Conventional Commits by the humans (alternating authors, cross co-author trailers, no AI
  trailers).
- Zero hardcoded tunables — config only. Secrets never in git (rules 39–40).
- Interpretation decisions recorded ADR-style in `docs/DECISIONS.md` (lands Phase 10).
