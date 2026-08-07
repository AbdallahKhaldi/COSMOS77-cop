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

## Status

| Phase | Deliverable | State |
|---|---|---|
| 0 | Bootstrap: repos, uv/py3.12 toolchain, league kit verified (113/113 vectors, clean 6/6 selfplay) | done |
| 1 | Seven PRDs + PLAN + TODO (development story) — see [`PRD/`](PRD/), [`PLAN.md`](PLAN.md), [`TODO.md`](TODO.md) | done |
| 2 | Engine: board physics, endings 46/47, scoring — 55 tests, 99% cov | done |
| 3 | Strategy: retrograde solver, scent-inversion tracker, brains | next |
| 4–13 | Protocol crypto → MCP net → scent/hints → series driver → sparring → GUI/replay → Gmail → deploy → Challenge Console → academic README → league play | pending |
