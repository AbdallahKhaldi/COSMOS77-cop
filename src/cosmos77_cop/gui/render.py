"""Dependency-free SVG rendering of the live view and the replay stamp.

The Tk windows are the interactive article; this module draws the SAME render model to a file so
the submission always carries reproducible images (and CI can assert on them) without needing a
display, a font stack or an image library.
"""

from __future__ import annotations

from pathlib import Path

from .model import LOCKED, LiveView

CELL = 56
PAD = 18
SIDEBAR = 300
INK = "#101418"
GRID = "#c8ced6"
BARRIER = "#2b3440"
SELF = "#1d7f5f"
BELIEF = "#c02b30"
SCENT = "#3a6ea5"


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _text(
    x: int, y: int, body: str, size: int = 13, fill: str = INK, weight: str = "normal"
) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Helvetica,Arial,sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{_esc(body)}</text>'
    )


def _cell_xy(cell: tuple[int, int]) -> tuple[int, int]:
    return PAD + cell[1] * CELL, PAD + cell[0] * CELL


def _board_parts(view: LiveView) -> list[str]:
    parts: list[str] = []
    for cell, value in sorted(view.perceived_scent.items()):
        if value <= 0:
            continue
        x, y = _cell_xy(cell)
        opacity = min(0.55, 0.12 + value * 0.5)
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{SCENT}" '
                     f'opacity="{opacity:.3f}"/>')
    peak = max(view.posterior.values()) if view.posterior else 0.0
    for cell, prob in sorted(view.posterior.items()):
        if prob <= 0 or peak <= 0:
            continue
        x, y = _cell_xy(cell)
        opacity = min(0.85, 0.10 + 0.75 * (prob / peak))
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{BELIEF}" '
                     f'opacity="{opacity:.3f}"/>')
    for cell in sorted(view.barriers):
        x, y = _cell_xy(cell)
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{BARRIER}"/>')
    for row in range(view.grid_size + 1):
        pos = PAD + row * CELL
        span = view.grid_size * CELL
        parts.append(f'<line x1="{PAD}" y1="{pos}" x2="{PAD + span}" y2="{pos}" stroke="{GRID}"/>')
        parts.append(f'<line x1="{pos}" y1="{PAD}" x2="{pos}" y2="{PAD + span}" stroke="{GRID}"/>')
    x, y = _cell_xy(view.self_pos)
    cx, cy = x + CELL // 2, y + CELL // 2
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{CELL // 3}" fill="{SELF}"/>')
    parts.append(_text(x + CELL // 2 - 10, y + CELL // 2 + 5, "US", 13, "#ffffff", "bold"))
    return parts


def live_svg(view: LiveView) -> str:
    """Render *view* as a standalone SVG document."""
    span = view.grid_size * CELL
    width, height = PAD * 2 + span + SIDEBAR, PAD * 2 + span + 74
    left = PAD * 2 + span
    banner_fill = "#7a8290" if view.banner == LOCKED else "#1d7f5f"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#fbfcfd"/>',
        *_board_parts(view),
        f'<rect x="{left}" y="{PAD}" width="{SIDEBAR - PAD}" height="34" rx="6" '
        f'fill="{banner_fill}"/>',
        _text(left + 14, PAD + 23, view.banner, 16, "#ffffff", "bold"),
        _text(left, PAD + 62, f"role: {view.role}   sub-game {view.sub_game}   step {view.step}"),
        _text(left, PAD + 84, f"our cell: {view.self_pos}   barriers left: {view.barriers_left}"),
        _text(left, PAD + 106, f"tracking: {view.confidence}"),
    ]
    peak = view.belief_peak
    if peak is not None:
        parts.append(_text(left, PAD + 128, f"belief peak: {peak[0]} p={peak[1]:.2f}", 13, BELIEF))
    parts.append(_text(left, PAD + 158, "hints received", 13, "#5a6472", "bold"))
    for index, hint in enumerate(view.hints[-5:]):
        clipped = hint if len(hint) <= 34 else hint[:33] + "…"
        parts.append(_text(left, PAD + 180 + index * 20, f"· {clipped}", 12))
    for index, line in enumerate(_wrap(view.caption, 58)):
        parts.append(_text(PAD, PAD + span + 24 + index * 18, line, 12, "#5a6472"))
    if view.note:
        parts.append(_text(left, height - PAD, view.note, 12, "#5a6472"))
    parts.append("</svg>")
    return "\n".join(parts)


def _wrap(text: str, width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines


def write_live_svg(view: LiveView, path: str | Path) -> Path:
    """Write *view* to *path* as SVG and return the path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(live_svg(view), encoding="utf-8")
    return target
