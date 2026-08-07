# PRD-5 — Cloud exposure and tunneling (book ch. 2 · stage 5)

## Goal

The peer reachable from the public internet on two honest paths: **Render** (always-on availability
+ handshake/F1 smoke) and **local + cloudflared** (the path every F2/F3 friendly and ALL counted
runs actually use — Gmail credentials, artifacts, and git live on our machine, and F3 must run the
exact counted bytes on the exact counted network path).

## Scope

**In:** `deploy/render.yaml`, `net/asgi.py` as the uvicorn entry, `scripts/warmup.py` (poll until
406), `docs/DEPLOY.md` (cloudflared runbook: quick tunnel, 421 host-header fix, loopback proof),
probe integration with `kit/tools/netcheck.py`.

**Out:** any counted-run mail/artifact behavior on Render (structurally impossible there — no
credentials, ephemeral disk — and that is correct).

## Binding rules implemented

| Rule | Requirement | Where |
|---|---|---|
| 10 | Tunnel the local server to the public internet | cloudflared quick tunnel (`cloudflared tunnel --url http://localhost:<port>`); 421 fixed at the tunnel (`originRequest.httpHostHeader`), never in code |
| 39, 40 | No secrets in the repo | Render env vars (`GEMINI_API_KEY`, `PYTHON_VERSION=3.12`); `credentials.json`/`token.json` never leave the local machine |
| Playbook §2.6 | Probe semantics | ready = **406** to a bare GET at `…/mcp` (never 200); 502 = edge with nothing behind; loopback-nonce probe is the only proof our own public hostname reaches our own listener |

## Deployment facts (HW6 lessons, binding here)

- Render build: `pip install -e .` (**editable** — a plain install orphans `config/`).
- Start: `uvicorn cosmos77_cop.net.asgi:app --host 0.0.0.0 --port $PORT`; Health Check Path
  **blank** (MCP servers have no GET /).
- Free dynos sleep ~15 min (~50 s cold start): `scripts/warmup.py` runs 10 min before any window;
  the pairing page documents "first probe may need a retry".
- Env `STANDING_FRIENDLY=1` enables the Phase-11B await-peer mode.

## Acceptance criteria

- [ ] Both Render services answer 406 to a bare GET at `…/mcp` (human deploys; agent verifies).
- [ ] A cross-machine F1 handshake succeeds against at least one deployed endpoint.
- [ ] `netcheck.py --expect 406` and `--loopback` pass for the cloudflared path.
- [ ] `warmup.py` turns a cold service ready within its poll budget and exits nonzero on failure.
- [ ] A counted-armed run on Render is structurally impossible (no credentials present; the arming
      preflight refuses when it cannot deliver its report).

## Test plan

Unit: `tests/net/test_probes.py` (406/421/502/timeout classification against a mocked HTTP layer),
`tests/deploy/test_warmup.py` (poll loop with mocked responses, budget exhaustion). Live checks are
manual runbook steps recorded in `docs/DEPLOY.md` with expected outputs; no live network in CI.

## Dependencies / phase mapping

Implements playbook **Phase 11** (+ feeds Phase 11B standing-friendly mode). Depends on PRD-2.
Human inputs: Render account/services, cloudflared install (`brew install cloudflared`).
