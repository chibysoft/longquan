"""vc33 L3 clear: Y-align accents to gaps using pad map; handle pad46 coupling."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import (  # noqa: E402
    FIXTURE_L3_CLEAR,
    FIXTURE_L4,
    Sess,
    body_ndiff,
    enter_l3,
    gaps_on_beams,
    pads_sorted,
    plane,
    small_sprites,
    summarize,
)

OUT = ROOT / "tests" / "fixtures" / "vc33_l3_clear_hunt.json"


def pairs(g):
    gaps = {gp["color"]: gp for gp in gaps_on_beams(g)}
    out = []
    for s in small_sprites(g):
        if not s["accent"]:
            continue
        ac = s["accent"]["color"]
        gp = gaps.get(ac)
        if not gp:
            continue
        out.append({
            "c": ac,
            "acc_y": s["accent"]["y0"],
            "gap_y": gp["y0"],
            "dy": s["accent"]["y0"] - gp["y0"],
            "aligned": s["accent"]["y0"] == gp["y0"],
            "acc": s["accent"],
            "gap": gp,
        })
    return out


def click_x(sess, g, x0):
    pad = next(p for p in pads_sorted(g) if p["x0"] == x0)
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    d = sess.click(*xy)
    return d, plane(d["frame"]), list(xy)


def measure_pad(sess, g, x0):
    """One-step effect from current g without restore (mutates!). Don't use."""
    raise NotImplementedError


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        ent = enter_l3(sess)
        d, g = ent["data"], ent["frame"]
        steps = []
        print("start", pairs(g))

        # Controls (x0):
        # 14: 12=-y, 16=+y
        # 15: 38=-y, 34=+y
        # 11: 46=+y (also 15=-y); need find 11=-y
        # env: 24,28; noop:50 at start

        def pick_action(g):
            ps = pairs(g)
            byc = {p["c"]: p for p in ps}
            # Prefer moving a misaligned sprite without harming aligned ones
            # Score candidates
            cands = []
            for x0, desc in (
                (12, "14-y"),
                (16, "14+y"),
                (34, "15+y"),
                (38, "15-y"),
                (46, "11+y/15-y"),
                (24, "env24"),
                (28, "env28"),
                (50, "p50"),
            ):
                cands.append((x0, desc))
            # We can't simulate offline; choose by heuristic:
            acts = []
            if 14 in byc and not byc[14]["aligned"]:
                acts.append(12 if byc[14]["dy"] > 0 else 16)
            if 15 in byc and 11 in byc:
                # dual pad useful if both need: 15 wants -y (dy>0) and 11 wants +y (dy<0)
                if byc[15]["dy"] > 0 and byc[11]["dy"] < 0:
                    acts.append(46)
                elif not byc[15]["aligned"]:
                    acts.append(38 if byc[15]["dy"] > 0 else 34)
                elif not byc[11]["aligned"]:
                    acts.append(46)  # may disturb 15; try anyway
            elif 15 in byc and not byc[15]["aligned"]:
                acts.append(38 if byc[15]["dy"] > 0 else 34)
            elif 11 in byc and not byc[11]["aligned"]:
                acts.append(46)
            # unique preserve order
            seen = set()
            ordered = []
            for a in acts:
                if a not in seen:
                    seen.add(a)
                    ordered.append(a)
            return ordered

        stuck_n = 0
        for i in range(50):
            lv = int(d.get("levels_completed") or 0)
            ps = pairs(g)
            print(f"s{i} lv={lv}", [(p["c"], p["acc_y"], p["gap_y"], p["aligned"]) for p in ps])
            if lv >= 3:
                break
            if all(p["aligned"] for p in ps):
                print("all aligned — try env / any pad")
                for x0 in (24, 28, 50, 46, 12, 38):
                    g0 = g
                    d, g, xy = click_x(sess, g, x0)
                    steps.append({"i": i, "xy": xy, "x0": x0, "why": "post-align",
                                  "body": body_ndiff(g0, g), "levels": int(d.get("levels_completed") or 0),
                                  "pairs": pairs(g)})
                    print("  post", x0, "body", steps[-1]["body"], "lv", steps[-1]["levels"])
                    if int(d.get("levels_completed") or 0) >= 3:
                        break
                break

            ordered = pick_action(g)
            if not ordered:
                print("no actions")
                break
            moved = False
            for x0 in ordered:
                g0 = g
                ps0 = pairs(g)
                d, g, xy = click_x(sess, g, x0)
                bd = body_ndiff(g0, g)
                ps1 = pairs(g)
                steps.append({
                    "i": i,
                    "xy": xy,
                    "x0": x0,
                    "body": bd,
                    "levels": int(d.get("levels_completed") or 0),
                    "before": [(p["c"], p["acc_y"], p["aligned"]) for p in ps0],
                    "after": [(p["c"], p["acc_y"], p["aligned"]) for p in ps1],
                })
                print("  click", x0, "body", bd, "after", steps[-1]["after"], "lv", steps[-1]["levels"])
                if int(d.get("levels_completed") or 0) >= 3:
                    moved = True
                    break
                if bd > 0:
                    moved = True
                    break
            if not moved:
                stuck_n += 1
                if stuck_n > 2:
                    print("stuck")
                    break
            else:
                stuck_n = 0
            if int(d.get("levels_completed") or 0) >= 3:
                break

        out["steps"] = steps
        out["cleared"] = int(d.get("levels_completed") or 0) >= 3
        out["final_pairs"] = pairs(g)
        out["final"] = summarize(g)
        print("CLEARED", out["cleared"], "lv", d.get("levels_completed"), out["final_pairs"])

        if out["cleared"]:
            FIXTURE_L3_CLEAR.write_text(
                json.dumps(
                    {
                        "game_id": sess.game_id,
                        "meta": {
                            "levels_completed": d.get("levels_completed"),
                            "state": d.get("state"),
                            "available_actions": d.get("available_actions"),
                            "win_levels": d.get("win_levels"),
                        },
                        "steps": steps,
                        "summary": summarize(g),
                        "frame": g.tolist(),
                    },
                    indent=2,
                    default=float,
                ),
                encoding="utf-8",
            )
            stale = g
            d4 = sess.action("ACTION1")
            g4 = plane(d4["frame"])
            diff = int(np.sum(stale != g4))
            print("L4 sync", diff)
            FIXTURE_L4.write_text(
                json.dumps(
                    {
                        "game_id": sess.game_id,
                        "meta": {
                            "levels_completed": d4.get("levels_completed"),
                            "state": d4.get("state"),
                            "available_actions": d4.get("available_actions"),
                            "win_levels": d4.get("win_levels"),
                        },
                        "sync": {"action": "ACTION1", "pixel_diff_from_stale": diff},
                        "summary": summarize(g4),
                        "frame": g4.tolist(),
                    },
                    indent=2,
                    default=float,
                ),
                encoding="utf-8",
            )
            print("saved", FIXTURE_L3_CLEAR, FIXTURE_L4)
    finally:
        sess.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("cleared") else 1


if __name__ == "__main__":
    raise SystemExit(main())
