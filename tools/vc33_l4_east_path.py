"""L4 H32/H33: can sprite get cx>28 or reach gap without mid12?

tags=["vc33_recon"]. Enter via enter_l4. Does NOT duplicate mid_iso flank work.
"""
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
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import (  # noqa: E402
    FIXTURE_L4_CLEAR,
    FIXTURE_L5,
    components,
    enter_l4,
    sprite,
)

OUT = ROOT / "tests/fixtures/vc33_l4_east_path.json"
PAD_XS = (9, 15, 39, 45, 51, 57)


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def snap(d, g, tag=""):
    sp = sprite(g)
    acts = d.get("available_actions")
    lv = d.get("levels_completed")
    cx = sp["body"]["cx"] if sp else None
    cy = sp["body"]["cy"] if sp else None
    x1 = sp["body"]["x1"] if sp else None
    print(
        f"{tag} cx={cx} cy={cy} x1={x1} h12={int((g==12).sum())} "
        f"acts={acts} lv={lv}"
    )
    return {
        "tag": tag,
        "cx": cx,
        "cy": cy,
        "x0": sp["body"]["x0"] if sp else None,
        "x1": x1,
        "cy_body": cy,
        "h12": int((g == 12).sum()),
        "acts": acts,
        "lv": lv,
        "cx_gt28": (cx is not None and cx > 28),
        "x1_gt28": (x1 is not None and x1 > 28),
    }


def pad(sess, d, g, x0, tag="", log=None):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    s0 = sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, None
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0.0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0.0
    info = snap(d2, g2, f"{tag}pad{x0}")
    info.update({"dx": dx, "dy": dy, "nd": body_ndiff(g, g2)})
    if log is not None:
        log.append(info)
    return d2, g2, info


def sink_to_c12(sess, d, g, log=None):
    for i in range(12):
        if int((g == 12).sum()) > 0:
            break
        d, g, info = pad(sess, d, g, 15, f"sink{i} ", log)
        if info and abs(info.get("dy") or 0) < 0.1 and int((g == 12).sum()) == 0:
            break
    return d, g


