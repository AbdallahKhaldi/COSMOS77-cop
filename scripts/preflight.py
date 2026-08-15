#!/usr/bin/env python3
"""The pre-submission checklist, run as code instead of trusted as intention (book §11.5).

Every box the machine can decide, it decides; the rest are printed as HUMAN items so nothing is
quietly assumed. Exit 0 only when no mechanical check failed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = next(p for p in (REPO / "src").iterdir() if p.is_dir())
SECRET_NAMES = ("credentials.json", "token.json", "token.pickle", ".env", "TEAM.env.md")
GITIGNORE_MUST = (".env", "credentials.json", "token.json", "runs/", "config/peer.toml")
README_MUST = (
    "Dec-POMDP",
    "docs/img/live_belief_exact.svg",
    "docs/img/replay_verified.svg",
    "COSMOS77-thief" if PKG.name.endswith("cop") else "COSMOS77-cop",
    "docs/DECISIONS.md",
)

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> bool:
    """Record one mechanical verdict."""
    results.append((ok, label))
    return ok


def tracked_files() -> list[str]:
    """Every path git actually tracks in this repo."""
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=False
    )
    return out.stdout.splitlines()


def main() -> int:
    """Run every mechanical check and print the human-only remainder."""
    tracked = tracked_files()
    leaked = [f for f in tracked if Path(f).name in SECRET_NAMES]
    check(not leaked, f"no secret file is tracked in git (found: {leaked or 'none'})")

    ignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    missing = [p for p in GITIGNORE_MUST if p not in ignore]
    check(not missing, f".gitignore covers the secret patterns (missing: {missing or 'none'})")

    long_files = [
        str(p.relative_to(REPO))
        for p in list(PKG.rglob("*.py")) + list((REPO / "scripts").glob("*.py"))
        if len(p.read_text(encoding="utf-8").splitlines()) > 150
    ]
    check(not long_files, f"every .py is <=150 lines (over: {long_files or 'none'})")

    for name in ("PLAN.md", "TODO.md", "README.md", "LICENSE"):
        check((REPO / name).exists(), f"{name} present")
    prds = sorted((REPO / "PRD").glob("PRD-*.md"))
    check(len(prds) == 7, f"seven PRDs present (found {len(prds)})")
    check((REPO / "docs" / "DECISIONS.md").exists(), "docs/DECISIONS.md present")
    check((REPO / "artifacts" / "league_ledger.json").exists(), "rule-52 ledger committed")

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    absent = [token for token in README_MUST if token not in readme]
    check(not absent, f"README carries the graded sections (missing: {absent or 'none'})")
    shots = ("live_belief_exact", "live_belief_degraded", "replay_verified", "replay_tampered")
    for image in shots:
        check((REPO / "docs" / "img" / f"{image}.svg").exists(), f"screenshot {image} exists")

    sync = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "sync_protocol.py")],
        capture_output=True, text=True, check=False,
    )
    check("IDENTICAL" in sync.stdout, "vendored protocol/ trees are byte-identical across repos")

    kit = REPO.parent / "kit" / "verify_vectors.py"
    if kit.exists():
        out = subprocess.run(
            [sys.executable, str(kit)], cwd=kit.parent, capture_output=True, text=True, check=False
        )
        check("ALL VECTORS PASS" in out.stdout, "community kit vectors pass")

    tag = subprocess.run(["git", "rev-list", "-n1", "v1.0-submission"],
                         cwd=REPO, capture_output=True, text=True, check=False)
    head = subprocess.run(["git", "rev-parse", "HEAD"],
                          cwd=REPO, capture_output=True, text=True, check=False)
    check(
        tag.returncode != 0 or tag.stdout.strip() == head.stdout.strip(),
        "v1.0-submission tag absent or AT HEAD (a stale tag would submit old code — "
        "the six-key consensus bug lived exactly there)",
    )

    print(f"\n  Pre-submission checklist — {PKG.name}\n")
    for ok, label in results:
        print(f"  [{'x' if ok else ' '}] {label}")
    print("\n  HUMAN-ONLY items (not decidable here):")
    for item in (
        "both repos public or shared with rmisegal@gmail.com, invite ACCEPTED",
        "annotated tag v1.0-submission CREATED FRESH AT THE FINAL COMMIT and pushed in "
        "both repos (a mechanical check below refuses a stale one)",
        "at least 2 counted games vs different teams, settled and reported by BOTH sides",
        "Railway arena answers 200 /health and 406 on /cop/mcp + /thief/mcp + /mcp; "
        "a cross-machine F1 handshake succeeded",
        "each member submitted the filled PDF separately in Moodle",
    ):
        print(f"  [ ] {item}")
    failed = [label for ok, label in results if not ok]
    print(f"\n  {len(results) - len(failed)}/{len(results)} mechanical checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
