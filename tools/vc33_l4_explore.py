"""vc33 L4 explore: unblock + hunt +x; then align accent11 to gap11."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_ndiff  # noqa: E402
from tools.vc33_l4_pad_map import (  # noqa: E402
    FIXTURE_L4_CLEAR,
    FIXTURE_L5,
    enter_l4,
    gap11,
    sprite,
    summarize,
)
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "vc33_l4_clear_hunt.json"


def click_x(sess, g, x0):
    pad = next(p for p in pads_sorted(g) if p["x0"] == x0)
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    try:
        d = sess.click(*xy)
    except requests.HTTPError as e:
        return None, g, list(xy), str(e)
    return d, plane(d["frame"]), list(xy), d.get("state")


def dist(g):
    sp, gp = sprite(g), gap11(g)
    if not sp or not sp.get("accent") or not gp:
        return 999
    a = sp["accent"]
    return abs(a["cx"] - gp["cx"]) + abs(a["cy"] - gp["cy"])


def aligned(g):
    return summarize(g)["aligned"]


def probe_all_pads(sess, d, g, path_xy, steps_log):
    """From L4 start replay path, test each pad once; return effects. Expensive."""
    effects = []
    pads = pads_sorted(g)  # current pad list for x0s
    x0s = [p["x0"] for p in pads]
    for x0 in x0s:
        ent = enter_l4(sess)
        gg = ent["frame"]
        dd = ent["data"]
        for xy in path_xy:
            dd = sess.click(*xy)
            gg = plane(dd["frame"])
        sp0 = sprite(gg)
        pad = next(p for p in pads_sorted(gg) if p["x0"] == x0)
        xy = (int(round(pad["cx"])), int(round(pad["cy"])))
        try:
            dd2 = sess.click(*xy)
        except requests.HTTPError:
            continue
        gg2 = plane(dd2["frame"])
        sp1 = sprite(gg2)
        effects.append({
            "x0": x0,
            "xy": list(xy),
            "body": body_ndiff(gg, gg2),
            "ddx": None if not (sp0 and sp1) else round(sp1["body"]["cx"] - sp0["body"]["cx"], 3),
            "ddy": None if not (sp0 and sp1) else round(sp1["body"]["cy"] - sp0["body"]["cy"], 3),
            "acc_ddx": None
            if not (sp0 and sp1 and sp0.get("accent") and sp1.get("accent"))
            else round(sp1["accent"]["cx"] - sp0["accent"]["cx"], 3),
            "acc_ddy": None
            if not (sp0 and sp1 and sp0.get("accent") and sp1.get("accent"))
            else round(sp1["accent"]["cy"] - sp0["accent"]["cy"], 3),
            "levels": int(dd2.get("levels_completed") or 0),
            "dist": dist(gg2),
        })
    return effects


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"log": []}
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        path = []
        print("start", summarize(g), "dist", dist(g))

        # Phase 1: move up with x9, env when blocked — watch for unlock
        envs = [39, 45, 51, 57]
        env_i = 0
        for i in range(40):
            if aligned(g) or int(d.get("levels_completed") or 0) >= 4:
                break
            sp = sprite(g)
            gp = gap11(g)
            print(f"s{i} dist={dist(g):.1f} acc={sp['accent'] if sp else None} gap={gp} lv={d.get('levels_completed')}")

            # Prefer reducing dy first if |dy| large, else dx — but only if we have pads
            # Try known movers toward gap
            want = []
            if sp and gp:
                ady = sp["accent"]["cy"] - gp["cy"]
                adx = sp["accent"]["cx"] - gp["cx"]
                if abs(ady) >= 1.5:
                    want.append(9 if ady > 0 else 15)  # 9=-y, 15=+y
                if abs(adx) >= 1.5:
                    # unknown +x/-x pads yet; will probe if stuck
                    pass

            moved = False
            for x0 in want:
                g0 = g
                d2, g2, xy, st = click_x(sess, g, x0)
                if d2 is None:
                    print("err", x0)
                    continue
                bd = body_ndiff(g0, g2)
                sp1 = sprite(g2)
                ddx = (sp1["body"]["cx"] - sp["body"]["cx"]) if sp and sp1 else 0
                ddy = (sp1["body"]["cy"] - sp["body"]["cy"]) if sp and sp1 else 0
                entry = {"xy": xy, "x0": x0, "body": bd, "ddx": ddx, "ddy": ddy,
                         "levels": int(d2.get("levels_completed") or 0), "dist": dist(g2)}
                out["log"].append(entry)
                print(" ", entry)
                d, g = d2, g2
                path.append(xy)
                if bd > 0 and (abs(ddx) + abs(ddy) > 0.1):
                    moved = True
                    break
                if entry["levels"] >= 4:
                    moved = True
                    break

            if int(d.get("levels_completed") or 0) >= 4 or aligned(g):
                break

            if not moved:
                # env then retry
                x0 = envs[env_i % len(envs)]
                env_i += 1
                g0 = g
                d2, g2, xy, st = click_x(sess, g, x0)
                if d2 is None:
                    break
                bd = body_ndiff(g0, g2)
                entry = {"xy": xy, "x0": x0, "body": bd, "role": "env",
                         "levels": int(d2.get("levels_completed") or 0), "dist": dist(g2)}
                out["log"].append(entry)
                print("  env", entry)
                d, g = d2, g2
                path.append(xy)
                if st == "GAME_OVER":
                    print("GAME_OVER")
                    break
                # after a few envs, re-probe pad roles (costly) every 4 env clicks
                if env_i % 4 == 0:
                    print("reprobe pads...")
                    effects = probe_all_pads(sess, d, g, path, out["log"])
                    out.setdefault("reprobes", []).append({"path_len": len(path), "effects": effects})
                    print("effects", [(e["x0"], e["ddx"], e["ddy"], e["body"]) for e in effects])
                    # restore board by re-enter + path
                    ent = enter_l4(sess)
                    d, g = ent["data"], ent["frame"]
                    for xy in path:
                        d = sess.click(*xy)
                        g = plane(d["frame"])
                    # if any +x found, bias next wants — store
                    plus = [e for e in effects if (e.get("ddx") or 0) > 0.5]
                    minus = [e for e in effects if (e.get("ddx") or 0) < -0.5]
                    if plus or minus:
                        out["unlocked_x"] = {"plus": plus, "minus": minus}
                        print("UNLOCKED X", out["unlocked_x"])

            if env_i > 24 and not moved:
                print("give up phase1")
                break

        out["final"] = summarize(g)
        out["levels"] = int(d.get("levels_completed") or 0)
        out["cleared"] = out["levels"] >= 4
        print("CLEARED", out["cleared"], out["final"], "lv", out["levels"])

        if out["cleared"]:
            FIXTURE_L4_CLEAR.write_text(
                json.dumps({
                    "game_id": sess.game_id,
                    "meta": {
                        "levels_completed": d.get("levels_completed"),
                        "state": d.get("state"),
                        "available_actions": d.get("available_actions"),
                        "win_levels": d.get("win_levels"),
                    },
                    "log": out["log"],
                    "summary": summarize(g),
                    "frame": g.tolist(),
                }, indent=2, default=float),
                encoding="utf-8",
            )
            stale = g
            d5 = sess.action("ACTION1")
            g5 = plane(d5["frame"])
            diff = int(np.sum(stale != g5))
            FIXTURE_L5.write_text(
                json.dumps({
                    "game_id": sess.game_id,
                    "meta": {
                        "levels_completed": d5.get("levels_completed"),
                        "state": d5.get("state"),
                        "available_actions": d5.get("available_actions"),
                        "win_levels": d5.get("win_levels"),
                    },
                    "sync": {"action": "ACTION1", "pixel_diff_from_stale": diff},
                    "summary": summarize(g5),
                    "frame": g5.tolist(),
                }, indent=2, default=float),
                encoding="utf-8",
            )
            print("saved L4 clear + L5", diff)
    finally:
        sess.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("cleared") else 1


if __name__ == "__main__":
    raise SystemExit(main())
