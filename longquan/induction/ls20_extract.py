"""ls20 bridge: rendered frame -> induction State (the real "probe -> data" link).

This is the divide the induction engine exists to cross: probe code currently
computes `gate_u`, `armed_only`, `stamp_c9`, `has_plus` INLINE (see
tools/ls20_l4_arming_probe._gate_walk / _has_plus_marker) and dumps them as
debug dicts / log strings. The engine needs them as a *State* dict so a
Transition (before --action--> after) can be built and fed to Inducer.

The features here are the SAME ones the probes compute, consolidated into one
definition so probes and engine cannot drift apart. They are all closed-book:
derived only from the rendered plane via `longquan.interactive.ls20` + `match`.

Feature -> derivation (mirrors evidence.FEATURES):
  armed_only_nonempty (bool) : walk_a - walk_u is nonempty
  unlocked_stamp      (bool) : stamp bbox has no color-9 glyph (stamp_c9 == 0)
  has_plus            (bool) : a compact plus-like 0/1 marker exists
  ui                  (int)  : color-11 pixels on the bottom step bar
  total_c9            (int)  : playfield color-9 pixel count (y < 54)
  stamp_c9            (int)  : color-9 pixels inside the stamp bbox

TARGET (evidence.TARGET = "gate_u"):
  gate_u              (bool) : the stamp-gate cell is walkable *unarmed*

WARNING — measured on the lingjingsolo recording (2026-09-11):
  `gate_u` is DEGENERATE as an induction target. In ls20 the "gate" cell is
  armed-only by design (you must be armed to stamp), so `gate_u` flips
  False->True exactly once per level — at the frame `levels_completed`
  increments, i.e. level COMPLETION, not a mid-level "unlock" sub-event. It
  then resets False at the next level's first frame. See
  tools/ls20_induct_l4.py for the evidence, and treat the *real* unlock signal
  (legend flip / ring-crush) as a MISSING feature — route 2.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor

# Reuse the proven probe threshold (tools/ls20_seated_clear_full.PALETTE_Y).
PALETTE_Y = 54


def _plane(frame) -> "Any":
    return ls20._plane(frame)


def _overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> int:
    ox0, oy0 = max(a[0], b[0]), max(a[1], b[1])
    ox1, oy1 = min(a[2], b[2]), min(a[3], b[3])
    if ox0 <= ox1 and oy0 <= oy1:
        return (ox1 - ox0 + 1) * (oy1 - oy0 + 1)
    return 0


def stamp_bbox(frame) -> Optional[Tuple[int, int, int, int]]:
    st = ls20.init(frame)
    return next((g.shape for g in st.goals if g.id == "ls20-stamp"), None)


def gate_cell(frame) -> Optional[Tuple[int, int]]:
    """First armed-only cell whose mover footprint overlaps the stamp (ov>=10)."""
    off = ls20.grid_offset(frame)
    wa = ls20.build_walkable(frame, off, armed=True)
    stamp = stamp_bbox(frame)
    if stamp is None:
        return None
    for c in sorted(wa):
        if _overlap(mover_bbox_from_cursor(c, off), stamp) >= 10:
            return c
    return None


def armed_only_cells(frame) -> "frozenset":
    """Cells walkable armed but not unarmed (wa - wu)."""
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    wa = ls20.build_walkable(frame, off, armed=True)
    return wa - wu


def stamp_c9(frame) -> int:
    """Color-9 pixel count inside the stamp bbox (-1 if no stamp)."""
    stamp = stamp_bbox(frame)
    if stamp is None:
        return -1
    x0, y0, x1, y1 = stamp
    g = _plane(frame)
    return int((g[y0 : y1 + 1, x0 : x1 + 1] == 9).sum())


def total_c9(frame) -> int:
    """Playfield color-9 pixel count (rows above the bottom palette)."""
    g = _plane(frame)
    return int((g[:PALETTE_Y] == 9).sum())


def has_plus(frame) -> bool:
    """True iff a compact plus-like 0/1 blob exists (mirrors probe helper)."""
    g = _plane(frame)
    H, W = g.shape
    for y in range(H - 2):
        if y >= PALETTE_Y:
            break
        for x in range(W - 2):
            patch = g[y : y + 3, x : x + 3]
            core = {(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)}
            vals = [int(patch[dy, dx]) for dx, dy in core]
            if all(v in (0, 1) for v in vals) and int(patch[1, 1]) in (0, 1):
                return True
    return False


def gate_u(frame) -> Optional[bool]:
    """Whether the stamp-gate cell is walkable unarmed (None if no gate)."""
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    gate = gate_cell(frame)
    if gate is None:
        return None
    return gate in wu


def legend_c12(frame) -> int:
    """Color-12 pixel count in the bottom chrome (y>=54) = the legend glyph.

    The legend glyph (lower-left, ~24px) is color12 while the level's gate is
    LOCKED and flips to color9 on the unlock event (E7). The mover never enters
    y>=54 (that is UI chrome), so any color12 there is the legend.
    """
    g = _plane(frame)
    return int((g[54:] == 12).sum())


def legend_locked(frame) -> bool:
    return legend_c12(frame) > 0


def legend_unlocked(frame) -> bool:
    """Inverse of legend_locked — usable as an induction TARGET (unlock event)."""
    return not legend_locked(frame)


def extract_state(frame) -> Dict[str, Any]:
    """Frame -> induction State. Keys match evidence.FEATURES + TARGET.

    `legend_unlocked` is the *unlock-event* target (falsy->truthy at the crush);
    `gate_u` is the *completion* target (degenerate, see docs).
    """
    sc9 = stamp_c9(frame)
    return {
        "armed_only_nonempty": bool(armed_only_cells(frame)),
        "unlocked_stamp": sc9 == 0,
        "has_plus": has_plus(frame),
        "legend_locked": legend_locked(frame),
        "ui": ls20.ui_energy(frame),
        "total_c9": total_c9(frame),
        "stamp_c9": sc9,
        # targets
        "gate_u": gate_u(frame),
        "legend_unlocked": legend_unlocked(frame),
    }


__all__ = [
    "extract_state",
    "stamp_bbox", "gate_cell", "armed_only_cells",
    "stamp_c9", "total_c9", "has_plus", "gate_u",
    "legend_c12", "legend_locked", "legend_unlocked",
    "PALETTE_Y",
]
