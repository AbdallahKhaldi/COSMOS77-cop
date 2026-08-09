# Interpretation decisions (ADRs)

The rulebook, the reference implementation and the community kit disagree in a handful of places.
The book's own academic-freedom clause says: implement either side, but **document and justify**.
Each record below states the conflict, what we do, and why — so a grader (or an opponent) can
check our reading rather than guess it.

---

## ADR-001 — "Email the lecturer the commit number per game" is satisfied inside the result JSON

**Conflict.** Appendix F instruction 5 asks that the commit number of each game be emailed to the
lecturer. Rule 53 separately requires the played commit in the step-zero declaration. Read
literally, instruction 5 could mean a *second*, separate email per sub-game.

**Decision.** One email per counted series, and the commits ride inside it: every row of
`sub_games[]` carries `github_commit: {<group_id>: <bare 40-hex>}`, and the declaration carries
the same value per group. No separate commit email is sent.

**Why.** Rule 34 forbids free-text reports and the kit's own artifact bundle reads instruction 5
the same way — the commit is a *field*, not a message. A second email stream would also be
unparseable for the lecturer's automation and would burn Gatekeeper quota for no informational
gain. The commits are machine-readable, byte-comparable between the two teams' reports, and
resolvable on GitHub.

---

## ADR-002 — "Report after every legal game" means counted games to the lecturer, friendlies to us

**Conflict.** Rules 32/35 say results are reported automatically after every legal game. Chapter
9.2.1 also recommends warm-up games, which are legal games that do not count.

**Decision.** A counted series emails exactly one report per team to
`rmisegal+uoh26finalgame@gmail.com`. A friendly emails the same artifact to **our own two
inboxes** and never to the lecturer, with every league field disarmed.

**Why.** Rule 37 makes the lecturer's count of our counted games load-bearing, and rules 37–38
make a false declaration project-fatal. Friendly reports arriving at the league address would
corrupt exactly the count the league is built on. Reporting them to ourselves keeps the habit
(and the compare ritual) without touching the lecturer's ledger. Enforced in code: the league
address is only reachable from `recipients_for()`, which requires config `counted=true` **and**
CLI `--counted`, and a test asserts no other posture can produce it.

---

## ADR-003 — Every "signature" in this project is a SHA-256 construction, not public-key crypto

**Conflict.** Chapter 5 speaks of a "pre-supplied key" for the step-zero declaration, which reads
like asymmetric signing. The kit states plainly that there is **no public-key cryptography
anywhere** in the release.

**Decision.** All four signature-shaped things are SHA-256: the terms signature is a commit over
the flat terms with the signer's nonce; per-step commits are `sha256(canonical|nonce)`; the
declaration's per-group `signature` blocks are sign-then-insert hashes over the group block; the
report consensus signature is the spaced-form hash inserted under
`חתימת_קונסנזוס_משותפת`.

**Why.** Interop beats literalism: an asymmetric signature the opponent cannot verify is worse
than useless, and every reference construction in the kit's vectors is a hash. The nonce supplies
the unforgeability the "key" phrasing was reaching for — it stays secret until the audit.

---

## ADR-004 — Appendix B's `rate_limits.json` lives in `game.json`; send tunables stay private

**Conflict.** Appendix B lists `rate_limits.json` as a shared JSON file, but Appendix F's
Gatekeeper values also appear as the `rate_limiter_gatekeeper` block of the shared constitution,
and some of them (a daily mail cap, a burst allowance) are about *our mailbox*, not about the
game.

**Decision.** The negotiated limits live in `config/game.json` under `rate_limiter_gatekeeper`
(one shared, signed file — no second artifact). The token bucket's **refill rate derives from the
signed `requests_per_minute`**, so the opponent can see it; the **burst capacity and daily cap
are private** and live in `config/peer.toml`.

**Why.** The decision test from Appendix B is "must the opponent agree on, or rely on, this
value?". They rely on our request rate; they do not rely on how many emails our own account will
send in a day. Keeping private values out of the shared file also keeps the byte-for-byte
identity of `game.json` (rule 11) achievable, since two teams need not agree on each other's
mailbox policy.

---

## ADR-005 — Exact scent inversion is gated on the pair-locked scent model

**Conflict.** Under `subtractive_chebyshev_v1` the argmax of a transmitted grid is the emitter's
current cell (we measured 159/159 at offset 0 against the community kit). Nothing in the protocol
says a *different* model's grid behaves that way.

