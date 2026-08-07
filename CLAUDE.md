# CLAUDE.md — COSMOS77-cop (cop agent · team cosmos77 · course 203.3763 final project)

The master spec is `../../CLAUDE_CODE_PLAYBOOK.md` (binding rules §0–§2, architecture §3, strategy
§4, phases §5, traps ledger §7). Rulebook + kit digests: `../../reference/`. The community kit at
`../kit/` is executable ground truth — its `vectors/*.json` pin every hash this repo must produce.
This file pins what every session in THIS repo must obey.

## Engineering discipline (playbook §0.14 — non-negotiable, verbatim)

uv only · TDD, mock ALL LLM/MCP/network/Gmail I/O in tests · coverage ≥85% · ruff zero violations ·
≤150 lines per .py file · all logic behind a single `SDK` class per repo · zero hardcoded tunables
(config only) · Conventional Commits authored by the humans, **no AI co-author trailers** · type
hints + docstrings on public symbols · deterministic seeded tests.

## Hard rules that live in this repo's code (playbook §0)

1. Cop and thief are two separate processes in two separate repos. NEVER import the sibling repo
   (`../COSMOS77-thief`); `selfplay` shells out to its CLI as a subprocess over localhost HTTP.
   Vendored `src/cosmos77_cop/protocol/` must stay byte-identical with the sibling's copy
   (`scripts/sync_protocol.py` + the protocol-identity test).
2. Four crypto stages per step: Commit → Acknowledge → Reveal → end-of-game Final Audit. Nonces =
   `secrets.token_hex(16)`, secret until audit — never `random`.
3. Canonical JSON = `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`;
   commit = `sha256(canonical|nonce)` — nonce pipe-appended OUTSIDE the JSON. The ONE exception:
   the report consensus signature uses spaced default separators, sign-then-insert under the
   Hebrew key `חתימת_קונסנזוס_משותפת`.
4. The LLM NEVER decides a move. Moves are pure Python; Gemini writes hint text only (≤15 words,
   never coordinates, truthful `intent` flag) with a zero-token template fallback.
5. The live GUI renders LOCAL TRUTH only — never the objective board (project disqualification).
6. Secrets (`credentials.json`, `token.json`, `.env`) never in git. Gmail scope `gmail.send` only;
   every send goes through the Gatekeeper; the lecturer address is structurally unreachable unless
   config `counted=true` AND CLI `--counted`.
7. MCP tool handlers validate → enqueue → return `{"ok": True}` immediately; never block, never
   refuse via return value (refusals travel as ControlMessages). `submit_audit` takes `payload`;
   `negotiate`/`receive_turn`/`receive_control` take `message`.

## Commands

- `make test` · `make lint` · `make smoke` · `make kill` — gates and process hygiene
- `uv sync` · `uv run pytest` · `uv run ruff check .`
- CLI: `uv run cosmos-cop …` (serve | selfplay | friendly | counted | replay | report | doctor |
  compare | kill — subcommands land in Phase 7)

## Phase workflow

Work happens phase-by-phase per playbook §5, each phase on a branch `phase-N-<slug>` merged to main
at gate-green. Never advance on a red gate; never weaken a gate to pass it. Mirror every change
into `../COSMOS77-thief` in the same phase (role-specific code differs; `protocol/` is synced
verbatim).
