"""vc33 L3 clear v3: strict env↔move alternate per sprite; restore 15 after 46."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

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
    out = {}
    for s in small_sprites(g):
        if not s["accent"]:
            continue
        ac = s["accent"]["color"]
        gp = gaps.get(ac)
        if not gp:
            continue
        out[ac] = {
            "acc_y": s["accent"]["y0"],
            "gap_y": gp["y0"],
            "dy": s["accent"]["y0"] - gp["y0"],
            "aligned": s["accent"]["y0"] == gp["y0"],
        }
    return out


def click_x(sess, g, x0):
    pads = [p for p in pads_sorted(g) if p["x0"] == x0]
    if not pads:
        raise RuntimeError(f"no pad x0={x0}")
    pad = pads[0]
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    try:
        d = sess.click(*xy)
    except requests.HTTPError as e:
        return None, g, list(xy), str(e)
    return d, plane(d["frame"]), list(xy), None


def step(sess, d, g, x0, why, steps):
    g0 = g
    ps0 = pairs(g)
    d2, g2, xy, err = click_x(sess, g, x0)
    if err or d2 is None:
        steps.append({"xy": xy, "x0": x0, "why": why, "error": err})
        print("  ERR", x0, err)
        return d, g, False
    bd = body_ndiff(g0, g2)
    ps1 = pairs(g2)
    entry = {
        "xy": xy,
        "x0": x0,
        "why": why,
        "body": bd,
        "levels": int(d2.get("levels_completed") or 0),
        "state": d2.get("state"),
        "after": {c: (p["acc_y"], p["aligned"]) for c, p in ps1.items()},
    }
    steps.append(entry)
    print(f"  {why} x{x0} body={bd} lv={entry['levels']}", entry["after"])
    return d2, g2, bd > 0 or entry["levels"] >= 3


def restore_15(sess, d, g, steps):
    """If 15 not aligned, nudge with 34/38 toward gap."""
    for _ in range(8):
        ps = pairs(g)
        if 15 not in ps or ps[15]["aligned"]:
            return d, g
        x0 = 38 if ps[15]["dy"] > 0 else 34
        d, g, ok = step(sess, d, g, x0, "restore15", steps)
        if int(d.get("levels_completed") or 0) >= 3:
            return d, g
        if not ok:
            d, g, _ = step(sess, d, g, 24, "env-r15", steps)
            d, g, ok = step(sess, d, g, x0, "restore15", steps)
            if not ok:
                return d, g
    return d, g


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

        env_toggle = 0
        for i in range(80):
            lv = int(d.get("levels_completed") or 0)
            ps = pairs(g)
            print(f"=== {i} lv={lv}", {c: (p["acc_y"], p["gap_y"], p["aligned"]) for c, p in ps.items()})
            if lv >= 3:
                break
            if d.get("state") == "GAME_OVER":
                print("GAME_OVER")
                break

            if all(p["aligned"] for p in ps.values()):
                print("ALL ALIGNED — probe taps")
                for x0 in (24, 28, 50, 12, 38, 46):
                    d, g, _ = step(sess, d, g, x0, "post", steps)
                    if int(d.get("levels_completed") or 0) >= 3:
                        break
                break

            progressed = False

            # --- 14: alternate env + pad12/16 ---
            if 14 in ps and not ps[14]["aligned"]:
                want = 12 if ps[14]["dy"] > 0 else 16
                d, g, ok = step(sess, d, g, want, "14", steps)
                if int(d.get("levels_completed") or 0) >= 3:
                    break
                if not ok:
                    env = 24 if env_toggle % 2 == 0 else 28
                    env_toggle += 1
                    d, g, _ = step(sess, d, g, env, "env14", steps)
                    d, g, ok = step(sess, d, g, want, "14", steps)
                if ok:
                    progressed = True

            # --- 15: dedicated pads, with env if blocked ---
            if int(d.get("levels_completed") or 0) >= 3:
                break
            ps = pairs(g)
            if 15 in ps and not ps[15]["aligned"]:
                want = 38 if ps[15]["dy"] > 0 else 34
                d, g, ok = step(sess, d, g, want, "15", steps)
                if int(d.get("levels_completed") or 0) >= 3:
                    break
                if not ok:
                    d, g, _ = step(sess, d, g, 24, "env15", steps)
                    d, g, ok = step(sess, d, g, want, "15", steps)
                if ok:
                    progressed = True

            # --- 11: use 46, then restore 15 ---
            if int(d.get("levels_completed") or 0) >= 3:
                break
            ps = pairs(g)
            if 11 in ps and not ps[11]["aligned"]:
                # only +y needed at start (dy<0)
                if ps[11]["dy"] < 0:
                    d, g, ok = step(sess, d, g, 46, "11", steps)
                    if int(d.get("levels_completed") or 0) >= 3:
                        break
                    if not ok:
                        d, g, _ = step(sess, d, g, 28, "env11", steps)
                        d, g, ok = step(sess, d, g, 46, "11", steps)
                    if ok:
                        progressed = True
                        d, g = restore_15(sess, d, g, steps)
                else:
                    # need 11 -y — try 50
                    d, g, ok = step(sess, d, g, 50, "11-y?", steps)
                    if ok:
                        progressed = True

            if not progressed:
                print("no progress", pairs(g))
                # last resort: spam envs
                d, g, _ = step(sess, d, g, 24, "env?", steps)
                d, g, _ = step(sess, d, g, 28, "env?", steps)
                if steps[-1]["body"] == 0 and steps[-2]["body"] == 0:
                    break

        out["steps"] = steps
        out["cleared"] = int(d.get("levels_completed") or 0) >= 3
        out["final"] = pairs(g)
        print("CLEARED", out["cleared"], "lv", d.get("levels_completed"), out["final"])

        if out["cleared"]:
            FIXTURE_L3_CLEAR.write_text(
                json.dumps({
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
                }, indent=2, default=float),
                encoding="utf-8",
            )
            stale = g
            d4 = sess.action("ACTION1")
            g4 = plane(d4["frame"])
            diff = int(np.sum(stale != g4))
            FIXTURE_L4.write_text(
                json.dumps({
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
                }, indent=2, default=float),
                encoding="utf-8",
            )
            print("saved clear+L4", diff)
    finally:
        sess.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("cleared") else 1


if __name__ == "__main__":
    raise SystemExit(main())
