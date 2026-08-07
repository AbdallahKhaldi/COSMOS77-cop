# The sparring exam — measured interop against the community kit

Phase 8's gate. Every run is a full six-window series over **real HTTP** against
[`Imreec/copthief-league-protocol`](https://github.com/Imreec/copthief-league-protocol)'s sparring
peer (a third independent implementation whose crypto is imported straight from the kit's
`verify_vectors.py`, so it cannot drift from the published vectors).

Reproduce: `uv run python scripts/sparring_exam.py --label <name> [flags]`.

## Topology

The sparring peer runs one process whose role alternates each window and dials **one** URL; our
team is role-split across two fixed-role processes (rule 1: cop and thief never share a process).
`scripts/sparring_relay.py` bridges the two shapes — it terminates MCP and re-calls the current
window's owner, keyed on each greeting's `sub_game_number`. It routes transport only; it holds no
game state, and both of our peers still run their own servers, their own handshakes and their own
audits.

## Results

| Run | Opponent policy | Scent model | Our score | Their score | Windows settled | Audits | Artifacts | Tracker offset |
|---|---|---|---|---|---|---|---|---|
| `a-greedy` | greedy (opens thief) | `subtractive_chebyshev_v1` | **90** | 30 | 6/6 | clean both sides | ALL PASS + cross-join | 159/159 at 0 |
| `b-police` | greedy (opens police) | `subtractive_chebyshev_v1` | **90** | 30 | 6/6 | clean both sides | ALL PASS | clean at 0 |
| `c-book` | greedy | `multiplicative_book_v1` | 47 | 47 | 6/6 | clean both sides | ALL PASS | n/a (belief mode) |
| `d-random` | random | `subtractive_chebyshev_v1` | **90** | 30 | 6/6 | clean both sides | ALL PASS | clean at 0 |

All runs used `--hint-lang mixed` (the sparring default: Hebrew **and** an astral emoji on the
wire — the serializer exam that catches `ensure_ascii=True`). Every audit passed in both
directions, which means our `ensure_ascii=False` canonical form re-hashes identically inside an
implementation we did not write.

`c-book` reads 47–47 rather than 45–45 because a tied series pays the declared `series_add` bonus
(+2 each, added to totals) — the tie rule working end to end.

## What the exam measured, beyond "it interoperates"

**1. The inversion thesis, confirmed against a foreign implementation: 159/159 exact at offset 0.**
Every step of every subtractive-model window, the argmax of the opponent's transmitted grid was
its true cell as later revealed in the audit. This is the project's core claim, and it is now a
measurement rather than an argument (`scripts/calibrate_tracker.py`).

**2. Exact inversion is model-specific, and trusting it blindly is worse than knowing nothing.**
Under `multiplicative_book_v1` the peer still transmits a grid — but it does not invert to the
emitter's cell. Our first book-model run was swept 30–90: the tracker reported `exact` on that
grid and handed the brain a confidently wrong position (their true cell sat at (0,0) for six
turns while our estimate wandered). Exact mode is now gated on the pair-locked scent model; a
non-subtractive peer keeps us in belief mode, and the same matchup settles 45–45 (47–47 after the
tie rule). Pinned by `test_exact_mode_is_gated_on_the_subtractive_model`.

**3. Barrier declarations are an exact position channel.** Rule 15 makes every placement public
and truthful, and a placement is only legal on the cop's own cell or a 4-neighbour — so a declared
barrier pins the cop inside a five-cell set, and because placement *replaces* movement, the belief
must not diffuse that turn. The thief's belief layer uses both facts.

**4. The barrier planner has to keep itself inside.** A region cut that separates the cop from the
thief's component hands the thief a guaranteed survival however much area it removes. The building
regime now rejects those placements, and `test_cop_converts_against_the_kit_greedy_evader` freezes
the whole duel as a regression: capture within 25 moves from five different thief starts, quota
respected, never sealed out.

## Standing caveats

- The sparring peer is *one* opponent shape. A team that reads scent as an oracle the way we do
  will not lose 3/3 as its thief; the friendly ladder (F1→F2→F3) exists to find out which bucket
  each real opponent is in before a counted run.
- Calibration is per-opponent. Never enter a counted run without re-running
  `scripts/calibrate_tracker.py` over that opponent's friendly logs.
