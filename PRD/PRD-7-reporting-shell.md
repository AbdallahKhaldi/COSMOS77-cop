# PRD-7 — Reporting & visualization shell: artifacts, Gmail, GUI, replay (book ch. 9/7/App. A · stage 7)

## Goal

The outer shell that turns played games into **defensible, graded evidence**: per-game artifacts in
counted format, gated Gmail reporting that cannot misfire, a local-truth live GUI, a cryptographic
replay viewer, and (Phase 11B) the Challenge Console that makes pairing with us near-zero-effort.

## Scope

**In:** `report/result.py` (artifact builders), `report/gatekeeper.py`, `report/gmail.py`,
`report/compare.py` (report-compare ritual), `orchestrator/series.py` (six windows, role
alternation, sequencing, settlement), `gui/live.py`, `replay/viewer.py`, `console/` (ops dashboard
+ public pairing page), the full CLI (`serve | selfplay | friendly | counted | replay | report |
doctor | compare | kill`).

## Binding rules implemented

| Rule | Requirement | Where |
|---|---|---|
| 8, 9 | Live UI local truth only; never the objective board | `gui/live.py` renders OUR position, OUR barrier knowledge, the tracker's posterior heatmap, hints ticker, YOUR TURN/LOCKED banner — even exact-mode tracking renders as belief=1.0, and the console shows OPERATIONAL data only (never any board/position/scent) |
| 20 | Replay + verification viewer | `replay/viewer.py`: step fwd/back, per-step recompute of the FULL sealed-payload commit → `Verified OK` / `TAMPERED` (one failure voids the match) |
| 28, 29 | Token-bucket limiter + DOS detector on Gmail | `gatekeeper.py`: quota manager (daily cap) + bucket (`tokens = min(C, tokens + r·Δt)`, allow ⟺ ≥1; defaults r=0.5/s, C=5 from config) + anomaly lock; 429 ⇒ exponential backoff, never blind resend |
| 30 | `gmail.send` scope only | OAuth Desktop flow; send-only; gate on the RECIPIENT (send-only cannot draft) |
| 32–35, 51 | Automatic JSON report per legal counted game, from BOTH teams, to `rmisegal+uoh26finalgame@gmail.com` | body = the **exact canonical bytes** hashed AND the same file as the single attachment; totals derived, never declared |
| 31, 37, 38, 52 | League integrity | truthful `counted_games_played` (exclusive) at declaration; `games_played_including_this` (inclusive) in the report; one counted game per opponent; friendlies fully disarmed (counts unbumped, diversity false); rule-52 ledger committed and advanced only by the counted settlement path |
| 53, 54 | Per-game commit + token totals in the report rows | `github_commit` bare 40-hex per sub-game row; `tokens` per group |
| 49, 50 | Two cross-linked repos; PRD/PLAN/TODO/README present | repo layout (this file is part of it) |
| 41–45, 55 | Tag, academic README, Moodle discipline, 8-char team code, self-grade = code quality | Phase 12 outputs |

## Structural safety (the money-losers, designed out)

- The lecturer address is **structurally unreachable** unless config `counted=true` AND CLI
  `--counted` (two independent switches; friendlies mail only our two inboxes from TEAM.env.md).
- A series with any unsettled played sub-game **emits nothing** (rule 35 protection) — and the
  driver still plays all six windows.
- Artifacts are written as **canonical bytes + newline**; the emailed body is those exact bytes.
- `compare.py` implements the must-match / may-differ ritual (digest_kit §9): run after every
  friendly and counted series, both directions.
- Window N launches only after window N−1's log file exists; `kill` frees ports and tracked PIDs
  (orphaned peers keep playing).

## Acceptance criteria

- [ ] `cosmos-cop selfplay` (two processes, sibling repo as subprocess) settles 6/6 with clean
      audits and writes all 14 artifacts; `kit/tools/check_artifacts.py` passes incl. `--terms`.
- [ ] Dry-run report: body bytes == attachment bytes == hashed preimage; consensus signature
      verifies by pop-and-rehash.
- [ ] Gatekeeper unit matrix: quota exhausted / bucket empty / DOS lock / 429 backoff — all block
      the send and say why.
- [ ] Armed-path test proves the lecturer address is unreachable in every non-counted mode.
- [ ] Live GUI runs during a selfplay sub-game showing local truth only; replay stamps a clean log
      `Verified OK` and a deliberately corrupted byte `TAMPERED`.
- [ ] Console: pairing page generates a constitution + uid byte-identical to a hand-derived one;
      the counted button on the web path is structurally disabled (asserted by test).

## Test plan

ALL Gmail I/O mocked (`tests/report/test_gmail.py` MIME assembly byte-checks, `test_gatekeeper.py`
matrix, `test_recipient_gating.py`), `tests/report/test_result.py` (artifact shapes vs
`kit/examples/pairing-artifacts/`), `test_compare.py` (must-match/may-differ fixtures),
`tests/orchestrator/test_series.py` (alternation, sequencing, settle-all-six, emits-nothing rule),
`tests/replay/test_viewer.py` (verify + tamper), GUI logic tested headless (render model, not
pixels), `tests/console/test_web_cannot_arm.py`.

## Dependencies / phase mapping

Implements playbook **Phases 7, 9, 10, 11B** (+ Phase 12 outputs). Depends on every PRD before it.
Human inputs: Gmail `credentials.json` + first OAuth consent (Phase 10), `WEB_PASSPHRASE` for the
console.
