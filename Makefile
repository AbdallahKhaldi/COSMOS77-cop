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

# Two-process gate: launch this repo's peer and ../COSMOS77-thief's peer on localhost,
# complete one handshake + one committed turn each, exit 0. Real from Phase 5 (net layer);
# until then it fails honestly instead of lying green.
smoke:
	@echo "smoke: handshake + one committed turn vs ../COSMOS77-thief over localhost."
	@echo "smoke: the net layer lands in Phase 5 — failing honestly until then."
	@exit 2

# Orphaned peers keep playing sub-games for you ("killing a shell does not kill what it
# spawned" — playbook §7.17). Free our port between attempts.
kill:
	-@lsof -ti tcp:$(COP_PORT) | xargs kill 2>/dev/null; true
	@echo "kill: freed tcp:$(COP_PORT)"
