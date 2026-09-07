"""ft09 L1 click-flip closed-loop probe.

WHY
  User's request: run the full "click-flip" closed loop on ft09 L1 — send ACTION6
  coordinate clicks, record the 9->8 change trajectory after every click, then
  analyze offline whether the trajectory is describable by a reflect primitive
  ("flip colors about some symmetry axis").

  This probe is PURE OBSERVATION + one guided hypothesis test. It does NOT
  hardcode a level->action table (red line 1); it derives WHICH blocks to click
  from the frame's own 0/2 annotation pattern (the 6x6 "instruction" pattern in
  the center of the puzzle region encodes a 3x3 macro-grid of 22/00 bits, which
  we hypothesize marks flip-vs-keep). No engine source, no canned answers.

  Pass criterion is NOT "pixels look right" — it is levels_completed increment
  only (red line 3).

USAGE
  python tools/ft09_click_flip_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, _api_key

GAME = "ft09"
FIXTURE_OUT = ROOT / "tests" / "fixtures" / "ft09_l1_click_flip_trajectory.json"
REPORT_OUT = ROOT / "docs" / "ft09-click-flip-probe.md"


def _headers(key, json_body=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


class Ft09Session:
    def __init__(self, key, base=BASE):
        self.base = base
        self.key = key
        self.s = requests.Session()
        self.card_id = None
        self.game_id = None
        self.guid = None

    def open(self, tags=None, timeout=60):
        r = self.s.post(f"{self.base}/api/scorecard/open",
                        headers=_headers(self.key, True),
                        json={"tags": tags or ["ft09_click_flip"]}, timeout=timeout)
        r.raise_for_status()
        self.card_id = r.json()["card_id"]
        r = self.s.get(f"{self.base}/api/games/{GAME}",
                       headers=_headers(self.key), timeout=timeout)
        r.raise_for_status()
        self.game_id = r.json()["game_id"]

    def reset(self, timeout=60):
        r = self.s.post(f"{self.base}/api/cmd/RESET",
                        headers=_headers(self.key, True),
                        json={"card_id": self.card_id, "game_id": self.game_id},
                        timeout=timeout)
        r.raise_for_status()
        data = r.json()
        self.guid = data["guid"]
        return data

    def click(self, x, y, timeout=60):
        r = self.s.post(f"{self.base}/api/cmd/ACTION6",
                        headers=_headers(self.key, True),
                        json={"game_id": self.game_id, "guid": self.guid,
                              "x": int(x), "y": int(y)}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        self.guid = data.get("guid", self.guid)
        return data

    def action(self, name: str, timeout=60, **kw):
        """Send a raw ACTION* (e.g. ACTION1 sync after level-up)."""
        body = {"game_id": self.game_id, "guid": self.guid, **kw}
        r = self.s.post(f"{self.base}/api/cmd/{name}",
                        headers=_headers(self.key, True),
                        json=body, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        self.guid = data.get("guid", self.guid)
        return data

    def close(self):
        if not self.card_id:
            return
        try:
            self.s.post(f"{self.base}/api/scorecard/close",
                        headers=_headers(self.key, True),
                        json={"card_id": self.card_id}, timeout=30)
        except Exception:
            pass


def _plane(frame) -> np.ndarray:
    a = np.asarray(frame, dtype=np.int8)
    return a[0] if a.ndim == 3 else a


def frame_diff(prev, cur):
    """Return list of (x, y, before, after) for pixels that changed."""
    p, c = _plane(prev), _plane(cur)
    ys, xs = np.where(p != c)
    return [(int(x), int(y), int(p[y, x]), int(c[y, x])) for x, y in zip(xs, ys)]


# The 3x3 puzzle region inside the central frame. Block (r, c) sits at pixel
# top-left (36 + 8*c, 36 + 8*r), 6x6, for r,c in {0,1,2}. Center (1,1) is the
# 0/2 instruction pattern. We derive flips from THAT pattern, not from a table.
FRAME_ORIGIN_X, FRAME_ORIGIN_Y = 36, 36
BLOCK = 6
GAP = 8


def block_center(r, c):
    x0 = FRAME_ORIGIN_X + GAP * c
    y0 = FRAME_ORIGIN_Y + GAP * r
    return x0 + BLOCK // 2, y0 + BLOCK // 2


def read_instruction(frame):
    """Decode the center 3x3 macro-pattern (2x2 cells each) into flip/keep.

    Returns dict {(r,c): 'flip'|'keep'|'fixed'} for the 8 outer positions.
    The instruction sits at (44,44)-(49,49); each macro-cell is 2x2 pixels,
    value 0 -> 'flip' (turn 9->8), 2 -> 'keep' (stay 9), 8 -> fixed center.

    (Verified against the already-completed LEFT 3x3, whose 9/8 layout matches
    its own L pattern exactly under this 0=flip / 2=keep reading.)
    """
    g = _plane(frame)
    macro = {}
    for r in range(3):
        for c in range(3):
            x0 = 44 + 2 * c
            y0 = 44 + 2 * r
            cell = g[y0:y0 + 2, x0:x0 + 2]
            if np.all(cell == 8):
                macro[(r, c)] = "fixed"
            elif np.all(cell == 0):
                macro[(r, c)] = "flip"
            elif np.all(cell == 2):
                macro[(r, c)] = "keep"
            else:
                macro[(r, c)] = "mixed"
    return macro


def main() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = Ft09Session(key)
    trajectory = []
    try:
        sess.open()
        reset = sess.reset()
        frame = reset["frame"]
        lv0 = int(reset.get("levels_completed") or 0)
        print(f"game={sess.game_id} lv0={lv0} "
              f"available_actions={reset.get('available_actions')}")

        instr = read_instruction(frame)
        print("instruction macro (r,c):")
        for r in range(3):
            print("  " + " ".join(f"{instr[(r, c)]:>5}" for c in range(3)))

        # derive clicks: outer positions marked 'flip', in row-major order
        clicks = [(r, c) for r in range(3) for c in range(3)
                  if (r, c) != (1, 1) and instr.get((r, c)) == "flip"]
        print(f"derived clicks (row-major): {clicks}")

        for i, (r, c) in enumerate(clicks, start=1):
            cx, cy = block_center(r, c)
            resp = sess.click(cx, cy)
            nf = resp["frame"]
            lv = int(resp.get("levels_completed") or 0)
            d = frame_diff(frame, nf)
            flips = [t for t in d if t[2] == 9 and t[3] == 8]
            print(f"click {i} block({r},{c})@({cx},{cy}) "
                  f"lv={lv} diff_n={len(d)} nine_to_eight={len(flips)}")
            trajectory.append({
                "step": i,
                "block": (r, c),
                "pixel": (cx, cy),
                "levels_completed": lv,
                "diff": d,
                "nine_to_eight": flips,
            })
            frame = nf
            if lv > lv0:
                print(f"  >>> LEVEL INCREMENT {lv0} -> {lv}")
                break

        print(f"final levels_completed = {trajectory[-1]['levels_completed'] if trajectory else lv0}")

        FIXTURE_OUT.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_OUT.write_text(json.dumps({
            "game_id": sess.game_id,
            "levels_start": lv0,
            "instruction": {f"{r},{c}": v for (r, c), v in instr.items()},
            "clicks": clicks,
            "trajectory": trajectory,
        }, indent=2), encoding="utf-8")
        print(f"saved -> {FIXTURE_OUT}")
        return 0
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
