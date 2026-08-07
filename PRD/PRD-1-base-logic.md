# PRD-1 — Base Logic: board physics, endings, scoring (book ch. 3 · build stage 1)

## Goal

A deterministic, fully-tested game engine that runs a complete pursuit in a **single process with
zero I/O**: board, legal movement, barriers, all three capture families, survival, and the fixed
scoring table. Every later layer (strategy, net, crypto, GUI) consumes this engine; nothing in it
may depend on them.

## Scope

**In:** `engine/board.py` (grid + barrier set from config), `engine/rules.py` (legal-move
generation), `engine/capture.py` (ending detection), `engine/subgame.py` (turn sequencing, step
ceiling, outcome row). All tunables read from `config/game.json` — never constants in code.

**Out:** networking, LLM, scent transmission (the scent *model* lives in vendored `protocol/scent.py`,
PRD-6), GUI, artifacts. The engine never knows an opponent exists as a process.

## Binding rules implemented (App. E numbering · playbook §0–§2)

| Rule | Requirement | Engine behavior |
|---|---|---|
| 13, 14 | Orthogonal moves only; no diagonals | Move set = N/S/E/W/STAY; diagonal or >1-step deltas rejected as illegal |
| 12 | Minimums only raisable | Config loader refuses `board_size<7`, `barriers_max<14`, `max_steps<35` |
| 15, 16 | Barrier placement openly and truthfully declared | Placement API returns the declaration record the net layer must transmit verbatim |
| 46 | Barrier onto the thief's current cell = capture | `capture.py` family 2 |
| 47 | Thief with no legal move = captured (STAY does not rescue a fully-boxed thief) | `capture.py` family 3 |
| 21, 22 | Capture claims truthful only | Engine exposes ground truth so the brain can never claim falsely |
| 48 | Fixed scoring: capture 20/5 · survival 10/5 · technical 0/0 | Outcome table derived from config; zeroed rows are sanctions: `tie: false`, `winner_group: null` |
| Playbook §1 | 7×7 default, `(row, col)` top-left 0-indexed, thief [3,3] cop [0,0], quota 14, ceiling 35 | Constructor + validators |

Cop-specific mechanics owned here: barrier placement **replaces movement**, is legal on own cell or
a 4-neighbor, is permanent, decrements a quota, and blocks both agents.

## Role emphasis (this repo)

The cop engine drives **placement legality and claim truth**: every barrier placement is validated
before it becomes a public declaration, and capture detection (co-location + rule 46 radius) is the
only source a claim may be made from. The mirrored thief repo exercises the same engine from the
other side (rule-47 self-detection and concession duty).

## Acceptance criteria

- [ ] A scripted 35-step pursuit runs to survival with zero exceptions; a scripted capture ends the
      sub-game the move it happens.
- [ ] Diagonal, >1-step, off-board, and into-barrier moves are rejected; STAY always legal unless
      the mover's cell is irrelevant to legality (STAY never escapes rule 47).
- [ ] Barrier placement on own cell and on each 4-neighbor accepted; 5th-neighbor/diagonal rejected;
      quota exhausted ⇒ placement rejected; placement consumes the turn.
- [ ] Rule 46: placement onto the thief's cell yields `capture` immediately.
- [ ] Rule 47: a thief whose every orthogonal neighbor is barrier/off-board is captured even though
      STAY is geometrically possible; a thief with ≥1 open neighbor is not.
- [ ] Outcome rows byte-match the fixed table incl. the zeroed-sanction shape.
- [ ] Config with a lowered minimum (board 6, quota 13, ceiling 34) is refused at load.
- [ ] Coverage ≥85% on `engine/`; ruff clean; every file ≤150 lines; zero I/O imports in `engine/`.

## Test plan

`tests/engine/test_board.py` (construction, barrier sets, config minimums), `test_rules.py`
(exhaustive move-legality matrix over edge/corner/barrier-adjacent cells), `test_capture.py`
(all three families + rule-46 radius cases + boxed-corner and boxed-center rule-47 cases),
`test_subgame.py` (step ceiling, survival at 35, outcome rows, quota ledger). All tests seeded and
deterministic; no network, no clock, no LLM. Property-style sweep: every cell × every barrier
pattern of size ≤3 near the thief must classify rule-47 identically to a brute-force reachability
check.

## Dependencies / phase mapping

Implements playbook **Phase 2**. Requires only `config/game.json` (constitution defaults, §1).
Consumed by PRD-3 (solver reads engine states), PRD-2 (net drives subgame), PRD-6 (audit replays
physics), PRD-7 (GUI renders local state).
