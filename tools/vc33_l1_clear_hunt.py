"""vc33 L1 clear hunt: sweep pad clicks, watch levels_completed only.

tags=["vc33_recon"]. No canned clear table. Derive clicks from frame pads/sprite.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402
from tools.vc33_recon_probe import (  # noqa: E402
    TAGS,
    body_changes,
    body_ndiff,
    c9_blocks,
    meta,
    plane,
    sprite_cc,
    _headers,
)

OUT = ROOT / "tests" / "fixtures" / "vc33_l1_clear_hunt.json"


def beam_gap(g: np.ndarray):
    """Color-11 cells on the y=28..31 beam row band (exclude sprite band)."""
    band = g[28:32]
    ys, xs = np.where(band == 11)
    if len(xs) == 0:
        return None
    return {
        "n": int(len(xs)),
        "x0": int(xs.min()),
        "x1": int(xs.max()),
        "cx": float(xs.mean()),
        "y0": int(ys.min() + 28),
        "y1": int(ys.max() + 28),
    }


def c5_span(g: np.ndarray):
    ys, xs = np.where(g == 5)
    if len(xs) == 0:
        return None
    return {
        "n": int(len(xs)),
        "x0": int(xs.min()),
        "x1": int(xs.max()),
        "y0": int(ys.min()),
        "y1": int(ys.max()),
    }


def summarize(g: np.ndarray) -> dict:
    return {
        "sprite": sprite_cc(g),
        "pads": c9_blocks(g),
        "gap": beam_gap(g),
        "c5": c5_span(g),
        "hist": {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))},
    }


class Sess:
    def __init__(self, key: str):
        self.key = key
        self.s = requests.Session()
        self.card_id = None
        self.game_id = None
        self.guid = None

    def open(self):
        r = self.s.post(
            f"{BASE}/api/scorecard/open",
            headers=_headers(self.key, True),
            json={"tags": TAGS},
            timeout=20,
        )
        r.raise_for_status()
        self.card_id = r.json()["card_id"]
        r = self.s.get(f"{BASE}/api/games/vc33", headers=_headers(self.key), timeout=20)
        r.raise_for_status()
        self.game_id = r.json()["game_id"]

    def reset(self):
        r = self.s.post(
            f"{BASE}/api/cmd/RESET",
            headers=_headers(self.key, True),
            json={"card_id": self.card_id, "game_id": self.game_id},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self.guid = data["guid"]
        return data

    def click(self, x, y):
        r = self.s.post(
            f"{BASE}/api/cmd/ACTION6",
            headers=_headers(self.key, True),
            json={"game_id": self.game_id, "guid": self.guid, "x": int(x), "y": int(y)},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self.guid = data.get("guid", self.guid)
        return data

    def close(self):
        if not self.card_id:
            return
        try:
            self.s.post(
                f"{BASE}/api/scorecard/close",
                headers=_headers(self.key, True),
                json={"card_id": self.card_id},
                timeout=15,
            )
        except Exception:
            pass


def pad_xy(pads, which: str):
    # which: upper/lower by y order
    pads = sorted(pads, key=lambda b: b["y0"])
    b = pads[0] if which == "upper" else pads[1]
    return int(round(b["cx"])), int(round(b["cy"]))


def sweep(sess: Sess, direction: str, max_steps: int = 20) -> dict:
    d = sess.reset()
    g = plane(d["frame"])
    pads = c9_blocks(g)
    which = "upper" if direction == "right" else "lower"
    xy = pad_xy(pads, which)
    timeline = [{"step": 0, "action": "RESET", **summarize(g), "levels": 0}]
    print(f"=== sweep {direction} via {which} {xy}")
    for step in range(1, max_steps + 1):
        # re-locate pads each step (derive from frame, not canned)
        pads = c9_blocks(g)
        if len(pads) < 2:
            timeline.append({"step": step, "error": "pads_missing", "sum": summarize(g)})
            break
        xy = pad_xy(pads, which)
        d2 = sess.click(*xy)
        g2 = plane(d2["frame"])
        lv = int(d2.get("levels_completed") or 0)
        entry = {
            "step": step,
            "click": list(xy),
            "pad": which,
            "body_ndiff": body_ndiff(g, g2),
            "changes": body_changes(g, g2),
            **summarize(g2),
            "levels": lv,
            "state": d2.get("state"),
        }
        # alignment metrics
        sp, gap = entry["sprite"], entry["gap"]
        if sp and gap:
            entry["align_cx"] = round(sp["cx"] - gap["cx"], 3)
            entry["align_x0"] = sp["x0"] - gap["x0"]
            entry["sprite_under_gap"] = sp["x0"] <= gap["cx"] <= sp["x1"]
        timeline.append(entry)
        print(
            f"  s{step} lv={lv} body={entry['body_ndiff']} "
            f"sp={sp} gap={gap} align_cx={entry.get('align_cx')}"
        )
        g = g2
        if lv > 0:
            print("LEVEL UP")
            break
        if entry["body_ndiff"] == 0:
            print("stuck")
            break
    return {"direction": direction, "timeline": timeline, "cleared": timeline[-1].get("levels", 0) > 0}


def after_position_clicks(sess: Sess, left_steps: int) -> dict:
    """Move left N times then try clicking gap/beam/sprite/other."""
    d = sess.reset()
    g = plane(d["frame"])
    for _ in range(left_steps):
        pads = c9_blocks(g)
        xy = pad_xy(pads, "lower")
        d = sess.click(*xy)
        g = plane(d["frame"])
        if int(d.get("levels_completed") or 0) > 0:
            return {"preclear": True, "levels": d.get("levels_completed"), "sum": summarize(g)}
    sp = sprite_cc(g)
    gap = beam_gap(g)
    targets = []
    if gap:
        targets.append(("gap", int(round(gap["cx"])), int(round((gap["y0"] + gap["y1"]) / 2))))
    if sp:
        targets.append(("sprite", int(round(sp["cx"])), int(round(sp["cy"]))))
        targets.append(("sprite_top", int(round(sp["cx"])), sp["y0"] - 1))
    targets += [
        ("beam_left", 25, 29),
        ("beam_right", 50, 29),
        ("c5_mid", 45, 29),
        ("above_sprite", int(round(sp["cx"])) if sp else 48, 40),
        ("left_field", 20, 46),
    ]
    # also click both pads once each after parking
    pads = c9_blocks(g)
    for i, p in enumerate(sorted(pads, key=lambda b: b["y0"])):
        targets.append((f"pad{i}", int(round(p["cx"])), int(round(p["cy"]))))

    rows = []
    base = summarize(g)
    print(f"=== after {left_steps} left, parked", base["sprite"], "gap", base["gap"])
    for label, x, y in targets:
        # fresh path each time
        d = sess.reset()
        g = plane(d["frame"])
        for _ in range(left_steps):
            pads = c9_blocks(g)
            d = sess.click(*pad_xy(pads, "lower"))
            g = plane(d["frame"])
            if int(d.get("levels_completed") or 0) > 0:
                return {"preclear": True, "levels": d.get("levels_completed")}
        g_before = g
        d2 = sess.click(x, y)
        g2 = plane(d2["frame"])
        lv = int(d2.get("levels_completed") or 0)
        row = {
            "label": label,
            "xy": [x, y],
            "body_ndiff": body_ndiff(g_before, g2),
            "levels": lv,
            "sprite": sprite_cc(g2),
            "changes": body_changes(g_before, g2),
        }
        rows.append(row)
        print(f"  try {label} {x,y} body={row['body_ndiff']} lv={lv} sp={row['sprite']}")
        if lv > 0:
            break
    return {"left_steps": left_steps, "parked": base, "tries": rows}


def alternate(sess: Sess, pattern: str, steps: int = 12) -> dict:
    """pattern like 'ULUL' or 'LLU' repeated."""
    d = sess.reset()
    g = plane(d["frame"])
    timeline = []
    print(f"=== alternate {pattern}")
    for step in range(steps):
        which = "upper" if pattern[step % len(pattern)] == "U" else "lower"
        pads = c9_blocks(g)
        xy = pad_xy(pads, which)
        d2 = sess.click(*xy)
        g2 = plane(d2["frame"])
        lv = int(d2.get("levels_completed") or 0)
        entry = {
            "step": step + 1,
            "which": which,
            "body_ndiff": body_ndiff(g, g2),
            "sprite": sprite_cc(g2),
            "gap": beam_gap(g2),
            "levels": lv,
        }
        timeline.append(entry)
        print(f"  s{step+1} {which} body={entry['body_ndiff']} sp={entry['sprite']} lv={lv}")
        g = g2
        if lv > 0:
            break
        if entry["body_ndiff"] == 0 and step > 0:
            # allow one noop then stop if consecutive
            pass
    return {"pattern": pattern, "timeline": timeline, "cleared": any(e["levels"] > 0 for e in timeline)}


def left_until_align_then_more(sess: Sess) -> dict:
    """Move left until sprite cx near gap cx, record; continue to left wall."""
    d = sess.reset()
    g = plane(d["frame"])
    rows = []
    print("=== left until past gap")
    for step in range(1, 25):
        pads = c9_blocks(g)
        d2 = sess.click(*pad_xy(pads, "lower"))
        g2 = plane(d2["frame"])
        lv = int(d2.get("levels_completed") or 0)
        sp, gap = sprite_cc(g2), beam_gap(g2)
        row = {
            "step": step,
            "body_ndiff": body_ndiff(g, g2),
            "sprite": sp,
            "gap": gap,
            "align_cx": None if not (sp and gap) else round(sp["cx"] - gap["cx"], 3),
            "levels": lv,
            "c5": c5_span(g2),
        }
        rows.append(row)
        print(f"  s{step} body={row['body_ndiff']} align={row['align_cx']} sp={sp} lv={lv}")
        g = g2
        if lv > 0:
            break
        if row["body_ndiff"] == 0:
            break
    return {"rows": rows, "cleared": any(r["levels"] > 0 for r in rows)}


def main():
    key = _api_key()
    if not key:
        raise RuntimeError("no key")
    sess = Sess(key)
    out = {"game_id": None, "card_id": None, "experiments": {}}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        out["card_id"] = sess.card_id

        out["experiments"]["sweep_right"] = sweep(sess, "right")
        out["experiments"]["sweep_left"] = sweep(sess, "left")
        out["experiments"]["left_align"] = left_until_align_then_more(sess)

        # park near gap (from left_align find best align step) and click extras
        # start cx~49, gap cx~38.5 → need ~3 left steps for align_cx~0
        for n in (2, 3, 4, 5, 6):
            out["experiments"][f"after_left_{n}"] = after_position_clicks(sess, n)

        out["experiments"]["alt_UL"] = alternate(sess, "UL", 10)
        out["experiments"]["alt_LU"] = alternate(sess, "LU", 10)
        out["experiments"]["alt_LLU"] = alternate(sess, "LLU", 12)
        out["experiments"]["alt_UUL"] = alternate(sess, "UUL", 12)

        cleared = []
        for k, v in out["experiments"].items():
            if isinstance(v, dict) and v.get("cleared"):
                cleared.append(k)
            if isinstance(v, dict) and v.get("preclear"):
                cleared.append(k + ":preclear")
            if isinstance(v, dict) and any(
                (t.get("levels") or 0) > 0 for t in v.get("tries", [])
            ):
                cleared.append(k + ":try")
        out["cleared_hits"] = cleared
        print("CLEARED_HITS", cleared)
    finally:
        sess.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("cleared_hits") else 1


if __name__ == "__main__":
    raise SystemExit(main())
