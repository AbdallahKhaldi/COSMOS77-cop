# PRD-6 — Security & cryptography: commit-reveal, Step-0, audit (book ch. 5 · stage 6)

## Goal

Byte-exact, kit-conformant integrity: one canonical serialization, the pinned commit construction,
truthful Step-0, and a four-layer end-of-game audit whose verdicts we can defend. The kit's
`vectors/*.json` are the executable specification — every construction below must reproduce them
inside OUR test suite, in both repos, forever.

## Scope

**In:** vendored `protocol/` (canonical.py, sealing.py, terms.py, ids.py, scent.py, outcome.py,
consensus.py — stateless, no I/O, byte-identical across repos via `scripts/sync_protocol.py` + an
identity test), `crypto/nonce.py`, `crypto/step0.py`, `crypto/audit.py`, settlement rules,
`tests/vectors/` (kit fixtures replayed against our functions).

**Out:** transport (PRD-2), report mailing (PRD-7).

## Binding rules implemented

| Rule | Requirement | Construction |
|---|---|---|
| 17 | SHA-256 commit-reveal | `commit = sha256(canonical_json(payload) + "\|" + nonce)` — nonce pipe-appended OUTSIDE the JSON; canonical = `sort_keys=True, ensure_ascii=False, separators=(",",":")` |
| 18 | Nonce secret until game end | `secrets.token_hex(16)` (32 lowercase hex); revealed only in `submit_audit` |
| 19 | Any audit hash mismatch ⇒ forger scores 0 | audit layer 1; verdict `TAMPERED` kept apart from `ILLEGAL` (physics) |
| 23 | Scent model locked pre-game | registered doc hashes (`subtractive_chebyshev_v1` = `81ebee59…`, `multiplicative_book_v1` = `934c220d…`); refuse ONLY when both declare and hashes differ — omission never refuses |
| 24, 53 | Hardware + commit declared at Step-0 | `step0.py`: platform/psutil hardware incl. `cpu_freq_ghz`, `git rev-parse HEAD` as bare 40-hex `code_version`, truthful `num_games_declared` |
| 36 | Comprehensive mutual audit every game | four layers: (1) integrity — every revealed record re-hashes to its own commit with OUR serializer; (2) **binding** — revealed commit == received commit per step up to the consumed frontier, and every received step revealed; (3) physics from the revealed position trail (on-board, ≤1 orthogonal step, quota, ceiling+1 terminal) — never from move-token spelling; (4) concession/answer corroboration (rule 46/47 endings must be SAID and then proven against the cop's OWN barrier record + trail end) |
| Playbook §2.3 | `terms_signature = commit(flat-14-terms, own_nonce)`; `game_id = "-vs-".join(sorted)`; `game_uid` from **the flat 14 terms** + sorted pair — never the whole config; uid declared in the greeting | `terms.py`, `ids.py` |
| Playbook §2.5 | Report consensus signature = SPACED separators, sign-then-insert under `חתימת_קונסנזוס_משותפת` | `consensus.py` — the release's one deliberate serialization exception |

## Settlement (one rule, playbook §2.9)

Audits exchanged & clean → played outcome stands. Exchanged & failed → `tamper_forfeit` (the failed
audit IS the settlement). No audit on a zeroed outcome → settled technical-loss row
(`log_verified: false, tampered: false`). No audit on a **played** outcome → NOT settled → no
result artifact, **nothing is sent** — and all six sub-games are finished regardless.

## Acceptance criteria

- [ ] Every applicable kit vector replays green against OUR functions in BOTH repos:
      `canonical_json`, `commit_reveal` (incl. all three `divergent_forms` telling apart),
      `terms_signature`, `game_uid`, `uid_declaration`, `pairing_declaration`, `locked_model`,
      `pheromone`, `scent_book_v3`, `report_consensus`, `delivery_contract`.
- [ ] Hebrew + astral-emoji payloads round-trip unescaped (`ensure_ascii=False` proven by hash).
- [ ] `scripts/sync_protocol.py` copies cop→thief; a pytest in each repo asserts the two
      `protocol/` trees are hash-identical AND the vectors pass.
- [ ] Audit engine: seeded tamper (1 byte), wholesale re-forged log (self-consistent but not
      binding), illegal trail, false concession, and honest-degraded (no position fields) each get
      the correct verdict — TAMPERED / TAMPERED / ILLEGAL / tamper_forfeit / verified-with-notes.
- [ ] Step-0 record carries real hardware + the currently-checked-out commit; refuses a dirty tree
      for counted runs.

## Test plan

`tests/vectors/test_kit_conformance.py` (fixture replay, parametrized over every case),
`tests/protocol/test_canonical.py` (float spellings `0.1`/`6.0`/`1e-07`/`1e+16`, code-point key
sort, `"10,1" < "2,3"`), `test_sealing.py`, `test_ids.py` (uid from flat terms vs whole config —
the wrong one must NOT equal ours), `tests/crypto/test_audit.py` (verdict matrix above),
`test_step0.py` (mocked psutil/git), `test_sync_identity.py`. Deterministic; nonces injected.

## Dependencies / phase mapping

Implements playbook **Phase 4** (before net, so network faults are never confused with crypto
faults — the book's ordering rationale, inverted deliberately: our wire tests need real commits).
Consumed by every later PRD.
