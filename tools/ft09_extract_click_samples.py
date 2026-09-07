"""Build ft09 click samples from fixtures and induce a transition program.

Offline (no API): synthesize (before, click, after) by applying seated
transition operators to live fixtures, then run induce_transition.

Usage:
  python tools/ft09_extract_click_samples.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive.maskflip.flip_block import FlipBlockParam, step as flip_step
from longquan.interactive.maskflip.grid import as_plane
from longquan.interactive.maskflip.induce import induce_transition
from longquan.interactive.maskflip.xor_north import XorNorthParam, step as north_step
from longquan.interactive.maskflip.xor_plus import XorPlusParam, step as plus_step

OUT_SAMPLES = ROOT / "tests" / "fixtures" / "ft09_click_samples.json"
OUT_PROG = ROOT / "tests" / "fixtures" / "ft09_induced_transition.json"
L5 = ROOT / "tests" / "fixtures" / "ft09_l5_frame_live.json"
L6 = ROOT / "tests" / "fixtures" / "ft09_l6_frame_live.json"


def _load(path: Path) -> np.ndarray:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return as_plane(raw["frame"] if isinstance(raw, dict) else raw)


def _pack(g: np.ndarray) -> list:
    return np.asarray(g).tolist()


def build_samples() -> list[dict]:
    g5 = _load(L5)
    g6 = _load(L6)
    samples = []

    # L5 solid 14→15
    ax, ay = 14, 12
    after = flip_step(g5, (ax + 3, ay + 3), FlipBlockParam(14, 15, origin=(ax, ay)))
    samples.append({
        "id": "l5_solid_14_15",
        "level": 5,
        "before": _pack(g5),
        "action": [ax + 3, ay + 3],
        "after": _pack(after),
        "role": "train",
    })

    # L5 solid reverse on a fresh copy of flipped? use another solid
    ax, ay = 30, 4
    after = flip_step(g5, (ax + 3, ay + 3), FlipBlockParam(14, 15, origin=(ax, ay)))
    samples.append({
        "id": "l5_solid_holdout",
        "level": 5,
        "before": _pack(g5),
        "action": [ax + 3, ay + 3],
        "after": _pack(after),
        "role": "holdout",
    })

    # L5 checker plus (full arms)
    cx, cy = 22, 12
    after = plus_step(g5, (cx + 3, cy + 3), XorPlusParam(14, 15, origin=(cx, cy)))
    samples.append({
        "id": "l5_checker_plus",
        "level": 5,
        "before": _pack(g5),
        "action": [cx + 3, cy + 3],
        "after": _pack(after),
        "role": "train",
    })

    # L5 checker with glyph-skipped south arm
    cx, cy = 22, 28
    after = plus_step(g5, (cx + 3, cy + 3), XorPlusParam(14, 15, origin=(cx, cy)))
    samples.append({
        "id": "l5_checker_skip_glyph",
        "level": 5,
        "before": _pack(g5),
        "action": [cx + 3, cy + 3],
        "after": _pack(after),
        "role": "train",
    })

    # L6 self-only
    after = north_step(g6, (7, 9), XorNorthParam(11, 14, origin=(4, 6), family="pip"))
    samples.append({
        "id": "l6_north_self_only",
        "level": 6,
        "before": _pack(g6),
        "action": [7, 9],
        "after": _pack(after),
        "role": "train",
    })

    # L6 self+north
    after = north_step(g6, (7, 17), XorNorthParam(11, 14, origin=(4, 14), family="pip"))
    samples.append({
        "id": "l6_north_couple",
        "level": 6,
        "before": _pack(g6),
        "action": [7, 17],
        "after": _pack(after),
        "role": "holdout",
    })
    return samples


def main() -> int:
    samples = build_samples()
    meta = []
    for s in samples:
        meta.append({
            "id": s["id"],
            "level": s["level"],
            "action": s["action"],
            "role": s["role"],
            "before_shape": [64, 64],
            "after_shape": [64, 64],
        })
    OUT_SAMPLES.write_text(json.dumps({"samples": meta, "n": len(samples)}, indent=2), encoding="utf-8")
    # Full samples (large) for induce / tests
    full_path = ROOT / "tests" / "fixtures" / "ft09_click_samples_full.json"
    full_path.write_text(json.dumps(samples), encoding="utf-8")
    print("wrote", OUT_SAMPLES, "and", full_path)

    # Induce per-level and a joint branch program on L5 only
    def to_tuples(rows):
        return [
            (np.asarray(s["before"], dtype=np.int16), tuple(s["action"]),
             np.asarray(s["after"], dtype=np.int16))
            for s in rows
        ]

    l5_train = [s for s in samples if s["level"] == 5 and s["role"] == "train"]
    l5_hold = [s for s in samples if s["level"] == 5 and s["role"] == "holdout"]
    prog5 = induce_transition(to_tuples(l5_train), holdout=to_tuples(l5_hold))
    print("L5 induced:", None if prog5 is None else (prog5.kind, prog5.complexity))

    l6_train = [s for s in samples if s["level"] == 6 and s["role"] == "train"]
    l6_hold = [s for s in samples if s["level"] == 6 and s["role"] == "holdout"]
    prog6 = induce_transition(to_tuples(l6_train), holdout=to_tuples(l6_hold))
    print("L6 induced:", None if prog6 is None else (prog6.kind, prog6.complexity))

    payload = {
        "l5": None if prog5 is None else {
            "kind": prog5.kind,
            "complexity": prog5.complexity,
            "params": _serialize_params(prog5),
            "train_ok": prog5.satisfies(to_tuples(l5_train)),
            "holdout_ok": prog5.satisfies(to_tuples(l5_hold)),
        },
        "l6": None if prog6 is None else {
            "kind": prog6.kind,
            "complexity": prog6.complexity,
            "params": _serialize_params(prog6),
            "train_ok": prog6.satisfies(to_tuples(l6_train)),
            "holdout_ok": prog6.satisfies(to_tuples(l6_hold)),
        },
    }
    OUT_PROG.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("wrote", OUT_PROG)
    ok = (
        payload["l5"] and payload["l5"]["holdout_ok"]
        and payload["l6"] and payload["l6"]["holdout_ok"]
    )
    return 0 if ok else 1


def _serialize_params(prog) -> dict:
    out = {"kind": prog.kind}
    if prog.kind == "branch_appearance":
        out["color_a"] = prog.params["color_a"]
        out["color_b"] = prog.params["color_b"]
    elif "param" in prog.params:
        p = prog.params["param"]
        out["color_a"] = p.color_a
        out["color_b"] = p.color_b
        if hasattr(p, "family"):
            out["family"] = p.family
        if hasattr(p, "gap"):
            out["gap"] = p.gap
    return out


if __name__ == "__main__":
    raise SystemExit(main())
