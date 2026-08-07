"""Recipient gating — the league address is STRUCTURALLY unreachable unless doubly armed.

Rules 32/35 pay a counted report; rules 37-38 make an *uncounted* game dressed as counted
project-fatal. So the lecturer's address is never a value this code can reach by accident: it
exists only behind :func:`recipients_for`, which demands the config flag AND the CLI flag
together, and refuses to arm on a run that could not deliver.
"""

from __future__ import annotations

from dataclasses import dataclass

LEAGUE_ADDRESS = "rmisegal+uoh26finalgame@gmail.com"
FRIENDLY_INBOXES = ("abdallahkh12@icloud.com", "natortasneem@gmail.com")


class ArmingError(RuntimeError):
    """A send was requested in a posture that must not be able to reach the lecturer."""


@dataclass(frozen=True)
class Posture:
    """How this run is armed. ``counted`` requires BOTH switches — never one."""

    config_counted: bool
    cli_counted: bool

    @property
    def counted(self) -> bool:
        """True only when the config file AND the command line agree."""
        return self.config_counted and self.cli_counted

    @property
    def label(self) -> str:
        """What to write into the artifacts' league block."""
        return "counted" if self.counted else "friendly"


def recipients_for(posture: Posture) -> tuple[str, ...]:
    """The ONLY function that can produce the league address."""
    if posture.counted:
        return (LEAGUE_ADDRESS,)
    return FRIENDLY_INBOXES


def assert_deliverable(posture: Posture, *, has_credentials: bool, settled: bool) -> None:
    """An armed counted run refuses to start if it could not deliver its report."""
    if not posture.counted:
        if posture.cli_counted or posture.config_counted:
            raise ArmingError(
                "half-armed: counted requires BOTH config counted=true AND --counted; "
                "refusing to run in an ambiguous posture"
            )
        return
    if not has_credentials:
        raise ArmingError("counted run cannot deliver its report: no Gmail credentials present")
    if not settled:
        raise ArmingError("counted run has an unsettled window: nothing may be sent (rule 35)")


def is_league_address(address: str) -> bool:
    """True for the lecturer's automated-report alias."""
    return address.strip().lower() == LEAGUE_ADDRESS
