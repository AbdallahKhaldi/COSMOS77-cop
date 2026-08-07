#!/usr/bin/env python3
"""Sync the vendored ``protocol/`` package cop -> thief byte-exact (playbook §3).

The canonical direction is always cop -> thief. Run from either repo; prints the tree hash both
sides must share. The pytest ``test_sync_identity.py`` asserts the equality on every run.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path


def tree_hash(pkg: Path) -> str:
    """SHA-256 over the sorted relative names + bytes of every .py file under *pkg*."""
    digest = hashlib.sha256()
    for path in sorted(pkg.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    """Copy cop's protocol package over thief's and print both tree hashes."""
    workspace = Path(__file__).resolve().parents[2]
    src = workspace / "COSMOS77-cop" / "src" / "cosmos77_cop" / "protocol"
    dst = workspace / "COSMOS77-thief" / "src" / "cosmos77_thief" / "protocol"
    if not src.is_dir() or not dst.parent.is_dir():
        print(f"missing tree: {src} or {dst.parent}", file=sys.stderr)
        return 2
    for stale in dst.glob("*.py"):
        stale.unlink()
    dst.mkdir(exist_ok=True)
    for path in sorted(src.glob("*.py")):
        shutil.copy2(path, dst / path.name)
    a, b = tree_hash(src), tree_hash(dst)
    print(f"cop   protocol tree {a}")
    print(f"thief protocol tree {b}")
    print("IDENTICAL" if a == b else "DRIFT — investigate immediately")
    return 0 if a == b else 1


if __name__ == "__main__":
    sys.exit(main())
