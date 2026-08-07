"""Belief map: delta start, physics-constrained diffusion, conditioning, normalization."""

import pytest

from cosmos77_cop.belief.bayes import BeliefMap
from cosmos77_cop.engine.board import Board


def test_starts_as_delta_at_known_start():
    m = BeliefMap(Board(7), (3, 3))
    assert m.argmax() == ((3, 3), 1.0)


def test_diffusion_spreads_only_one_legal_step():
    m = BeliefMap(Board(7), (3, 3))
    m.diffuse()
    support = set(m.posterior())
    assert support == {(3, 3), (2, 3), (4, 3), (3, 2), (3, 4)}
    assert sum(m.posterior().values()) == pytest.approx(1.0)


def test_diffusion_respects_barriers():
    b = Board(7)
    b.add_barrier((2, 3))
    m = BeliefMap(b, (3, 3))
    m.diffuse()
    assert (2, 3) not in m.posterior()


def test_condition_not_at_removes_and_renormalizes():
    m = BeliefMap(Board(7), (3, 3))
    m.diffuse()
    m.condition_not_at((3, 3))
    post = m.posterior()
    assert (3, 3) not in post
    assert sum(post.values()) == pytest.approx(1.0)


def test_condition_region_shifts_mass():
    m = BeliefMap(Board(7), (3, 3))
    m.diffuse()
    m.condition_region({(2, 3)}, 5.0)
    assert m.argmax()[0] == (2, 3)
    m.condition_region({(2, 3)}, 0.01)
    assert m.argmax()[0] != (2, 3)


def test_all_mass_removed_recovers_uniform():
    m = BeliefMap(Board(7), (3, 3))
    m.condition_not_at((3, 3))
    post = m.posterior()
    assert len(post) == 49
    assert sum(post.values()) == pytest.approx(1.0)
