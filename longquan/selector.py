"""Stage 1a: family router — pick reflect / toggle / move from a raw frame.

Geometric solvers (hypotheses/*) and interactive solvers (ls20, maskflip) do not
share a search API. The selector's job is only to rank *families* so the caller
dispatches to the right pipeline:

  reflect  -> perceive + solve_auto (cover/backproject)
  toggle   -> interactive.maskflip (+ GF(2) goal)
  move     -> interactive.ls20 seated clear / move+match

Scores are closed-book heuristics over the rendered plane only.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np

Family = str  # "reflect" | "toggle" | "move"
ScoreRow = Tuple[float, Family]


def _plane(frame) -> np.ndarray:
    a = np.asarray(frame)
    return a[0] if a.ndim == 3 else a


def score_reflect(frame) -> float:
    """Mirror-line games (ar25): a near-full column/row of line-color 10."""
    g = _plane(frame)
    h, w = g.shape
    line_color = 10  # AR25 mirror line (perceive.COLOR_LINE)
    best = 0.0
    for x in range(w):
        col = g[:, x]
        frac = float(np.mean(col == line_color))
        if frac >= 0.7:
            best = max(best, 0.5 + 0.5 * frac)
    for y in range(h):
        row = g[y, :]
        frac = float(np.mean(row == line_color))
        if frac >= 0.7:
            best = max(best, 0.5 + 0.5 * frac)
    return float(min(1.0, best))


def score_toggle(frame) -> float:
    """Click-flip boards (ft09): 6x6 glyph blocks on an 8px-gap lattice."""
    from longquan.interactive.maskflip.grid import BLOCK, GAP, is_glyph_block

    g = _plane(frame)
    h, w = g.shape
    hits = 0
    probes = 0
    # Lattice origins used by ft09 (6 cell + 2 gap = 8 stride).
    for ay in range(0, max(1, h - BLOCK + 1), GAP):
        for ax in range(0, max(1, w - BLOCK + 1), GAP):
            probes += 1
            if is_glyph_block(g, ax, ay):
                hits += 1
    if probes == 0:
        return 0.0
    dens = hits / probes
    if hits == 0:
        return 0.0
    return float(min(1.0, 0.35 + 0.65 * dens))


def score_move(frame) -> float:
    """Cursor-move games (ls20): a color-12 5x2 mover footprint.

    Twin-block mate boards (m0r0) also have color-12 paint — defer to mate
    when ``score_mate`` wins, by keeping this score moderate unless a 5x2
    mover footprint is present.
    """
    try:
        from longquan.interactive import ls20
    except Exception:
        return 0.0
    bb = ls20.locate_mover(frame)
    if bb is None:
        return 0.0
    x0, y0, x1, y1 = bb
    # ls20 mover is 5x2 (w=5,h=2). Broad color-12 paint is not a mover.
    if (x1 - x0 + 1, y1 - y0 + 1) != (5, 2):
        return 0.15
    score = 0.7
    try:
        if ls20.stamp_block(frame) is not None:
            score += 0.15
        if ls20.ui_energy(frame) >= 0:
            score += 0.1
    except Exception:
        pass
    return float(min(1.0, score))


def score_mate(frame) -> float:
    """Twin mirrored blocks (m0r0)."""
    try:
        from longquan.interactive import m0r0
    except Exception:
        return 0.0
    return float(m0r0.score_frame(frame))


_SCORERS = {
    "reflect": score_reflect,
    "toggle": score_toggle,
    "move": score_move,
    "mate": score_mate,
}


def score_families(frame) -> List[ScoreRow]:
    """Return (score, family) pairs sorted by score desc."""
    rows = [(float(_SCORERS[name](frame)), name) for name in _SCORERS]
    rows.sort(key=lambda t: (-t[0], t[1]))
    return rows


def select_family(frame, *, min_score: float = 0.35) -> Family:
    """Top family if above threshold; else 'reflect' as geometric default."""
    rows = score_families(frame)
    if not rows or rows[0][0] < min_score:
        return "reflect"
    return rows[0][1]


def route(frame) -> dict:
    """Dispatch hint for solvers / solve_auto wrappers."""
    rows = score_families(frame)
    family = rows[0][1] if rows and rows[0][0] >= 0.35 else "reflect"
    return {
        "family": family,
        "scores": {name: score for score, name in rows},
        "pipeline": {
            "reflect": "hypotheses.reflect + loop.solve_auto",
            "toggle": "interactive.maskflip",
            "move": "interactive.ls20 (seated clear)",
            "mate": "interactive.m0r0 (mirrored twin blocks)",
        }[family],
    }


__all__ = [
    "score_reflect",
    "score_toggle",
    "score_move",
    "score_families",
    "select_family",
    "route",
]
