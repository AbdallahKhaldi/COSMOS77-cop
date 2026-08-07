"""The vendored protocol/ trees must be byte-identical across the two repos (playbook §0.1)."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
SIBLING = REPO_ROOT.parent / (
    "COSMOS77-thief" if REPO_ROOT.name == "COSMOS77-cop" else "COSMOS77-cop"
)


def test_protocol_trees_hash_identical():
    if not SIBLING.is_dir():
        pytest.skip("sibling repo not checked out beside this one")
    sys.path.insert(0, str(SCRIPTS))
    try:
        from sync_protocol import tree_hash
    finally:
        sys.path.pop(0)
    mine = REPO_ROOT / "src" / f"cosmos77_{REPO_ROOT.name.split('-')[1]}" / "protocol"
    theirs = SIBLING / "src" / f"cosmos77_{SIBLING.name.split('-')[1]}" / "protocol"
    assert tree_hash(mine) == tree_hash(theirs)
