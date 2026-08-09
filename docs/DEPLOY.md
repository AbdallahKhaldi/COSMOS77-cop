# Deployment runbook — public reachability without losing a window

Rule 10 requires the peer to be reachable from the public internet. We use **three** paths,
and they are not interchangeable.

| Path | What it is for | What it cannot do |
|---|---|---|
| **Railway hub** (always-on, canonical) | **Every counted run** (armed only from an operator SSH terminal — ADR-006), full friendlies, the public arena endpoints | Web paths structurally refuse counted; arming needs a human in an SSH TTY |
| **Render** (always-on) | Availability backup, first-contact handshakes, F1 smoke, the standing-friendly mode | No Gmail credentials and an ephemeral disk — it cannot write a durable artifact set or send a report, **by design** |
| **local + cloudflared** | F2/F3 rehearsal backup if the hub is ever unavailable | Needs a human at the machine |

Counted games execute on the always-on hub (decision amended 2026-08-09 — ADR-006 in
docs/DECISIONS.md: durable volume for the unrepeatable artifact set, resident Gmail credentials,
permanent public URLs, truthful Step-0 hardware declaration via `HUB_HARDWARE_DESC`). F3's point
is unchanged: rehearse the counted bytes on the counted network path — which now means a hub
friendly, not a tunnel — so a friendly that "passed on Render" proves nothing about the run
that scores.

## The ready signal is 406, not 200

An MCP server refuses a browser-shaped GET without
`Accept: application/json, text/event-stream`. So:

| Status | Meaning |
|---|---|
| **406** | **Ready.** Poll for this. |
| 400 | The server is there; the request had no MCP session (not an outage) |
| 421 | FastMCP's DNS-rebinding guard rejected the tunnelled `Host` — **fix at the tunnel**, never in code |
| 502 | The edge is up with nothing behind it (indistinguishable from a tunnel with no ingress — hence the loopback proof below) |
| 530 | Hostname unrouted |
| 30x | A forwarder, not the peer (a redirected POST becomes a GET) |

```bash
uv run python scripts/warmup.py https://cosmos77-cop.onrender.com/mcp     # exits 0 only on 406
python ../kit/tools/netcheck.py https://cosmos77-cop.onrender.com/mcp --expect 406
```

## Render (one-time, human)

1. New Web Service from this repo, plan free, runtime Python.
2. Build `pip install -e .` — **editable**. A plain install orphans `config/` and the peer will
   not start.
3. Start `uvicorn cosmos77_cop.net.asgi:app --host 0.0.0.0 --port $PORT`.
4. **Health Check Path: blank.** An MCP server has no `GET /`; a health check would flap it.
5. Env: `PYTHON_VERSION=3.12`, `GEMINI_API_KEY`, `WEB_PASSPHRASE`, `STANDING_FRIENDLY=1`.
6. `deploy/render.yaml` carries all of the above if you prefer a Blueprint.

Free dynos sleep after ~15 min and cold-start in ~50 s: run `scripts/warmup.py` **10 minutes
before** any agreed T, and tell opponents the first probe may need a retry.

## cloudflared (rehearsal / backup path — no longer the counted path, ADR-006)

```bash
brew install cloudflared
uv run cosmos-cop serve --port 8801 --peer-url <their-url> --gid-a cosmos77 --gid-b <them> \
    --out artifacts/<game_id> &
cloudflared tunnel --url http://localhost:8801        # prints https://<random>.trycloudflare.com
```

Give the peer `https://<random>.trycloudflare.com/mcp` — **the `/mcp` path is part of the
address.**

**If they see 421**, the tunnel is forwarding the public hostname as `Host`. Fix it at the tunnel,
not in our code:

```yaml
# ~/.cloudflared/config.yml
ingress:
  - hostname: <your-hostname>
    service: http://127.0.0.1:8801
    originRequest:
      httpHostHeader: 127.0.0.1:8801
  - service: http_status:404
```

(ngrok equivalent: `ngrok http 8801 --host-header=rewrite`.)

## Prove it is *our* listener, not just a live edge

A 502 and a healthy-but-empty tunnel look identical from outside. The loopback probe binds a
throwaway listener, fetches your own public hostname and demands its own nonce back:

```bash
python ../kit/tools/netcheck.py --loopback 8801 https://<random>.trycloudflare.com
```

Never enter a window without this passing.

## The T-protocol (per window)

1. Agree a wall-clock minute **with a timezone**.
2. Both sides launch at T without waiting for the other.
3. Probe every hostname at T+30 s (`--expect 406`).
4. If an edge is not ready, **kill everything and name a new T**. Never debug into a window —
   a failed handshake ends in ~60 s while a real sub-game takes minutes, so the failing side runs
   ahead and the two of you end up describing different series.

`make kill` (or `cosmos-cop kill`) frees our port between attempts: killing a shell does not kill
what it spawned, and an orphaned peer will happily keep playing sub-games for you.
