"""Confirm L2 clear via O24/+x alternate; grab L3."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import (  # noqa: E402
    FIXTURE_L2_CLEAR,
    FIXTURE_L3,
    Sess,
    aligned,
    body_ndiff,
    c9_blocks,
    enter_l2,
    pick_gap,
    plane,
    sprite_bundle,
    summarize,
)


def click_y(sess, g, y0):
    pad = next(p for p in sorted(c9_blocks(g), key=lambda b: b["y0"]) if p["y0"] == y0)
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    d = sess.click(*xy)
    return d, plane(d["frame"]), list(xy)


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l2(sess)
        d, g = ent["data"], ent["frame"]
        steps = []
        # Policy from hunt: while not clear, click env pad (y=24, no sprite Δ) then +x (y=44).
        # Live re-select by y-order index among pads that match roles measured at L2 start.
        pad_map = {}
        # measure roles once at start
        g_start = g
        for pad in sorted(c9_blocks(g_start), key=lambda b: b["y0"]):
            # fresh enter for each measure
            pass
        # Use hunt result roles by y0 (frame-stable on L2):
        env_y, plus_y = 24, 44
        while int(d.get("levels_completed") or 0) < 2 and len(steps) < 16:
            for y0, role in ((env_y, "env"), (plus_y, "plus")):
                g0 = g
                sp0 = sprite_bundle(g)
                d, g, xy = click_y(sess, g, y0)
                sp1 = sprite_bundle(g)
                entry = {
                    "role": role,
                    "y0": y0,
                    "xy": xy,
                    "body_ndiff": body_ndiff(g0, g),
                    "ddx": None if not (sp0 and sp1) else round(sp1["cx"] - sp0["cx"], 3),
                    "levels": int(d.get("levels_completed") or 0),
                    "aligned": aligned(g),
                    "accent": (sprite_bundle(g) or {}).get("accent"),
                    "gap": pick_gap(g),
                }
                steps.append(entry)
                print(entry["role"], entry["xy"], "ddx", entry["ddx"], "lv", entry["levels"],
                      "aligned", entry["aligned"], "acc", entry["accent"])
                if entry["levels"] >= 2:
                    break
            else:
                continue
            break

        assert int(d.get("levels_completed") or 0) >= 2
        FIXTURE_L2_CLEAR.write_text(
            json.dumps(
                {
                    "game_id": sess.game_id,
                    "meta": {
                        "levels_completed": d.get("levels_completed"),
                        "state": d.get("state"),
                        "available_actions": d.get("available_actions"),
                        "win_levels": d.get("win_levels"),
                    },
                    "policy": "alternate env pad y=24 (3↔0 wall) then +x pad y=44 until accent14 x==gap14 x",
                    "steps": steps,
                    "summary": summarize(g),
                    "frame": g.tolist(),
                },
                indent=2,
                default=float,
            ),
            encoding="utf-8",
        )
        print("saved", FIXTURE_L2_CLEAR, "steps", len(steps))

        stale = g
        d3 = sess.action("ACTION1")
        g3 = plane(d3["frame"])
        diff = int(np.sum(stale != g3))
        print("L3", diff, summarize(g3))
        FIXTURE_L3.write_text(
            json.dumps(
                {
                    "game_id": sess.game_id,
                    "meta": {
                        "levels_completed": d3.get("levels_completed"),
                        "state": d3.get("state"),
                        "available_actions": d3.get("available_actions"),
                        "win_levels": d3.get("win_levels"),
                    },
                    "sync": {"action": "ACTION1", "pixel_diff_from_stale": diff},
                    "summary": summarize(g3),
                    "frame": g3.tolist(),
                },
                indent=2,
                default=float,
            ),
            encoding="utf-8",
        )
        print("saved", FIXTURE_L3)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
