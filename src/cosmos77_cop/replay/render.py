"""SVG rendering of one replay step, with the verification stamp (rule 20 evidence)."""

from __future__ import annotations

from pathlib import Path

from ..gui.render import CELL, INK, PAD, SELF, _cell_xy, _text, _wrap
from .verify import VERIFIED, ReplayResult, StepVerdict

OK_GREEN = "#1d7f5f"
BAD_RED = "#c02b30"
TRAIL = "#8fb3d9"


def step_svg(result: ReplayResult, verdict: StepVerdict, grid_size: int = 7) -> str:
    """Render one verified step: the revealed trail so far plus the stamp."""
    span = grid_size * CELL
    width, height = PAD * 2 + span + 340, PAD * 2 + span + 96
    left = PAD * 2 + span
    fill = OK_GREEN if verdict.ok else BAD_RED
    trail = [
        v.payload["position"]
        for v in result.verdicts
        if v.side == verdict.side and v.index <= verdict.index and "position" in v.payload
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#fbfcfd"/>',
    ]
    for cell in trail[:-1]:
        x, y = _cell_xy((int(cell[0]), int(cell[1])))
        parts.append(f'<rect x="{x + 8}" y="{y + 8}" width="{CELL - 16}" height="{CELL - 16}" '
                     f'rx="4" fill="{TRAIL}" opacity="0.55"/>')
    for row in range(grid_size + 1):
        pos = PAD + row * CELL
        parts.append(f'<line x1="{PAD}" y1="{pos}" x2="{PAD + span}" y2="{pos}" stroke="#c8ced6"/>')
        parts.append(f'<line x1="{pos}" y1="{PAD}" x2="{pos}" y2="{PAD + span}" stroke="#c8ced6"/>')
    if trail:
        x, y = _cell_xy((int(trail[-1][0]), int(trail[-1][1])))
        parts.append(
            f'<circle cx="{x + CELL // 2}" cy="{y + CELL // 2}" r="{CELL // 3}" fill="{SELF}"/>'
        )
    counter = f"record {verdict.index + 1}/{len(result.verdicts)} ({verdict.side})"
    parts += [
        f'<rect x="{left}" y="{PAD}" width="300" height="40" rx="6" fill="{fill}"/>',
        _text(left + 14, PAD + 27, verdict.stamp, 18, "#ffffff", "bold"),
        _text(left, PAD + 72, counter),
        _text(left, PAD + 94, f"sealed step {verdict.step}"),
        _text(left, PAD + 124, "declared commit", 12, "#5a6472", "bold"),
        _text(left, PAD + 142, verdict.declared[:32], 11),
        _text(left, PAD + 158, verdict.declared[32:], 11),
        _text(left, PAD + 186, "recomputed from (payload, nonce)", 12, "#5a6472", "bold"),
        _text(left, PAD + 204, verdict.recomputed[:32], 11, INK if verdict.ok else BAD_RED),
        _text(left, PAD + 220, verdict.recomputed[32:], 11, INK if verdict.ok else BAD_RED),
    ]
    note = (
        "Full sealed payload re-hashed with the pinned construction "
        "sha256(canonical_json(payload)|nonce)."
        if verdict.ok
        else "Recomputed digest differs from the declared commit: this log has been altered."
    )
    for index, line in enumerate(_wrap(note, 62)):
        parts.append(_text(PAD, PAD + span + 26 + index * 18, line, 12, "#5a6472"))
    parts.append("</svg>")
    return "\n".join(parts)


def write_step_svg(
    result: ReplayResult, verdict: StepVerdict, path: str | Path, grid_size: int = 7
) -> Path:
    """Write one rendered step to *path*."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(step_svg(result, verdict, grid_size), encoding="utf-8")
    return target


def summary_line(result: ReplayResult) -> str:
    """The one line the CLI prints for a whole log."""
    ok = sum(1 for v in result.verdicts if v.ok)
    total = len(result.verdicts)
    head = VERIFIED if result.clean else f"{result.stamp} ({total - ok} of {total} failed)"
    return f"{Path(result.path).name}: {head} — {ok}/{total} records re-hashed"
