"""L4: at left-convert, expand color0@y<=45 east toward x24-26, then hop.

tags=["vc33_recon"]
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
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite, summarize  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_flank_east.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C", 9: "P"}


def dump(g, y0=40, y1=56, x0=0, x1=35):
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(x0, x1 + 1))
        print(f"{y:02d}|{row}")


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0, tag=""):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    g0, s0 = g, sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, {}
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "y0": s1["body"]["y0"] if s1 else None,
        "cy": s1["body"]["cy"] if s1 else None,
        "cx": s1["body"]["cx"] if s1 else None,
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
        "h12": int((g2 == 12).sum()),
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "lv": d2.get("levels_completed"),
    }
    print(
        f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) cy={info['cy']} "
        f"nd={info['nd']} h12={info['h12']} mid12={info['mid12']} lv={info['lv']}"
    )
    return d2, g2, info


def zeros_le45(g):
    cells = [(int(x), int(y)) for y, x in np.argwhere(g == 0) if y <= 45]
    cells.sort(key=lambda t: (t[1], t[0]))
    return cells


def flank_stats(g):
    z = zeros_le45(g)
    xs = [x for x, _ in z]
    at45 = [(x, y) for x, y in z if y == 45]
    at44 = [(x, y) for x, y in z if y == 44]
    at46 = [(int(x), 46) for x in range(0, 35) if int(g[46, x]) == 0]
    band = [(x, y) for x, y in z if 44 <= y <= 45]
    return {
        "n": len(z),
        "xmin": min(xs) if xs else None,
        "xmax": max(xs) if xs else None,
        "x_ge20": [(x, y) for x, y in z if x >= 20],
        "x_ge24": [(x, y) for x, y in z if x >= 24],
        "at44": at44,
        "at45": at45,
        "at46_x0_34": at46,
        "band44_45_xmax": max((x for x, y in band), default=None),
        "mid_gap0": [(x, y) for x in (24, 25, 26) for y in range(34, 46) if int(g[y, x]) == 0],
        "cells_crit": {
            "26_44": int(g[44, 26]),
            "26_45": int(g[45, 26]),
            "26_46": int(g[46, 26]),
            "20_45": int(g[45, 20]),
            "16_45": int(g[45, 16]),
            "10_45": int(g[45, 10]),
        },
    }


def to_convert(sess):
    """Enter L4, sink until left 1→12. Return before arming."""
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, info = pad(sess, d, g, 15, "s ")
        if abs(info.get("dy") or 0) < 0.1 and int((g == 12).sum()) == 0:
            # stuck — one more try from start height
            break
    return d, g


def arm(sess, d, g):
    c12 = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
    if not c12:
        return d, g, False
    c = c12[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    if d2 is None:
        return d, g, False
    return d2, plane(d2["frame"]), True


def maybe_clear(d, g, sess, out):
    if int(d.get("levels_completed") or 0) < 4:
        return False
    print("CLEAR", d.get("levels_completed"))
    (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
        json.dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
        encoding="utf-8",
    )
    d1 = sess.action("ACTION1")
    (ROOT / "tests/fixtures/vc33_l5_frame_live.json").write_text(
        json.dumps({"frame": d1["frame"], "levels": d1.get("levels_completed")}, indent=2),
        encoding="utf-8",
    )
    out["cleared"] = True
    out["l5_lv"] = d1.get("levels_completed")
    return True


def east_edge_zeros(g, y_lo=44, y_hi=46):
    """Rightmost color0 cells in dig band for clicking."""
    out = []
    for y in range(y_lo, y_hi + 1):
        xs = [int(x) for x in range(0, 40) if int(g[y, x]) == 0]
        if not xs:
            continue
        xmax = max(xs)
        out.append((xmax, y))
        if xmax + 1 < 64 and int(g[y, xmax + 1]) == 3:
            out.append((xmax + 1, y))  # empty just east of edge
    return out


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"phases": {}, "hits": []}
    try:
        sess.open()

        # === 1: convert dump — any y<=45 zeros already x>=20? ===
        print("\n=== 1 convert dump y<=45 zeros")
        d, g = to_convert(sess)
        st = flank_stats(g)
        sp = sprite(g)
        print("convert cy", sp["body"]["cy"] if sp else None, "h12", int((g == 12).sum()))
        print("flank", st)
        print("all y<=45 zeros:", st and zeros_le45(g))
        dump(g)
        out["phases"]["1_convert"] = {
            "cy": sp["body"]["cy"] if sp else None,
            "h12": int((g == 12).sum()),
            "flank": st,
            "zeros_le45": zeros_le45(g),
        }
        if st["x_ge20"] or st["mid_gap0"]:
            out["hits"].append({"phase": "1", "flank": st})

        # === 2: before hop — expand east at y44-46 ===
        print("\n=== 2 pre-hop east expand (unarmed)")
        # 2a env interleaved
        for i, e in enumerate((39, 45, 51, 57, 39, 45, 51, 57)):
            d, g, info = pad(sess, d, g, e, f"2e{i} ")
            st = flank_stats(g)
            print("  after env", e, "xmax", st["xmax"], "at45", st["at45"], "x_ge20", st["x_ge20"])
            out["phases"][f"2a_env{e}_{i}"] = st
            if st["x_ge24"] or st["mid_gap0"]:
                print("HIT east mid", st)
                out["hits"].append({"phase": "2a", "e": e, "flank": st})
            if maybe_clear(d, g, sess, out):
                OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                return

        # 2b click east-edge zeros + cell just east
        edges = east_edge_zeros(g)
        print("east edges", edges)
        for x, y in edges[:12]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            st = flank_stats(g2)
            if nd or st["xmax"] != flank_stats(g)["xmax"]:
                print(f"  click({x},{y}) nd={nd} ch={body_changes(g0,g2)} flank_xmax={st['xmax']} at45={st['at45']}")
                out["hits"].append({"phase": "2b", "xy": [x, y], "nd": nd, "flank": st})
                g, d = g2, d2
            else:
                g, d = g2, d2  # noop ok
            if st["x_ge24"] or st["mid_gap0"]:
                print("HIT click east", st)
            if maybe_clear(d, g, sess, out):
                OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                return

        # 2c micro dn/up interleaved with env
        for i in range(3):
            d, g, info = pad(sess, d, g, 15, f"2dn{i} ")  # deeper
            st = flank_stats(g)
            print("  deeper", st["xmax"], st["at45"], "h12", info.get("h12"))
            for e in (39, 45):
                d, g, info = pad(sess, d, g, e, f"2de{i} ")
                st = flank_stats(g)
                if st["x_ge20"] or st["mid_gap0"]:
                    print("HIT deep+env", st)
                    out["hits"].append({"phase": "2c", "flank": st})
            d, g, info = pad(sess, d, g, 9, f"2up{i} ")  # up toward convert height
            st = flank_stats(g)
            print("  up micro", st["xmax"], st["at45"], "cy", info.get("cy"), "h12", info.get("h12"))
            out["phases"][f"2c_{i}"] = st
            if st["x_ge24"] or st["mid_gap0"]:
                out["hits"].append({"phase": "2c_up", "flank": st})
            if maybe_clear(d, g, sess, out):
                OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                return

        st2 = flank_stats(g)
        out["phases"]["2_final_pre_arm"] = st2
        print("2 final pre-arm", st2)
        dump(g, 42, 56, 0, 35)

        # === 3: arm + hop (39 and fresh 15) if any expansion, else still hop to confirm ===
        print("\n=== 3 arm+hop after expand attempt")
        expanded = bool(st2["x_ge20"] or st2["mid_gap0"] or (st2["band44_45_xmax"] or 0) >= 20)

        def hop_trial(hop_pad, label):
            nonlocal d, g
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            while int((g == 12).sum()) == 0:
                d, g, _ = pad(sess, d, g, 15, f"{label}s ")
            # quick expand: env + edge clicks once
            for e in (39, 45, 51, 57):
                d, g, _ = pad(sess, d, g, e, f"{label}e ")
            for x, y in east_edge_zeros(g)[:6]:
                d2 = click(sess, x, y)
                if d2:
                    g, d = plane(d2["frame"]), d2
            st_pre = flank_stats(g)
            print(f"{label} pre-hop flank", st_pre)
            d, g, ok = arm(sess, d, g)
            print(f"{label} armed", ok)
            d, g, info = pad(sess, d, g, hop_pad, f"{label}hz ")
            st_land = flank_stats(g)
            print(f"{label} land", st_land, "sprite", sprite(g)["body"] if sprite(g) else None)
            out["phases"][f"{label}_land"] = {"pre": st_pre, "land": st_land, "info": info}
            if st_land["mid_gap0"] or info.get("mid12"):
                out["hits"].append({"phase": label, "land": st_land})
            # climb to mid and check convert
            for i in range(6):
                d, g, info = pad(sess, d, g, 15, f"{label}up{i} ")
                st = flank_stats(g)
                mid12 = info.get("mid12")
                print(f"  climb crit mid12={mid12} gap0={st['mid_gap0']} cells={st['cells_crit']} cy={info.get('cy')}")
                if mid12 or st["mid_gap0"] or int(info.get("lv") or 0) >= 4:
                    out["hits"].append({"phase": f"{label}_climb", "st": st, "info": info})
                    print("HIT climb")
                if abs(info.get("dy") or 0) < 0.1:
                    break
                if maybe_clear(d, g, sess, out):
                    return True
            # at ceil try click mid
            mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
            if mid:
                m = mid[0]
                d2 = click(sess, round(m["cx"]), round(m["cy"]))
                if d2:
                    g2 = plane(d2["frame"])
                    print(f"{label} midclick h12={int((g2==12).sum())} mid12",
                          bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
                          "lv", d2.get("levels_completed"))
                    g, d = g2, d2
                    if maybe_clear(d, g, sess, out):
                        return True
            return False

        if hop_trial(39, "3a39"):
            OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
            return
        if hop_trial(15, "3b15"):
            OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
            return

        # === 4: convert, no hop — climb with c12? / sink deeper then climb pit width ===
        print("\n=== 4a climb bay0 with c12 lit")
        d, g = to_convert(sess)
        st = flank_stats(g)
        print("4a at convert", st)
        for i in range(6):
            d, g, info = pad(sess, d, g, 9, f"4aup{i} ")  # up in left
            st = flank_stats(g)
            print(f"  c12={info.get('h12')} cy={info.get('cy')} flank_xmax={st['xmax']} at45={st['at45']} x_ge20={st['x_ge20']}")
            out["phases"][f"4a_{i}"] = {"h12": info.get("h12"), "cy": info.get("cy"), "flank": st}
            if st["x_ge24"] or st["mid_gap0"]:
                out["hits"].append({"phase": "4a", "flank": st})
            if info.get("h12") == 0:
                print("  c12 cleared while climbing")
                break
            if abs(info.get("dy") or 0) < 0.1:
                break

        print("\n=== 4b sink deeper then climb — watch dig east at high y")
        d, g = to_convert(sess)
        # deeper
        for i in range(3):
            d, g, info = pad(sess, d, g, 15, f"4bdn{i} ")
            st = flank_stats(g)
            print(f"  deep cy={info.get('cy')} h12={info.get('h12')} xmax={st['xmax']} at45={st['at45']}")
            if abs(info.get("dy") or 0) < 0.1:
                break
        dump(g, 42, 60, 0, 35)
        # climb watching xmax at y45 as we rise
        for i in range(10):
            d, g, info = pad(sess, d, g, 9, f"4bup{i} ")
            st = flank_stats(g)
            print(
                f"  up cy={info.get('cy')} h12={info.get('h12')} "
                f"xmax={st['xmax']} band_xmax={st['band44_45_xmax']} "
                f"at45={st['at45']} x_ge20={st['x_ge20']}"
            )
            out["phases"][f"4b_{i}"] = {"h12": info.get("h12"), "cy": info.get("cy"), "flank": st}
            if st["x_ge24"] or st["mid_gap0"]:
                print("HIT 4b", st)
                out["hits"].append({"phase": "4b", "flank": st})
                # arm hop immediately
                if int((g == 12).sum()):
                    d, g, ok = arm(sess, d, g)
                    d, g, info = pad(sess, d, g, 39, "4bhz ")
                    print("4b hop land", flank_stats(g), "mid12", info.get("mid12"))
                    for j in range(5):
                        d, g, info = pad(sess, d, g, 15, f"4bclimb{j} ")
                        if info.get("mid12") or flank_stats(g)["mid_gap0"]:
                            out["hits"].append({"phase": "4b_post", "st": flank_stats(g)})
                        if abs(info.get("dy") or 0) < 0.1:
                            break
                        if maybe_clear(d, g, sess, out):
                            OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                            return
                break
            if abs(info.get("dy") or 0) < 0.1:
                print("  left ceiling")
                dump(g, 38, 56, 0, 35)
                break

        out["final_lv"] = d.get("levels_completed")
        out["final_flank"] = flank_stats(g)
        out["expanded_flag"] = expanded
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("done hits", len(out["hits"]), "lv", out["final_lv"], "expanded", expanded)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
