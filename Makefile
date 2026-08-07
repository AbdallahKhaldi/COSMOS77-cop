# COSMOS77-cop — gates and process hygiene (playbook Phase 0).
# Port default mirrors the future config/peer.toml; override: make kill COP_PORT=9001
COP_PORT ?= 8801

.PHONY: sync test lint smoke kill

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

# Two-process gate: this repo's peer + ../COSMOS77-thief's peer over real localhost HTTP,
# full handshake + one committed turn each (no in-play reveal — nonces stay secret).
smoke:
	uv run python scripts/smoke.py

# Orphaned peers keep playing sub-games for you ("killing a shell does not kill what it
# spawned" — playbook §7.17). Free our port between attempts.
kill:
	-@lsof -ti tcp:$(COP_PORT) | xargs kill 2>/dev/null; true
	@echo "kill: freed tcp:$(COP_PORT)"
