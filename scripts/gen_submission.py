#!/usr/bin/env python3
"""Fill the Moodle submission form from TEAM.env.md and the league ledger.

The template's fields must not be moved or renamed (rule 43), so this does not build a document
from scratch: it emits the exact field/value pairs a human copies in, plus a filled Markdown
rendering to check them against. Self-grade is **code quality only** (rule 55).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEAM_FILE = REPO.parent / "TEAM.env.md"
LEDGER = REPO / "artifacts" / "league_ledger.json"


def read_team(path: Path) -> dict[str, str]:
    """Parse the flat ``key: value`` lines of TEAM.env.md (comments and blocks ignored)."""
    fields: dict[str, str] = {}
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        body = line.split("#", 1)[0].rstrip()
        if not body.strip():
            continue
        match = re.match(r"^(\s*)([A-Za-z0-9_]+):\s*(.*)$", body)
        if not match:
            continue
        indent, key, value = match.groups()
        if not indent:
            section = key if not value else ""
        prefix = f"{section}." if indent and section else ""
        if value:
            fields[f"{prefix}{key}"] = value.strip().strip('"')
    return fields


def ledger_rows(path: Path) -> list[dict[str, object]]:
    """The counted games, newest last."""
    if not path.exists():
        return []
    entries = json.loads(path.read_text(encoding="utf-8")).get("counted_games") or {}
    return [{"opponent": name, **dict(body)} for name, body in sorted(entries.items())]


def render(team: dict[str, str], games: list[dict[str, object]]) -> str:
    """The filled form, ready to copy into the template."""
    lines = [
        "# Moodle submission form — filled values (copy into the template; do not move fields)",
        "",
        f"- Group code: **{team.get('group_id', 'cosmos77')}**",
        f"- Student 1: {team.get('student_1.first_name_en')} "
        f"{team.get('student_1.last_name_en')} — ID {team.get('student_1.id')}",
        f"- Student 2: {team.get('student_2.first_name_en')} "
        f"{team.get('student_2.last_name_en')} — ID {team.get('student_2.id')}",
        f"- Agent email (automated reports): {team.get('agent_gmail')}",
        f"- Cop repository: {team.get('repo_cop')}",
        f"- Thief repository: {team.get('repo_thief')}",
        f"- LLM model: {team.get('llm_model')}",
        f"- Self-grade (CODE QUALITY ONLY, rule 55): **{team.get('self_score', '90')}**",
        f"- Bonus eligibility: **{team.get('bonus_eligibility', 'No')}**",
        "",
        f"## Counted games ({len(games)})",
        "",
        "| # | Opponent | Settled | Won | game_id |",
        "|---|---|---|---|---|",
    ]
    for index, game in enumerate(games, start=1):
        lines.append(
            f"| {index} | {game['opponent']} | {game.get('settled_at', '')} | "
            f"{'yes' if game.get('won') else 'no'} | {game.get('game_id', '')} |"
        )
    if not games:
        lines.append("| — | _no counted game played yet_ | | | |")
    unresolved = sorted(k for k, v in team.items() if "[FILL" in v)
    if unresolved:
        lines += ["", "## STILL MISSING (a human must supply these)", ""]
        lines += [f"- `{key}`" for key in unresolved]
    return "\n".join(lines) + "\n"


def main() -> int:
    """Write the filled form and report anything still missing."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", default=str(TEAM_FILE))
    parser.add_argument("--ledger", default=str(LEDGER))
    parser.add_argument("--out", default=str(REPO / "docs" / "SUBMISSION.md"))
    args = parser.parse_args()
    team_path = Path(args.team)
    if not team_path.exists():
        print(f"gen_submission: {team_path} not found (it lives in the workspace root)")
        return 2
    team = read_team(team_path)
    body = render(team, ledger_rows(Path(args.ledger)))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"gen_submission: wrote {out}")
    if "STILL MISSING" in body:
        print("gen_submission: some fields still need a human — see the file")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
