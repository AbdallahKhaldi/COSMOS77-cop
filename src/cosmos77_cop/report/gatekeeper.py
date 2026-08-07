"""The Gatekeeper: three cumulative protections on every send path (rules 28-29; book §9.3.1).

1. **Quota manager** — a hard daily cap; a report is worth points, a banned account is worth none.
2. **Token bucket** — ``tokens = min(C, tokens + r·Δt)``, allowed iff ``tokens >= 1`` (§9.3.2).
   The refill rate derives from the SIGNED ``requests_per_minute`` so both peers can see it;
   the burst capacity is a private ops choice.
3. **DOS detector** — an anomalous burst locks the interface rather than letting a loop hammer
   Gmail into a ban.

A 429 is answered with exponential backoff, never a blind resend.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ALLOW = "allow"
DENY_QUOTA = "deny:daily-quota-exhausted"
DENY_BUCKET = "deny:token-bucket-empty"
DENY_LOCKED = "deny:dos-lock-engaged"


class SendRefusedError(RuntimeError):
    """The Gatekeeper refused a send; the reason is the message."""


@dataclass
class TokenBucket:
    """Classic token bucket over a monotonic clock supplied by the caller."""

    rate_per_sec: float
    capacity: float
    tokens: float = field(default=0.0)
    last: float | None = None

    def __post_init__(self) -> None:
        """Start full: the first report of a session must never wait."""
        self.tokens = self.capacity

    def take(self, now: float) -> bool:
        """Refill for the elapsed time and consume one token if there is one."""
        if self.last is not None:
            self.tokens = min(self.capacity, self.tokens + self.rate_per_sec * (now - self.last))
        self.last = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


@dataclass
class Gatekeeper:
    """Quota + bucket + DOS lock. Pure: the clock and the sender are injected."""

    rate_per_sec: float = 0.5
    capacity: float = 5.0
    daily_cap: int = 20
    dos_window_s: float = 10.0
    dos_max_in_window: int = 4
    sent_today: int = 0
    locked: bool = False
    recent: list[float] = field(default_factory=list)
    bucket: TokenBucket | None = None

    def __post_init__(self) -> None:
        """Build the bucket from the configured rate and capacity."""
        if self.bucket is None:
            self.bucket = TokenBucket(self.rate_per_sec, self.capacity)

    @classmethod
    def from_config(cls, requests_per_minute: int, capacity: float, daily_cap: int) -> Gatekeeper:
        """Derive the refill rate from the signed ``requests_per_minute`` block."""
        return cls(
            rate_per_sec=requests_per_minute / 60.0, capacity=capacity, daily_cap=daily_cap
        )

    def check(self, now: float) -> str:
        """Decide without consuming anything (used by dry runs and the console)."""
        if self.locked:
            return DENY_LOCKED
        if self.sent_today >= self.daily_cap:
            return DENY_QUOTA
        return ALLOW

    def admit(self, now: float) -> str:
        """Consume one send allowance or return the refusal reason."""
        verdict = self.check(now)
        if verdict != ALLOW:
            return verdict
        if not self.bucket.take(now):
            return DENY_BUCKET
        self.recent = [t for t in self.recent if now - t <= self.dos_window_s]
        self.recent.append(now)
        if len(self.recent) > self.dos_max_in_window:
            self.locked = True
            return DENY_LOCKED
        self.sent_today += 1
        return ALLOW

    def backoff_delays(self, retries: int, base: float) -> list[float]:
        """Exponential backoff for 429s: base, 2·base, 4·base … (never a blind resend)."""
        return [base * (2**attempt) for attempt in range(retries)]

    def note_rate_limited(self) -> None:
        """A 429 costs the allowance we just spent — the send did not happen."""
        self.sent_today = max(0, self.sent_today - 1)
