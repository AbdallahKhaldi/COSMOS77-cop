"""Scent pipeline wiring: deposit-then-decay traces, gating, wire forms, receiver decay."""

import json
from pathlib import Path

from cosmos77_cop.engine.config import from_dict
from cosmos77_cop.orchestrator.scentflow import MULTIPLICATIVE, ScentFlow

REPO = Path(__file__).resolve().parents[2]


def cfg(**pheromone_overrides):
    raw = json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8"))
    raw["pheromones"].update(pheromone_overrides)
    return from_dict(raw)


def test_first_emission_is_deposit_then_decay():
    flow = ScentFlow(cfg())
    wire = flow.step_emit((3, 3))
    assert wire["3,3"] == 0.8
    assert wire["3,4"] == 0.5
    assert wire["1,1"] == 0.2


def test_trail_accumulates_by_max_and_keeps_decaying():
    flow = ScentFlow(cfg())
    flow.step_emit((3, 3))
    wire = flow.step_emit((3, 4))
    assert wire["3,4"] == 0.8
    assert wire["3,3"] == 0.7
    assert wire["1,1"] == 0.1
    wire3 = flow.step_emit((3, 5))
    assert wire3["3,5"] == 0.8
    assert wire3["3,3"] == 0.6


def test_argmax_of_wire_is_always_the_emitter_cell():
    flow = ScentFlow(cfg())
    path = [(3, 3), (3, 4), (4, 4), (4, 3), (4, 3)]
    for pos in path:
        wire = flow.step_emit(pos)
        best = max(wire, key=lambda k: wire[k])
        assert best == f"{pos[0]},{pos[1]}"


def test_min_center_gating_suppresses_emission():
    flow = ScentFlow(cfg(pheromone_min_center_intensity=0.95))
    flow.trail = {"2,2": 0.5}
    wire = flow.step_emit((3, 3))
    assert "3,3" not in wire
    assert wire["2,2"] == 0.4


def test_multiplicative_model_transmits_empty_but_never_drops_the_key():
    flow = ScentFlow(cfg(), model=MULTIPLICATIVE)
    assert flow.step_emit((3, 3)) == {}


def test_received_copy_decays_receiver_side():
    flow = ScentFlow(cfg())
    flow.observe({"2,2": 0.9, "2,3": 0.6})
    flow.step_received_decay()
    assert flow.received == {"2,2": 0.8, "2,3": 0.5}
    flow.observe({})
    assert flow.received == {"2,2": 0.8, "2,3": 0.5}
    flow.observe({"4,4": 0.9})
    assert flow.received == {"4,4": 0.9}