def arm_left(sess, d, g, log=None):
    c12 = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
    if not c12:
        return d, g, False
    c = c12[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    if d2 is None:
        return d, g, False
    g2 = plane(d2["frame"])
    info = snap(d2, g2, "arm_left")
    if log is not None:
        log.append(info)
    return d2, g2, True


def mid_win(g):
    mids = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    return mids[0] if mids else None


def click_mid(sess, d, g, log=None, tag="mid"):
    m = mid_win(g)
    if not m:
        # maybe already color12 mid — try that
        mids = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
        if not mids:
            return d, g, None
        m = mids[0]
    d2 = click(sess, round(m["cx"]), round(m["cy"]))
    if d2 is None:
        return d, g, None
    g2 = plane(d2["frame"])
    s0, s1 = sprite(g), sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0.0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0.0
    info = snap(d2, g2, tag)
    info.update({"dx": dx, "dy": dy, "nd": body_ndiff(g, g2), "mid_xy": [m["cx"], m["cy"]]})
    if log is not None:
        log.append(info)
    return d2, g2, info


def east_corridor(g, y_lo=28, y_hi=55):
    """Any y with continuous color0 from x26 to x40?"""
    hits = []
    for y in range(y_lo, y_hi + 1):
        xs = [x for x in range(26, 41) if int(g[y, x]) == 0]
        if not xs:
            continue
        # longest run / reach
        xmax = max(xs)
        # check path connectivity from 26
        if 26 in xs or any(int(g[y, x]) == 0 for x in range(26, 30)):
            connected = True
            for x in range(26, min(xmax, 40) + 1):
                if int(g[y, x]) != 0:
                    # allow one-gap? no — strict
                    connected = False
                    break
            if connected and xmax >= 30:
                hits.append({"y": y, "xmax": xmax, "n0": len(xs)})
    return hits


def color0_east_of(g, x_min=26):
    cells = [(int(x), int(y)) for y, x in np.argwhere(g == 0) if x >= x_min]
    return {
        "n": len(cells),
        "xmax": max((c[0] for c in cells), default=None),
        "ymin": min((c[1] for c in cells), default=None),
        "sample": cells[:30],
    }


def maybe_clear(sess, d, out):
    if int(d.get("levels_completed") or 0) < 4:
        return False
    print("CLEAR", d.get("levels_completed"))
    FIXTURE_L4_CLEAR.write_text(
        json.dumps(
            {
                "game_id": sess.game_id,
                "levels_completed": d.get("levels_completed"),
                "available_actions": d.get("available_actions"),
                "frame": d["frame"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    d1 = sess.action("ACTION1")
    FIXTURE_L5.write_text(
        json.dumps(
            {
                "game_id": sess.game_id,
                "levels_completed": d1.get("levels_completed"),
                "available_actions": d1.get("available_actions"),
                "frame": d1["frame"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    out["cleared"] = True
    out["l5_lv"] = d1.get("levels_completed")
    return True


def max_cx(log):
    cxs = [e["cx"] for e in log if e.get("cx") is not None]
    return max(cxs) if cxs else None


def any_acts_leave6(log):
    odd = []
    for e in log:
        a = e.get("acts")
        if a is not None and list(a) != [6]:
            odd.append({"tag": e.get("tag"), "acts": a})
    return odd


def main():
    key = _api_key()
    sess = Sess(key)
    out = {
        "hypothesis": "H32/H33 east of mid / gap without mid12",
        "bay0_armed": [],
        "bay1_rearm": [],
        "deep_dig": {},
        "acts_odd": [],
        "max_cx_global": None,
        "cleared": False,
    }
    try:
        sess.open()
        out["game_id"] = sess.game_id

        # ========== 1: bay0 armed — all pads + mid ==========
        print("\n==== 1 bay0 armed: all pads + mid")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        log1 = []
        snap(d, g, "enter")
        d, g = sink_to_c12(sess, d, g, log1)
        d, g, ok = arm_left(sess, d, g, log1)
        print("armed", ok, "cx", sprite(g)["body"]["cx"] if sprite(g) else None)
        # try each pad once from fresh arm — re-enter each time for clean landings
        landings = []
        for px in PAD_XS:
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            d, g = sink_to_c12(sess, d, g)
            d, g, ok = arm_left(sess, d, g)
            if not ok:
                landings.append({"pad": px, "armed": False})
                continue
            pre = snap(d, g, f"pre{px}")
            d, g, info = pad(sess, d, g, px, f"b0 ", log1)
            landings.append({
                "pad": px,
                "pre_cx": pre["cx"],
                "land_cx": info["cx"] if info else None,
                "land_x1": info["x1"] if info else None,
                "dx": info.get("dx") if info else None,
                "dy": info.get("dy") if info else None,
                "acts": info.get("acts") if info else None,
                "lv": info.get("lv") if info else None,
            })
            if maybe_clear(sess, d, out):
                break
        # mid-click from bay0 armed (fresh)
        if not out.get("cleared"):
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            d, g = sink_to_c12(sess, d, g)
            d, g, ok = arm_left(sess, d, g, log1)
            d, g, info = click_mid(sess, d, g, log1, "b0_mid")
            landings.append({
                "pad": "mid",
                "land_cx": info["cx"] if info else None,
                "land_x1": info["x1"] if info else None,
                "dx": info.get("dx") if info else None,
                "dy": info.get("dy") if info else None,
                "acts": info.get("acts") if info else None,
            })
            maybe_clear(sess, d, out)
        out["bay0_armed"] = {
            "landings": landings,
            "max_cx": max(
                (L["land_cx"] for L in landings if L.get("land_cx") is not None),
                default=None,
            ),
            "any_cx_gt28": any(
                (L.get("land_cx") or 0) > 28 or (L.get("land_x1") or 0) > 28
                for L in landings
            ),
            "log_tail": log1[-8:],
        }
        print("bay0 max_cx", out["bay0_armed"]["max_cx"], "gt28", out["bay0_armed"]["any_cx_gt28"])

        if out.get("cleared"):
            OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
            return

        # ========== 2: bay1 fresh re-arm — pads + mid + left c12 ==========
        print("\n==== 2 bay1 re-arm: pads + mid + left12")
        landings2 = []

        def to_bay1_floor(sess):
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            d, g = sink_to_c12(sess, d, g)
            d, g, ok = arm_left(sess, d, g)
            if not ok:
                return d, g, False
            d, g, _ = pad(sess, d, g, 39, "hop ")
            return d, g, True

        def rearm_bay1(sess, d, g, log=None):
            """Sink/climb until left c12, or re-convert if needed; arm left."""
            # if no c12: dig/sink to convert again in bay1 (cy~51)
            if int((g == 12).sum()) == 0:
                # try sink with pad9 (down in bay1)
                for i in range(8):
                    d, g, info = pad(sess, d, g, 9, f"b1dn{i} ", log)
                    if int((g == 12).sum()) > 0:
                        break
                    if info and abs(info.get("dy") or 0) < 0.1:
                        break
            # if still no left c12 — hop west and convert left again then hop back
            left12 = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
            if not left12:
                # hop west to bay0
                d, g, info = pad(sess, d, g, 39, "west ", log)
                d, g = sink_to_c12(sess, d, g, log)
                d, g, ok = arm_left(sess, d, g, log)
                if ok:
                    d, g, _ = pad(sess, d, g, 39, "rehop ", log)
                # now at bay1 with charge spent; need re-arm: sink for c12 then click
                if int((g == 12).sum()) == 0:
                    for i in range(8):
                        d, g, info = pad(sess, d, g, 9, f"b1s{i} ", log)
                        if int((g == 12).sum()) > 0:
                            break
                        if info and abs(info.get("dy") or 0) < 0.1:
                            break
            d, g, ok = arm_left(sess, d, g, log)
            return d, g, ok

        for target in list(PAD_XS) + ["mid", "left12"]:
            log2 = []
            d, g, ok = to_bay1_floor(sess)
            if not ok:
                landings2.append({"target": target, "ok": False})
                continue
            d, g, ok = rearm_bay1(sess, d, g, log2)
            pre = snap(d, g, f"b1pre_{target}")
            log2.append(pre)
            if not ok:
                landings2.append({"target": target, "armed": False, "pre_cx": pre["cx"]})
                continue
            if target == "mid":
                d, g, info = click_mid(sess, d, g, log2, "b1_mid")
            elif target == "left12":
                # second click on left c12 (or whatever remains)
                left = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
                if not left:
                    # click left window color1 if present
                    left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20]
                if left:
                    c = left[0]
                    d2 = click(sess, round(c["cx"]), round(c["cy"]))
                    if d2 is None:
                        info = None
                    else:
                        g = plane(d2["frame"])
                        d = d2
                        info = snap(d, g, "b1_left12")
                        s0cx = pre["cx"]
                        if info["cx"] is not None and s0cx is not None:
                            info["dx"] = info["cx"] - s0cx
                        log2.append(info)
                else:
                    info = None
                    print("no left12/1 to click")
            else:
                d, g, info = pad(sess, d, g, target, "b1 ", log2)
            landings2.append({
                "target": target,
                "armed": True,
                "pre_cx": pre["cx"],
                "land_cx": info["cx"] if info else None,
                "land_x1": info["x1"] if info else None,
                "dx": info.get("dx") if info else None,
                "dy": info.get("dy") if info else None,
                "acts": info.get("acts") if info else None,
                "lv": info.get("lv") if info else None,
            })
            print(
                f"  target={target} pre={pre['cx']} land={info['cx'] if info else None} "
                f"dx={info.get('dx') if info else None}"
            )
            if maybe_clear(sess, d, out):
                break
        out["bay1_rearm"] = {
            "landings": landings2,
            "max_cx": max(
                (L["land_cx"] for L in landings2 if L.get("land_cx") is not None),
                default=None,
            ),
            "any_cx_gt28": any(
                (L.get("land_cx") or 0) > 28 or (L.get("land_x1") or 0) > 28
                for L in landings2
            ),
            "any_dx_past_mid": any(
                (L.get("dx") or 0) > 5 and (L.get("land_cx") or 0) > 25
                for L in landings2
            ),
        }
        print(
            "bay1 max_cx", out["bay1_rearm"]["max_cx"],
            "gt28", out["bay1_rearm"]["any_cx_gt28"],
        )

        if out.get("cleared"):
            OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
            return

        # ========== 3: hop → deep dig → env spam → climb; east corridor? ==========
        print("\n==== 3 deep dig + env + climb corridor")
        log3 = []
        d, g, ok = to_bay1_floor(sess)
        # dig deep with pad9
        for i in range(14):
            d, g, info = pad(sess, d, g, 9, f"dig{i} ", log3)
            if info and abs(info.get("dy") or 0) < 0.1:
                break
        deep_sp = snap(d, g, "deep")
        corr_deep = east_corridor(g)
        east_deep = color0_east_of(g, 26)
        print("deep", deep_sp, "corr", corr_deep, "east0", east_deep["n"], east_deep["xmax"])

        # env spam
        env_flips = []
        for round_i in range(3):
            for px in (39, 45, 51, 57):
                g0 = g
                d, g, info = pad(sess, d, g, px, f"env{round_i} ", log3)
                flips = []
                for y in range(28, 56):
                    for x in range(24, 41):
                        if int(g0[y, x]) != int(g[y, x]):
                            flips.append((x, y, int(g0[y, x]), int(g[y, x])))
                if flips:
                    env_flips.append({"pad": px, "n": len(flips), "sample": flips[:20]})
                    print(f"  env{px} flips_n={len(flips)} sample={flips[:8]}")
                corr = east_corridor(g)
                if corr:
                    print("CORRIDOR after env", corr)
                    break
            else:
                continue
            break

        corr_env = east_corridor(g)
        east_env = color0_east_of(g, 26)

        # climb
        climb_log = []
        for i in range(10):
            d, g, info = pad(sess, d, g, 15, f"up{i} ", log3)
            corr = east_corridor(g)
            st = {
                "i": i,
                "cx": info["cx"] if info else None,
                "cy": info["cy"] if info else None,
                "corr": corr,
                "east_xmax": color0_east_of(g, 26)["xmax"],
                "acts": info.get("acts") if info else None,
            }
            climb_log.append(st)
            print(f"  climb{i} cx={st['cx']} cy={st['cy']} corr={corr} east_xmax={st['east_xmax']}")
            if corr:
                print("CORRIDOR on climb")
                break
            if info and abs(info.get("dy") or 0) < 0.1:
                break
            if maybe_clear(sess, d, out):
                break

        # try "walk" — click color0 cells east if any path; also click empty east cells
        walk_hits = []
        corr_now = east_corridor(g)
        east_cells = color0_east_of(g, 26)["sample"]
        # also try stepping pads while noting cx
        for x, y in east_cells[:12]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            info = snap(d2, g2, f"walk({x},{y})")
            if nd or info.get("cx_gt28"):
                walk_hits.append({"xy": [x, y], "nd": nd, **info})
                print("WALK HIT", walk_hits[-1])
                g = g2
                d = d2
            else:
                print(f"walk({x},{y}) noop")

        # also try clicking along x26..40 at accent y / body y if color0 or color3
        sp = sprite(g)
        if sp:
            ay = int(sp["accent"]["y0"]) if sp.get("accent") else int(sp["body"]["cy"])
            for x in range(26, 41, 2):
                for y in (ay, ay - 1, ay + 1, 40, 45, 46):
                    if not (0 <= y < 64):
                        continue
                    g0 = g
                    d2 = click(sess, x, y)
                    if d2 is None:
                        continue
                    g2 = plane(d2["frame"])
                    nd = body_ndiff(g0, g2)
                    if nd:
                        info = snap(d2, g2, f"scan({x},{y})")
                        walk_hits.append({"xy": [x, y], "nd": nd, **info})
                        print("SCAN HIT", walk_hits[-1])
                        g, d = g2, d2
                        if info.get("cx_gt28"):
                            break
                else:
                    continue
                break

        maybe_clear(sess, d, out)
        out["deep_dig"] = {
            "deep": deep_sp,
            "corr_deep": corr_deep,
            "east_deep": east_deep,
            "env_flips_n": len(env_flips),
            "env_flips": env_flips[:12],
            "corr_env": corr_env,
            "east_env": east_env,
            "climb": climb_log,
            "corr_final": east_corridor(g),
            "walk_hits": walk_hits,
            "final_cx": sprite(g)["body"]["cx"] if sprite(g) else None,
            "max_cx_log": max_cx(log3),
        }
        print(
            "deep_dig final_cx", out["deep_dig"]["final_cx"],
            "corr_final", out["deep_dig"]["corr_final"],
            "walk_hits", len(walk_hits),
        )

        # ========== 4: acts summary ==========
        all_logs = []
        for section in (out.get("bay0_armed") or {},):
            all_logs.extend(section.get("log_tail") or [])
        all_logs.extend(log3)
        # also harvest from landings acts
        for L in (out["bay0_armed"].get("landings") or []):
            if L.get("acts") is not None:
                all_logs.append({"tag": f"land{L.get('pad')}", "acts": L["acts"], "cx": L.get("land_cx")})
        for L in (out["bay1_rearm"].get("landings") or []):
            if L.get("acts") is not None:
                all_logs.append({"tag": f"b1land{L.get('target')}", "acts": L["acts"], "cx": L.get("land_cx")})
        out["acts_odd"] = any_acts_leave6(all_logs)
        out["acts_always_6"] = len(out["acts_odd"]) == 0
        cxs = []
        for L in out["bay0_armed"].get("landings") or []:
            if L.get("land_cx") is not None:
                cxs.append(L["land_cx"])
        for L in out["bay1_rearm"].get("landings") or []:
            if L.get("land_cx") is not None:
                cxs.append(L["land_cx"])
        if out["deep_dig"].get("final_cx") is not None:
            cxs.append(out["deep_dig"]["final_cx"])
        if out["deep_dig"].get("max_cx_log") is not None:
            cxs.append(out["deep_dig"]["max_cx_log"])
        out["max_cx_global"] = max(cxs) if cxs else None
        out["verdict"] = {
            "H32_cx_gt28": out["max_cx_global"] is not None and out["max_cx_global"] > 28,
            "H33_gap_without_mid12": False,  # only True if levels>=4 without mid12
            "levels_final": d.get("levels_completed"),
            "acts_always_6": out["acts_always_6"],
            "corridor_ever": bool(
                out["deep_dig"].get("corr_deep")
                or out["deep_dig"].get("corr_env")
                or out["deep_dig"].get("corr_final")
                or any(c.get("corr") for c in out["deep_dig"].get("climb") or [])
            ),
        }
        print("\n==== VERDICT", out["verdict"], "max_cx", out["max_cx_global"])

    finally:
        try:
            sess.close()
        except Exception:
            pass
        OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
        print("wrote", OUT)


if __name__ == "__main__":
    main()
