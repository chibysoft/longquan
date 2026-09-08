"""vc33 L3 clear v4: proven pad roles; 14 uses ONLY env24↔pad12."""
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
    pad = next(p for p in pads_sorted(g) if p["x0"] == x0)
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    try:
        d = sess.click(*xy)
    except requests.HTTPError as e:
        return None, g, list(xy), f"HTTP {e}"
    return d, plane(d["frame"]), list(xy), None


def do(sess, d, g, x0, why, steps):
    g0 = g
    d2, g2, xy, err = click_x(sess, g, x0)
    if err or d2 is None:
        steps.append({"x0": x0, "xy": xy, "why": why, "error": err})
        print(" ERR", why, x0, err)
        return d, g, False
    bd = body_ndiff(g0, g2)
    ps = pairs(g2)
    steps.append({
        "x0": x0, "xy": xy, "why": why, "body": bd,
        "levels": int(d2.get("levels_completed") or 0),
        "state": d2.get("state"),
        "after": {c: (p["acc_y"], p["aligned"]) for c, p in ps.items()},
    })
    print(f" {why:10} x{x0} body={bd} lv={steps[-1]['levels']}", steps[-1]["after"])
    return d2, g2, bd > 0


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

        # Phase A: raise 15 with pad38 until aligned (or blocked→skip to couple)
        for _ in range(12):
            ps = pairs(g)
            if ps.get(15, {}).get("aligned"):
                break
            if ps[15]["dy"] <= 0:
                break
            d, g, ok = do(sess, d, g, 38, "15-up", steps)
            if not ok:
                break

        # Phase B: pad46 until 11 aligned; restore 15 with 34 after each if broken
        for _ in range(20):
            ps = pairs(g)
            if ps.get(11, {}).get("aligned"):
                break
            if ps[11]["dy"] >= 0:
                break
            d, g, ok = do(sess, d, g, 46, "11-down", steps)
            if int(d.get("levels_completed") or 0) >= 3:
                break
            # restore 15 if needed
            for __ in range(6):
                ps = pairs(g)
                if ps.get(15, {}).get("aligned"):
                    break
                x0 = 38 if ps[15]["dy"] > 0 else 34
                d, g, ok2 = do(sess, d, g, x0, "15-fix", steps)
                if not ok2:
                    break
            if not ok:
                break

        print("after B", pairs(g))

        # Phase C: 14 ONLY env24 then pad12, repeat
        for _ in range(20):
            ps = pairs(g)
            print("C", ps)
            if int(d.get("levels_completed") or 0) >= 3:
                break
            if d.get("state") == "GAME_OVER":
                print("GAME_OVER")
                break
            if ps.get(14, {}).get("aligned"):
                break
            # try pad12 first
            d, g, ok = do(sess, d, g, 12, "14-up", steps)
            if int(d.get("levels_completed") or 0) >= 3:
                break
            if ok:
                continue
            # unblock with env24 ONLY
            d, g, _ = do(sess, d, g, 24, "env24", steps)
            if d.get("state") == "GAME_OVER":
                print("GAME_OVER after env24")
                break
            d, g, ok = do(sess, d, g, 12, "14-up", steps)
            if not ok:
                print("14 still blocked after env24")
                # try env28 once as last resort then 12
                d, g, _ = do(sess, d, g, 28, "env28", steps)
                d, g, ok = do(sess, d, g, 12, "14-up", steps)
                if not ok:
                    break

        print("after C", pairs(g), "lv", d.get("levels_completed"))

        # Phase D: if all aligned, tap; if 14 aligned and others ok, levels should tick on last align
        ps = pairs(g)
        if all(p["aligned"] for p in ps.values()) and int(d.get("levels_completed") or 0) < 3:
            for x0 in (24, 12, 38, 46, 28, 50):
                d, g, _ = do(sess, d, g, x0, "post", steps)
                if int(d.get("levels_completed") or 0) >= 3:
                    break

        out["steps"] = steps
        out["cleared"] = int(d.get("levels_completed") or 0) >= 3
        out["final"] = pairs(g)
        print("CLEARED", out["cleared"], out["final"])

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
                    "policy": "15:pad38; 11:pad46+restore15; 14:env24↔pad12; clear=all accent y==gap y",
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
            print("saved L3 clear + L4", diff)
    finally:
        sess.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("cleared") else 1


if __name__ == "__main__":
    raise SystemExit(main())
