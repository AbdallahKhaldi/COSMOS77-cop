# PRD-4 — Natural language + scent: pheromone field, hints, deception (book ch. 4 + 6 · stage 4)

## Goal

The uncertainty layer: emit and decay our pheromone field exactly per the pair-locked model,
consume the opponent's transmitted field, and speak the only legal deception channel — free-language
hints ≤15 words, LLM-authored with a zero-token fallback that guarantees every sub-game finishes.

## Scope

**In:** wiring vendored `protocol/scent.py` into the turn loop (emit / merge-by-max / deposit-then-
decay / receiver-side decay), `hints/templates.py` (arena-aware canned truths/lies, role persona),
`hints/gemini.py` (google-genai, model + timeout from `peer.toml [trash_talk]`, metered; the
endpoint refuses any deadline under 10 s, so shorter values are clamped up, never obeyed),
`hints/liar_score.py` (per-opponent hint-truthfulness vs scent-derived ground truth),
coordinate-regex lint, hard 15-word truncation, intent flagging MEASURED against the cell we
seal, token metering per sub-game/series with the negotiated series budget as a hard stop.

**Out:** the scent-model *math* itself (vendored, PRD-6 conformance), tracker consumption (PRD-3).

## Binding rules implemented

| Rule | Requirement | Where |
|---|---|---|
| 23 | Scent model cryptographically locked pre-game | greeting carries `scent_model_sha256` (registered doc hashes; default `subtractive_chebyshev_v1`, accept `multiplicative_book_v1`) |
| 26 | Communication in free natural language only | hints are prose; template pool is natural-language |
| 27 | No numeric-coordinate protocols | outgoing hints pass a coordinate-regex lint before send; violations replaced by a safe template line |
| 25 | LLM for text only | `hints/` may not touch move selection; provider failure of ANY kind falls back to templates (zero tokens) |
| 54 | Token totals reported | `gemini.py` meters usage into per-sub-game and per-series counters consumed by the report builder |
| Playbook §2.2 | `intent ∈ {truth, lie}` sealed truthfully | intent computed from whether the chosen line matches our actual move/quadrant; a bluff recorded as truth is tampering |
| Playbook §2.4 | Wire conventions | transmitted model sends `{"r,c": v}` (>0 cells only); `multiplicative_book_v1` sends `smell_grid: {}` — the key is never dropped |

## Cop persona (this repo)

Hints are **misdirection with ROI honesty**: imply presence where we are not, herd hint-trusting
thieves toward our wall line; occasionally truthful (flagged `truth`) to poison naive
lie-detectors. Expected ROI vs scent-reading teams ≈ 0 (our transmitted grid pinpoints us anyway) —
hints are flavor + points against naive teams, never load-bearing. Config:
`[trash_talk] provider = "gemini" | "template"`, `every_n_steps`.

## Acceptance criteria

- [ ] Emission window/values match the locked model exactly (kit `pheromone` / `scent_book_v3`
      vectors already green via PRD-6; this PRD proves the *turn-loop wiring*: deposit-then-decay
      order, merge-by-max, receiver-side decay, emission gated on center ≥0.5).
- [ ] A seeded selfplay turn sequence produces hints that are ≤15 words, coordinate-free, correctly
      intent-flagged, and metered (mocked Gemini usage counts accumulate).
- [ ] Gemini failure paths (timeout, exception, quota, malformed reply) all fall back to templates
      with zero user-visible stall; the sub-game always finishes.
- [ ] `every_n_steps` respected; hard truncation to 15 words proven on an over-long mock reply.
- [ ] Liar-score: a scripted lying opponent's hints converge to near-zero weight; truthful ones
      converge upward; scores persist per opponent across sub-games.

## Test plan

ALL Gemini I/O mocked (`tests/hints/test_gemini.py` with canned SDK responses + failure injection;
`test_templates.py` pool properties: word cap, no digits-pair patterns, arena vocabulary;
`test_liar_score.py` convergence; `tests/scent/test_turn_wiring.py` seeded emission/decay traces
byte-compared to hand-computed frames). No live API calls anywhere in CI; a `doctor` subcommand
(PRD-7) performs the only live-key check, manually.

## Dependencies / phase mapping

Implements playbook **Phase 6**. Depends on PRD-1/PRD-6 (engine + vendored scent math), PRD-3
(tracker context for intent computation). Needs `GEMINI_API_KEY` in `.env` only for live play —
never for tests.