**Decision.** The tracker reports `exact` only when the pair locked
`subtractive_chebyshev_v1`. Under any other locked model it stays `fuzzy` no matter what arrives
on the wire, and the physics-constrained belief map leads.

**Why.** Measured, not assumed: against the kit's `multiplicative_book_v1` peer, the transmitted
grid did **not** invert — its true position sat still for six turns while our argmax wandered.
Trusting it handed our brain a confidently wrong cell and cost a series 30–90; gated, the same
matchup settles 45–45. A confidently wrong position is worse than a declared unknown. See
`docs/SPARRING.md`.

---

## ADR-006 — Counted runs execute on the always-on hub, SSH-armed (amends Phase-11, 2026-08-09)

**Conflict.** The Phase-11 deployment decision (docs/DEPLOY.md) scoped the cloud to smoke tests
and put **every counted run on local + cloudflared**, because the free cloud tier had no Gmail
credentials and an ephemeral disk — a counted run there could neither persist its artifact set
nor send its report. The arena era changed the facts: the team now operates an always-on Railway
hub (`COSMOS77-hub`) that spawns both agent repos as subprocesses with resident credentials and a
mounted volume. Two committed decisions cannot both describe where the graded games run.

**Decision.** Amended 2026-08-09: **counted games run ON the hub from day one.** Arming is only
possible through the hub's `cosmos-hub-counted` CLI in an interactive SSH terminal — it refuses
when stdin is not a TTY and demands the typed phrase `ARM COUNTED` — after the operator hand-sets
the double-arming this repo already requires (config `counted=true` **and** CLI `--counted`,
unchanged from ADR-002's posture). Every web-reachable hub path structurally refuses
`kind=counted` and any `--counted` argv (HTTP 403, pinned by tests). The Phase-11 local +
cloudflared path is demoted to a rehearsal/backup posture; Render stays a warm availability
backup.

**Why.** The reasons the Phase-11 decision gave for "local" were durability, credentials and
network identity — and the hub now satisfies them better than a laptop: a persistent volume for
the unrepeatable rule-52 artifact set, Gmail credentials materialized at boot (mode 0600, never
logged, `gmail.send` scope only), permanent public URLs with no tunnel cold-start inside an
agreed window, and a truthful Step-0 hardware declaration via the `HUB_HARDWARE_DESC` override
(the agents declare the container's real hardware, never a fictional machine — rules 37–38 make
false declarations project-fatal). F3's rehearse-the-counted-bytes logic carries over intact:
friendlies on the hub exercise the same bytes, processes and network path as the counted run.
The SSH-only TTY gate preserves the human-ceremony invariant the league requires.

---

## ADR-007 — The web arena is the live GUI medium; bodycam by construction (rules 8–9)

**Conflict.** Phase 9 delivered the mandated live GUI as a local Tkinter window rendering our
local truth. The arena era adds a public always-on 3D viewer streaming every game. Rule 8 makes
a live GUI that shows the objective board a **project disqualification**, and rule 9 mandates a
cryptographic replay viewer — so a public viewer needs a documented reading of how it can be
legal at all, and of which GUI is the medium of record.

**Decision.** The hub's web arena is the live GUI medium of record, designed as a **bodycam**:
the live page renders exactly ONE agent's local truth at a time (switchable perspective), fed by
a per-perspective WebSocket channel whose envelopes are composed hub-side from that agent's own
`events.jsonl` — position, own barriers, perceived scent, hints, and the posterior rendered as a
labeled **BELIEF** hologram, never an opponent position. The live channel is structurally unable
to show the objective board: envelope payloads are whitelisted to the agent's `LiveView` fields,
window/series artifacts' post-reveal `records` never reach it, and one socket carries one
perspective (no fused frames). The **bird's-eye view exists only in the settled-replay cinema**,
rebuilt post-settlement from the mutually revealed audit trails with per-step SHA-256
`Verified OK / TAMPERED` stamps (the rule-9 artifact). The Phase-9 Tkinter GUI remains as the
offline fallback.

**Why.** Rules 8–9 draw the legality line between live knowledge and settled, mutually revealed
history — so the design enforces that line in the transport, not in the renderer: what the wire
does not carry, no page can leak. A spectator-grade public arena also serves the league goal
directly (opponents who watch a replay with integrity stamps become opponents who schedule
games), and the replay cinema doubles as the mandatory verification artifact with its per-step
seals. Screenshots for both READMEs come from the arena live view and the replay cinema — the
same two surfaces the professor can visit.
