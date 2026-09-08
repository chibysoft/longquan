"""vc33 L3 clear v2: env-unblock + per-color Y align; avoid breaking aligned sprites."""
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
    body_changes,
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
        })
    return {p["c"]: p for p in out}


def click_x(sess, g, x0):
    pad = next(p for p in pads_sorted(g) if p["x0"] == x0)
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    d = sess.click(*xy)
    return d, plane(d["frame"]), list(xy)


def try_move(sess, g, d, x0):
    g0 = g
    ps0 = pairs(g)
    d2, g2, xy = click_x(sess, g, x0)
    return {
        "xy": xy,
        "x0": x0,
        "body": body_ndiff(g0, g2),
        "changes": body_changes(g0, g2),
        "levels": int(d2.get("levels_completed") or 0),
        "before": ps0,
        "after": pairs(g2),
        "data": d2,
        "frame": g2,
    }


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

        # Pad roles:
        # 12:14-y  16:14+y  38:15-y  34:15+y  46:11+y & 15-y  24/28:env  50:?
        for i in range(60):
            lv = int(d.get("levels_completed") or 0)
            ps = pairs(g)
            print(f"--- s{i} lv={lv}", {c: (p["acc_y"], p["gap_y"], p["aligned"]) for c, p in ps.items()})
            if lv >= 3:
                break
            if all(p["aligned"] for p in ps.values()):
                print("ALL Y ALIGNED")
                for x0 in (24, 28, 50, 12, 38, 46, 34, 16):
                    r = try_move(sess, g, d, x0)
                    steps.append({k: v for k, v in r.items() if k not in ("data", "frame", "before", "after", "changes")})
                    steps[-1]["after"] = {c: (p["acc_y"], p["aligned"]) for c, p in r["after"].items()}
                    d, g = r["data"], r["frame"]
                    print("  tap", x0, "body", r["body"], "lv", r["levels"])
                    if r["levels"] >= 3:
                        break
                break

            # Plan one useful click
            chose = None
            # 1) If 14 needs -y, try 12; if noop, env then retry
            if 14 in ps and not ps[14]["aligned"]:
                want = 12 if ps[14]["dy"] > 0 else 16
                r = try_move(sess, g, d, want)
                if r["body"] > 0 and r["after"].get(14, {}).get("acc_y") != ps[14]["acc_y"]:
                    chose = r
                else:
                    # unblock
                    for env in (24, 28):
                        e = try_move(sess, g, d, env)
                        steps.append({
                            "xy": e["xy"], "x0": env, "body": e["body"], "levels": e["levels"],
                            "why": "env-for-14",
                            "after": {c: (p["acc_y"], p["aligned"]) for c, p in e["after"].items()},
                        })
                        d, g = e["data"], e["frame"]
                        print("  env", env, "body", e["body"])
                        if e["levels"] >= 3:
                            chose = e
                            break
                    if chose is None and int(d.get("levels_completed") or 0) < 3:
                        r2 = try_move(sess, g, d, want)
                        if r2["body"] > 0:
                            chose = r2
                        else:
                            # record failed
                            steps.append({"xy": r["xy"], "x0": want, "body": 0, "levels": r["levels"], "why": "14-blocked"})

            # 2) Move 15 with dedicated pads (38/34), not 46
            if chose is None and 15 in ps and not ps[15]["aligned"]:
                want = 38 if ps[15]["dy"] > 0 else 34
                r = try_move(sess, g, d, want)
                if r["body"] > 0 and r["after"].get(15, {}).get("acc_y") != ps[15]["acc_y"]:
                    chose = r
                else:
                    for env in (24, 28):
                        e = try_move(sess, g, d, env)
                        steps.append({
                            "xy": e["xy"], "x0": env, "body": e["body"], "levels": e["levels"],
                            "why": "env-for-15",
                            "after": {c: (p["acc_y"], p["aligned"]) for c, p in e["after"].items()},
                        })
                        d, g = e["data"], e["frame"]
                        print("  env", env, "body", e["body"])
                    r2 = try_move(sess, g, d, want)
                    if r2["body"] > 0:
                        chose = r2

            # 3) Move 11 with 46 only if 15 already aligned OR 15 also benefits (dy>0)
            if chose is None and 11 in ps and not ps[11]["aligned"]:
                # 46 moves 11+y and 15-y
                ok_couple = ps.get(15, {}).get("aligned") is False and ps.get(15, {}).get("dy", 0) > 0
                fifteen_ok = ps.get(15, {}).get("aligned") is True
                # If 15 aligned, 46 would break it — only use if 15 can be restored, or try env/50 first
                if ok_couple or not fifteen_ok:
                    if fifteen_ok:
                        # try pad50 as possible 11-only
                        for alt in (50, 46):
                            r = try_move(sess, g, d, alt)
                            if r["body"] == 0:
                                steps.append({"xy": r["xy"], "x0": alt, "body": 0, "why": "11-noop"})
                                continue
                            # accept if 11 moved closer and 15 stayed aligned or dy improved net
                            b11, a11 = ps[11]["dy"], r["after"][11]["dy"]
                            b15 = abs(ps[15]["dy"]) if 15 in ps else 0
                            a15 = abs(r["after"][15]["dy"]) if 15 in r["after"] else 0
                            if abs(a11) < abs(b11) and a15 <= b15 + 0.1:
                                chose = r
                                break
                            # revert by re-enter+replay — too heavy; if broke 15, keep and fix later
                            if abs(a11) < abs(b11):
                                chose = r
                                break
                    else:
                        r = try_move(sess, g, d, 46)
                        if r["body"] > 0:
                            chose = r
                if chose is None:
                    # unblock then 46
                    for env in (28, 24):
                        e = try_move(sess, g, d, env)
                        steps.append({
                            "xy": e["xy"], "x0": env, "body": e["body"], "levels": e["levels"],
                            "why": "env-for-11",
                            "after": {c: (p["acc_y"], p["aligned"]) for c, p in e["after"].items()},
                        })
                        d, g = e["data"], e["frame"]
                    r = try_move(sess, g, d, 46)
                    if r["body"] > 0:
                        chose = r

            if chose is None:
                print("no move found", ps)
                break

            steps.append({
                "xy": chose["xy"],
                "x0": chose["x0"],
                "body": chose["body"],
                "levels": chose["levels"],
                "why": "move",
                "after": {c: (p["acc_y"], p["aligned"]) for c, p in chose["after"].items()},
            })
            d, g = chose["data"], chose["frame"]
            print("  move", chose["x0"], "body", chose["body"], "after", steps[-1]["after"], "lv", chose["levels"])
            if chose["levels"] >= 3:
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
            print("saved fixtures L3 clear + L4", diff)
    finally:
        sess.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("cleared") else 1


if __name__ == "__main__":
    raise SystemExit(main())
