# Play COSMOS77 — the pairing sheet

Everything another team needs to play us, in the kit's own PAIRING-PLAYBOOK shape
(https://github.com/Imreec/copthief-league-protocol). Send corrections or a proposed T in the
group chat or on a kit issue — first contact on the record beats a DM.

## IDENTITY

```
group_id:        cosmos77
members:         Abdallah Khaldi (212389712) · Tasneem Natour (323118794)
repos:           cop  https://github.com/AbdallahKhaldi/COSMOS77-cop
                 thief https://github.com/AbdallahKhaldi/COSMOS77-thief
topology:        role-split (two endpoints; one address per role) — single-URL relay also offered
wire shape:      reference-v3 (flat 14-key terms + nonce + signature)
                 wire_shape_sha256  229ae6487a418c3fcb6da9be404de2f2533c288ebc228811bff6dedc4164d6f7
info_mode:       belief — info_mode_sha256 020947daeeb3f73494af9b04201326791742c7184085456e3517d21981ee1202
scent model:     subtractive_chebyshev_v1 — sha256 81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4
turn order:      thief moves first each sub-game (reference behaviour)
```

## ENDPOINTS — two transports, pick either

**A. Hosted (always up, nothing to schedule with us for friendlies):**

```
cop:    https://cosmos77-arena-production.up.railway.app/cop/mcp
thief:  https://cosmos77-arena-production.up.railway.app/thief/mcp
single: https://cosmos77-arena-production.up.railway.app/mcp   (window-parity relay)
```

A bare GET answers **406 — that IS the ready state** (an MCP endpoint refusing a browser GET is
healthy; see kit WARNINGS 2d). To bind our hosted agents to YOUR urls, use the challenge form on
https://cosmos77-arena-production.up.railway.app (MENU → Multiplayer) or tell us a T and we run
`--peer-url` at your addresses.

**B. Classic ports (what you asked for):** at an agreed T we run
`cop :8801` / `thief :8802` bound to the network (not loopback) on a machine reachable via
same-LAN IP, Tailscale, or an ngrok/cloudflared pair — your pick. Both agents accept inbound
dials and push outbound, so either side may open.

## DIALECT FACTS (so the first window is boring)

- `negotiate`: we **push first** AND we **answer every call with our greeting in the reply body**
  (`{"ok": true, "message": <greeting>}`) — compatible with push and request/response peers both
  (kit WARNINGS 2b). Read it from whichever place your build expects.
- Tools served: exactly `negotiate / receive_turn / receive_control / submit_audit` (SPEC §7.5).
- Turn messages: ten-key set, unknown keys tolerated and ignored, `timestamp` always non-empty
  ISO-8601, commit = `SHA256(canonical_json(payload)|nonce)` with a **single pipe**.
- Audit: we verify your disclosure against the commitments that **arrived in play** (WARNINGS 5d)
  and expect the same of you; clean games see no behaviour change.
- Consensus signature: the reference **five-key row** (`sub_game_number, roles, result,
  winner_group, score` — `tie` in the document row only), spaced separators, sign-then-insert
  under `חתימת_קונסנזוס_משותפת`.
- Roles: first-sorted group plays COP on odd sub-games (kit Stage-3 default).

## DERIVED VALUES for our standing pairings (verify independently)

| | best2934 | SMNGRP05 |
|---|---|---|
| agreed config sha256 | `9d129dd5958bf2b50dce50125308dae845c674a2f14c51d2cc07ccd1268402b2` | `db5b2cd0aa1a28418aad0f3ee114fcb16f6bdd522abfe66206c912eea22b5049` |
| game_id | `best2934-vs-cosmos77` | `SMNGRP05-vs-cosmos77` |
| game_uid | `98f8ea37-6472-97ad-9839-01514e7a32ea` | `a9ef6042-e900-bc7b-f229-af8299957670` |
| COP on odd (1,3,5) | best2934 | SMNGRP05 |
| COP on even (2,4,6) | cosmos77 | cosmos77 |

## MAIL & FAILURE POSTURE

- Friendly reports: both teams' own inboxes ONLY — never any lecturer address (our league rail is
  structurally unreachable unless a counted run is doubly armed: config AND CLI flag).
- Counted reports: the league alias, confirmed in chat before the counted T.
- Retry policy: **discard-and-rerun by mutual written agreement** unless you propose otherwise —
  agreed BEFORE any T.

## PROPOSED FLOW (kit playbook stages)

1. You confirm the config sha + derived values above (or send corrections).
2. One friendly window (F1) at an agreed T — reports to our two inboxes only.
3. Full friendly series (F2, six windows).
4. The counted series: rule 52, one per pairing, both reports filed same day.
