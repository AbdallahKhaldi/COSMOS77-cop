# PRD-2 — FastMCP infrastructure: P2P peer, receiver contract, state machine (book ch. 2 · stage 2)

## Goal

Two fully separate processes that speak the reference wire over FastMCP streamable HTTP and stay
alive through duplicates, reordering, drops, and deadline pressure. This layer moves **opaque
validated messages**; it never interprets strategy and never blocks a handler.

## Scope

**In:** `net/server.py` (the four MCP tools), `net/client.py` (dialer), `net/receiver.py`
(at-least-once contract), `net/asgi.py` (uvicorn entry), `net/probes.py` (406 + loopback-nonce),
`orchestrator/machine.py`, `orchestrator/deadline.py`, `orchestrator/watchdog.py`, handshake
validation with refusal codes SPAR-N00…N10.

**Out:** public exposure (PRD-5), crypto payload construction (PRD-6), series sequencing (PRD-7).

## Binding rules implemented

| Rule | Requirement | Where |
|---|---|---|
| 1, 2 | Two separate processes; no shared memory | Repo boundary itself; `selfplay` shells out to the sibling repo's CLI as a subprocess |
| 3 | Orchestrator = single entry point | `orchestrator/gateway.py` is the only construction site for subsystems |
| 4, 5 | Standard state machine; illegal transitions rejected | `machine.py`: `WAITING_FOR_OPPONENT → COMPUTING_MOVE → COMMITTING → AWAITING_REVEAL → VERIFYING → (loop)`, absorbing `TECHNICAL_LOSS`; illegal transition ⇒ raise |
| 6 | Deadline tracking | one clock per expected message; deadline evaluated on **every** loop lap; tolerated traffic never renews it |
| 7 | Watchdog with controlled rescue | `watchdog.py` persists state + flushes logs on crash |
| Playbook §2.6 | Tools `negotiate`/`receive_turn`/`receive_control` take `message`; `submit_audit` takes `payload`; **all return `{"ok": True}` immediately** | `server.py`: validate → enqueue → return; refusals travel as ControlMessages, never as returns |
| Playbook §2.7 | Receiver contract | dedupe on the **commit** (never `(kind, step)`); reorder window 4 (min 1); ahead-in-window buffers; past-window violation; played-with-different-commit = equivocation (loud); budgets reconciled at load (`watchdog>0`, `poll<watchdog`, `connect≤turn`, `io_stall>turn`, `buffer≥1`) |
| Playbook §2.6 | Handshake refusals SPAR-N00…N10; bystander semantics for N06/N07 (refuse on record, keep waiting); omission never refuses | `net/handshake.py` |

## Design constraints that are easy to lose

- Both sides dial each other; one held session per peer, re-established **once** on failure; a
  "Session terminated" at a sub-game boundary is an event, not a death.
- A bare GET probe must see **406** (ready), not 200; 421 = tunnel host-header; 502 = edge with
  nothing behind it.
- Every outbound request carries an ISO-8601 UTC timestamp and a deadline; expiry = controlled
  retry or declared technical loss — never a hang.
- Greeting carries our locks + declared `game_uid` so a wrong-uid derivation dies at handshake
  (SPAR-N10), not at report-diff.

## Acceptance criteria

- [ ] `make smoke` green: this repo's peer + `../COSMOS77-thief`'s peer as two localhost processes
      complete a full handshake and one committed turn each (commit + hint + smell_grid on the
      wire; no in-play move reveal).
- [ ] All four tools respond `{"ok": True}` in <50 ms under a busy game loop (handlers never block).
- [ ] Fault injection (duplicate every message, reorder within window, drop-with-retry) produces a
      **byte-identical outcome ledger** vs the clean run.
- [ ] Every SPAR-N refusal code reproduced by a targeted malformed greeting; N06/N07 keep waiting;
      absent locks/uid never refuse.
- [ ] Deadline expiry under a message flood is still detected on the next lap (one-clock rule).
- [ ] State machine raises on every illegal transition (exhaustive transition-matrix test).

## Test plan

Mock the transport entirely (in-memory queues implementing the FastMCP call signatures) —
`tests/net/test_server_contract.py`, `test_receiver.py` (the §2.7 decision table, one test per
row), `test_handshake_refusals.py` (N00–N10), `tests/orchestrator/test_machine.py`,
`test_deadline.py` (flood + renewal-refusal cases), fault-injection suite
`tests/net/test_fault_injection.py` asserting ledger byte-equality. No real sockets in unit tests;
`make smoke` is the only place two real processes meet, and it runs the real HTTP path.

## Dependencies / phase mapping

Implements playbook **Phase 5** (with the state machine shared by every later phase). Depends on
PRD-1 (engine) and PRD-6 (sealed commits) for the smoke turn. Consumed by PRD-5 (public exposure)
and PRD-7 (series driver).
