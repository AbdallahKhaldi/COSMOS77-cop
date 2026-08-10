"""Which hint author this process ACTUALLY runs with — resolved once, declared honestly.

The declared ``llm_model`` rides the sealed step-0 record and the pre-game declaration, and rules
37-38 make a false declaration project-fatal. So the id is never a constant: it is derived from
the private peer config AND the presence of a key, and a run that falls back to the zero-token
template pool declares exactly that. Naming a model we never call is the failure this prevents.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..hints.gemini import load_env_key

TEMPLATE = "template"
GEMINI = "gemini"


@dataclass(frozen=True)
class HintSetup:
    """The provider/model/key triple this series runs on."""

    provider: str
    model: str
    api_key: str | None
    timeout_s: float

    @property
    def live(self) -> bool:
        """Whether a real client may be constructed: configured for Gemini AND actually keyed."""
        return self.provider == GEMINI and bool(self.api_key)

    @property
    def declared_model(self) -> str:
        """The model id we may truthfully declare — never one this run cannot call."""
        return self.model if self.live else TEMPLATE


def hint_setup(peer_cfg: object, env_path: str | Path = ".env") -> HintSetup:
    """Resolve the hint author for one series from the private peer config and the local key."""
    return HintSetup(
        provider=peer_cfg.trash_provider,
        model=peer_cfg.trash_model,
        api_key=load_env_key(env_path),
        timeout_s=peer_cfg.hint_timeout_s,
    )
