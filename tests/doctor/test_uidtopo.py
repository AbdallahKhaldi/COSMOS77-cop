"""Uid stage (term diff, uid derivation, wrapper detection) + topology stage."""

import copy
import json
from pathlib import Path

from cosmos77_cop.doctor.uidtopo import topology_stage, uid_stage, unwrap_config
from cosmos77_cop.protocol.terms import TERMS_KEYS, terms_from_config

OUR_RAW = json.loads(Path("config/game.json").read_text(encoding="utf-8"))


def write(tmp_path, obj, name="theirs.json"):
    path = tmp_path / name
    path.write_text(json.dumps(obj), encoding="utf-8")
    return str(path)


def test_identical_config_is_green_with_shared_uid(tmp_path):
    stage = uid_stage(write(tmp_path, OUR_RAW), "best2934", our_raw=OUR_RAW, our_gid="cosmos77")
    assert stage.status == "green"
    assert "byte-identical" in stage.finding
    assert stage.detail["game_uid_ours"] == stage.detail["game_uid_theirs"]
    assert stage.detail["config_sha256_ours"] == stage.detail["config_sha256_theirs"]


def test_wrapper_only_difference_is_yellow_with_agreed_between_fix(tmp_path):
    theirs = copy.deepcopy(OUR_RAW)
    theirs["agreed_between"] = ["someone-else"]
    theirs["_note"] = "draft"
    theirs["schema_version"] = "9.9"
    stage = uid_stage(write(tmp_path, theirs), "best2934", our_raw=OUR_RAW, our_gid="cosmos77")
    assert stage.status == "yellow"
    assert "substance identical, wrapper differs" in stage.finding
    assert '"agreed_between": ["best2934", "cosmos77"]' in stage.fix_line
    assert "cannot change the signature or the uid" in stage.fix_line


def test_signed_term_difference_is_red_and_names_the_term(tmp_path):
    theirs = copy.deepcopy(OUR_RAW)
    theirs["pheromones"]["pheromone_decay"] = 0.2
    stage = uid_stage(write(tmp_path, theirs), None, our_raw=OUR_RAW, our_gid="cosmos77")
    assert stage.status == "red"
    assert "decay_per_step: ours=0.1 theirs=0.2" in stage.finding
    assert stage.detail["game_uid_ours"] != stage.detail["game_uid_theirs"]
    assert stage.detail["gid_pair_assumed"] is True


def test_unsigned_section_difference_is_yellow_and_named(tmp_path):
    theirs = copy.deepcopy(OUR_RAW)
    theirs["scoring"]["capture_cop"] = 25
    stage = uid_stage(write(tmp_path, theirs), "g2", our_raw=OUR_RAW, our_gid="cosmos77")
    assert stage.status == "yellow"
    assert "unsigned sections differ: scoring" in stage.finding
    assert stage.detail["game_uid_ours"] == stage.detail["game_uid_theirs"]


def test_wrapped_and_flat_configs_are_unwrapped(tmp_path):
    wrapped = {"schema_version": "x", "config": copy.deepcopy(OUR_RAW)}
    stage = uid_stage(write(tmp_path, wrapped), "g", our_raw=OUR_RAW, our_gid="cosmos77")
    assert stage.status in {"green", "yellow"}  # wrapper differs, substance nested
    assert stage.detail["extracted_via"] == "nested under 'config'"
    flat = terms_from_config(OUR_RAW)
    terms, how = unwrap_config(flat)
    assert how == "flat 14-term file"
    assert set(terms) == set(TERMS_KEYS)


def test_unreadable_and_unrecognizable_configs_are_red(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert uid_stage(str(bad), None, our_raw=OUR_RAW, our_gid="c").status == "red"
    assert uid_stage(str(tmp_path / "absent.json"), None,
                     our_raw=OUR_RAW, our_gid="c").status == "red"
    mystery = write(tmp_path, {"answer": 42}, "mystery.json")
    stage = uid_stage(mystery, None, our_raw=OUR_RAW, our_gid="c")
    assert stage.status == "red"
    assert "flat 14 signed terms" in stage.fix_line


def test_uid_skips_without_a_config():
    stage = uid_stage(None, None, our_raw=OUR_RAW, our_gid="c")
    assert stage.status == "green" and "skipped" in stage.finding


def test_topology_shapes_and_dial_us_urls():
    single = topology_stage(single=True, public_base="https://arena.example/")
    assert single.status == "green"
    assert single.detail["their_shape"] == "single-endpoint-both-roles"
    assert single.detail["dial_us"] == {
        "our_cop_endpoint": "https://arena.example/cop/mcp",
        "our_thief_endpoint": "https://arena.example/thief/mcp",
        "single_url_opponents_dial": "https://arena.example/mcp",
    }
    per_role = topology_stage(single=False, public_base="https://arena.example")
    assert per_role.detail["their_shape"] == "per-role endpoints"
    assert per_role.detail["we_can_dial_them"] and per_role.detail["they_can_dial_us"]
    offline = topology_stage(single=None, public_base="https://arena.example")
    assert "unknown" in offline.detail["their_shape"]
