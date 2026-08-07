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
