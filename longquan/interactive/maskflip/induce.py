"""Induce a click→frame transition program from samples (iterative deepening)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

import numpy as np

from longquan.interactive.maskflip import flip_block, xor_north, xor_plus
from longquan.interactive.maskflip.grid import as_plane, is_checker_block, is_pip_block, resolve_click_block

Sample = Tuple[Any, Tuple[int, int], Any]  # before, (x,y), after


@dataclass
class TransitionProgram:
    """Executable transition program.

    kind:
      - 'flip_block' | 'xor_plus' | 'xor_north'  (single op)
      - 'branch_appearance' : if checker→xor_plus elif pip→xor_north else flip_block
    """
    kind: str
    params: dict
    complexity: int

    def predict(self, frame, xy) -> np.ndarray:
        g = as_plane(frame)
        x, y = int(xy[0]), int(xy[1])
        if self.kind == "flip_block":
            return flip_block.step(g, (x, y), self.params["param"])
        if self.kind == "xor_plus":
            return xor_plus.step(g, (x, y), self.params["param"])
        if self.kind == "xor_north":
            return xor_north.step(g, (x, y), self.params["param"])
        if self.kind == "branch_appearance":
            ca = self.params["color_a"]
            cb = self.params["color_b"]
            hit = resolve_click_block(g, x, y, prefer="any", color_a=ca, color_b=cb)
            if hit is not None and is_checker_block(g, hit[0], hit[1], ca, cb):
                return xor_plus.step(g, (x, y), self.params["xor_plus"])
            if hit is not None and is_pip_block(g, hit[0], hit[1], ca, cb):
                return xor_north.step(g, (x, y), self.params["xor_north"])
            return flip_block.step(g, (x, y), self.params["flip_block"])
        raise ValueError(self.kind)

    def satisfies(self, samples: Sequence[Sample]) -> bool:
        for before, xy, after in samples:
            if not np.array_equal(as_plane(self.predict(before, xy)), as_plane(after)):
                return False
        return True


def _candidates_complexity1(samples: Sequence[Sample]) -> List[TransitionProgram]:
    progs: List[TransitionProgram] = []
    for before, _xy, after in samples:
        for mod, kind in (
            (flip_block, "flip_block"),
            (xor_plus, "xor_plus"),
            (xor_north, "xor_north"),
        ):
            for param in mod.backproject(before, after):
                # Prefer unbound origin so the program generalizes across clicks.
                if getattr(param, "origin", None) is not None:
                    continue
                progs.append(TransitionProgram(
                    kind=kind,
                    params={"param": param},
                    complexity=1,
                ))
    # Dedup by repr
    seen = set()
    uniq = []
    for p in progs:
        key = (p.kind, repr(p.params))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def _candidates_complexity2(samples: Sequence[Sample]) -> List[TransitionProgram]:
    """Branch by block appearance; share one color pair across ops."""
    pairs = set()
    for before, _xy, after in samples:
        for mod in (flip_block, xor_plus, xor_north):
            for param in mod.backproject(before, after):
                pairs.add((param.color_a, param.color_b))
                if hasattr(param, "family"):
                    pairs.add((param.color_a, param.color_b))
    progs = []
    for ca, cb in pairs:
        fb = flip_block.FlipBlockParam(color_a=ca, color_b=cb, origin=None)
        xp = xor_plus.XorPlusParam(color_a=ca, color_b=cb, origin=None)
        xn = xor_north.XorNorthParam(color_a=ca, color_b=cb, origin=None, family="pip")
        progs.append(TransitionProgram(
            kind="branch_appearance",
            params={
                "color_a": ca,
                "color_b": cb,
                "flip_block": fb,
                "xor_plus": xp,
                "xor_north": xn,
            },
            complexity=2,
        ))
    return progs


def induce_transition(
    samples: Sequence[Sample],
    *,
    max_complexity: int = 2,
    holdout: Sequence[Sample] | None = None,
) -> Optional[TransitionProgram]:
    """Return the lowest-complexity program that fits all train samples.

    If holdout is provided, also require holdout satisfaction (for selection).
    """
    if not samples:
        return None
    for cplx in range(1, max_complexity + 1):
        if cplx == 1:
            cands = _candidates_complexity1(samples)
        else:
            cands = _candidates_complexity2(samples)
        # Prefer fewer params bits: unbound origin already preferred.
        for prog in cands:
            if not prog.satisfies(samples):
                continue
            if holdout is not None and not prog.satisfies(holdout):
                continue
            return prog
    return None
