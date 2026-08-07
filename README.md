# COSMOS77-cop — cop agent · Distributed Cops-and-Robbers over a P2P network

The **cop half** of team `cosmos77`'s final project for *Orchestration of AI Agents* (course
203.3763, Dr. Yoram Segal, U. Haifa): a P2P pursuit agent that plays 6-sub-game series against
other teams' agents over FastMCP, with SHA-256 commit–reveal integrity, a mutual end-of-game
audit, automated Gmail JSON reporting, a local-truth live GUI, and a cryptographic replay viewer.

**Team cosmos77:** Tasneem Natour · Abdallah Khaldi

**Sister repo (the thief half): [COSMOS77-thief](https://github.com/AbdallahKhaldi/COSMOS77-thief)**
— two fully separate processes in two separate repos with no shared live state (league rule); only
the stateless `protocol/` package is vendored byte-identically in both.

Interoperates byte-for-byte with the community league kit
([Imreec/copthief-league-protocol](https://github.com/Imreec/copthief-league-protocol)), whose
`vectors/*.json` are executable ground truth for every hash this repo produces, and with the
reference implementation ([rmisegal/Game-P2P-Cop-Chase](https://github.com/rmisegal/Game-P2P-Cop-Chase)).

> The full academic report (Dec-POMDP model, FastMCP orchestration dilemmas, strategy analysis,
> GUI + replay screenshots) lands here in Phase 12. The graded development story lives in `PRD/`,
> `PLAN.md`, and `TODO.md` from Phase 1.

## Quickstart

```bash
uv sync        # Python 3.12 + all deps (uv only — no pip, no conda)
make test      # pytest; coverage ≥85% enforced
make lint      # ruff; zero violations policy
```

## Screenshots

**Live view — local truth only (rules 8–9).** Our cell (green), the barriers we have seen
declared, the scent field we perceive (blue), and our posterior over the opponent (red). The
opponent's true position is never an input to this window; even when tracking is exact it appears
as a belief of 1.0, which is an *inference* from the grid they transmitted.

| Exact tracking (scent inversion) | Degraded / belief mode (`multiplicative_book_v1`) |
|---|---|
| <img src="docs/img/live_belief_exact.svg" width="430"> | <img src="docs/img/live_belief_degraded.svg" width="430"> |

**Replay viewer — per-step verification (rule 20).** Every revealed record is re-hashed with the
FULL sealed-payload construction `sha256(canonical_json(payload)\|nonce)`; the book's simplified
`nonce\|move` sketch does not reproduce a real commit, and the viewer catches that too.

| A clean log | The same log with one byte changed |
|---|---|
| <img src="docs/img/replay_verified.svg" width="430"> | <img src="docs/img/replay_tampered.svg" width="430"> |

Regenerate: `uv run cosmos-cop selfplay --windows 1 --snapshots docs/img` and
`uv run cosmos-cop replay <log.json> --screenshot docs/img`. The interactive Tk windows are
`--gui` on `serve`/`selfplay` and the `replay` subcommand.

## Status

| Phase | Deliverable | State |
|---|---|---|
| 0 | Bootstrap: repos, uv/py3.12 toolchain, league kit verified (113/113 vectors, clean 6/6 selfplay) | done |
| 1 | Seven PRDs + PLAN + TODO (development story) — see [`PRD/`](PRD/), [`PLAN.md`](PLAN.md), [`TODO.md`](TODO.md) | done |
| 2 | Engine: board physics, endings 46/47, scoring — 55 tests, 99% cov | done |
| 3 | Strategy: solver (thief-win proof honored), tracker inversion, two-regime cop brain | done |
| 4 | Protocol crypto: every kit vector replayed green; 4-layer audit; vendored protocol/ synced byte-exact | done |
| 5 | MCP net: 4 tools, at-least-once receiver, N00-N10 handshake, two-process smoke green | done |
| 6 | Scent pipeline (deposit-then-decay trail, argmax-stable wire), Gemini bluffs (metered, any-failure template fallback), liar-score | done |
| 7 | Series driver: live turn loop, 6 windows, mutual audits, 14 kit-valid artifacts, selfplay 6/6 over real HTTP | done |
| 8 | Sparring exam: 4 combos vs the kit peer — **90–30 ×3**, 45–45 in book mode, audits clean both sides, inversion measured 159/159 at offset 0 ([details](docs/SPARRING.md)) | done |
| 9 | Live local-truth GUI + cryptographic replay viewer (screenshots above) | done |
| 10 | Gated Gmail reporting: send-only OAuth, Gatekeeper (quota/bucket/DOS/429), doubly-armed recipients, rule-52 ledger, [ADRs](docs/DECISIONS.md) | done |
| 11 | Deploy artifacts: `deploy/render.yaml`, `scripts/warmup.py`, [runbook](docs/DEPLOY.md) — awaiting the human's Render/cloudflared setup | code done |
| 11B | Challenge Console (plug-and-play pairing) | next |
| 6–13 | Scent/hints → scent/hints → series driver → sparring → GUI/replay → Gmail → deploy → Challenge Console → academic README → league play | pending |
