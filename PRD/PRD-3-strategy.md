# PRD-3 — Strategy module: retrograde solver, tracker, cop brain (book ch. 6 · stage 3)

## Goal

Moves that are **provably pure Python** (rule 25 — we bind the recommendation as a hard rule) and
league-winning: a retrograde (backward-induction) pursuit solver that is exact per barrier
configuration, a scent-inversion tracker that recovers the opponent's true cell from its
transmitted grid, and a cop brain whose barrier planner constructs a win the bare board does not
offer.

## Scope

**In:** `strategy/solver.py` (retrograde value + optimal move for both roles), `strategy/tracker.py`
(exact + degraded opponent-position estimation), `strategy/cop_brain.py` (pursuit + two-regime
barrier planner + truthful claim policy), `belief/bayes.py` (physics-constrained posterior used
when no grid is transmitted). Brains are pure functions of (config, tracker state, engine state).

**Out:** hint generation (PRD-4), any network or LLM call — nothing in `strategy/` may import them.

## Game-theory ground truth (shapes every decision here)

The bare 4-neighbor 7×7 grid is **NOT cop-win for one cop**: C4 is a retract of the grid and
c(C4)=2, so the cop number is ≥2. Against optimal evasion the solver correctly returns ∞ on the
empty board — that is a *correctness check*, not a failure. Consequences: (a) the mirrored thief's
35-step survival is a provable floor; (b) **this cop's only constructed path to capture is graph
surgery** — barriers that shrink the thief's region until the solver's value turns finite; (c) the
solver's capture set must include the rule-46 radius: with the cop to move, a thief adjacent to
(or on) the cop's cell is capturable by barrier/claim.

## Binding rules implemented

| Rule | Requirement | Where |
|---|---|---|
| 25 | LLM never decides movement | `strategy/` has no LLM import; CI greps for it |
| 21, 22 | Only truthful capture claims | claim emitted only when engine ground truth (co-location or rule-46 adjacency with the finisher available) holds; posterior-probe claims only at ≥0.9 belief and still truthful in form |
| 15, 16 | Barrier declarations truthful | placements come from the engine's validated placement API |
| Playbook §4.1 | Tracker: argmax of the received `subtractive_chebyshev_v1` grid = emitter's exact cell (kit-measured 224/224); degraded mode = Bayesian posterior weighted by liar-score | `tracker.py` confidence ∈ {exact, fuzzy} |
| Playbook §4.3 | Two-regime barrier policy | building regime (value ∞): maximize reachable-region reduction + wall continuity toward a corner, never gated on `steps_to_capture`; finishing regime (finite): place/move only if post-placement value (after the thief's free reply) ≤ remaining budget; keep ≥2 barriers reserved for the rule-46 finisher |

## Solver requirements

State = (cop, thief, mover) per barrier set: ≤ 49·49·2 = 4802 states. Retrograde solve <100 ms;
memoized per barrier-set hash; recompute after each placement (≤14 times). Returns
`steps_to_capture` (∞ when evasion holds), optimal cop move, optimal thief move (max capture
distance). Ported technique: HW6 `strategy/pursuit.py` — adapted from king-move (cop-win) to
orthogonal (thief-win bare board) with the enlarged capture set.

## Acceptance criteria

- [ ] Empty 7×7 board: solver returns ∞ for the cop (thief-win confirmed — the C4-retract check).
- [ ] Hand-built corner trap: solver returns a finite value and pursuit converts within budget.
- [ ] Solver idempotent under barrier-set recompute; <100 ms per solve (measured in test).
- [ ] Building regime strictly shrinks the sparring `greedy` thief's reachable region within N
      placements (empirical N frozen as a regression once tuned in Phase 8).
- [ ] Finishing regime never extends projected capture beyond the remaining step budget.
- [ ] Tracker exact mode recovers the emitter cell on synthetic grids 100% (and offset 0 vs the
      sparring peer's audit-revealed trail in Phase 8 calibration).
- [ ] Degraded mode: posterior mass never on physics-impossible cells; caught-lying hints get
      near-zero weight.
- [ ] Claims: no test path can produce a claim without engine ground truth.

## Test plan

`tests/strategy/test_solver.py` (empty-board ∞, trap finiteness, rule-46 radius states, timing,
memo idempotence), `test_tracker.py` (synthetic emissions → argmax; two-frame delta tie-breaks;
degraded posterior invariants), `test_cop_brain.py` (regime switching, reserve-2, budget guard,
claim truth-gate; scripted opponents: greedy, random, solver-evader), `tests/belief/test_bayes.py`
(reachability constraints, liar-score weighting). All seeded/deterministic; property sweeps over
random barrier sets ≤14.

## Dependencies / phase mapping

Implements playbook **Phase 3**. Depends on PRD-1 (engine states). Feeds PRD-4 (tracker posterior
is the GUI heatmap + hint context) and the series driver (PRD-7).
