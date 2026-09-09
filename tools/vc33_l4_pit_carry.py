"""L4: carry elevated color0 across hop; click mid-under beam; land tops.

Hypothesis: climb raises color0 under sprite; hop may translate that pit +15x.
If land tops <46, one climb breaks mid gap0. Also try color5 under mid → window extend.

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
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_pit_carry.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


def dump(g, y0=34, y1=56, x0=0, x1=40):
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
        "lv": d2.get("levels_completed"),
        "h12": int((g2 == 12).sum()),
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
    }
    print(f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) y0={info['y0']} cy={info['cy']} "
          f"h12={info['h12']} mid12={info['mid12']} lv={info['lv']}")
    return d2, g2, info


def tops(g, xs=range(0, 35)):
    o = {}
    for x in xs:
        ys = [int(y) for y in range(30, 64) if int(g[y, x]) == 0]
        if ys:
            o[int(x)] = min(ys)
    return o


def crit(g):
    t = tops(g, [3, 6, 9, 11, 18, 21, 24, 25, 26, 30])
    gap0 = [(x, y) for x in (24, 25, 26) for y in range(34, 46) if int(g[y, x]) == 0]
    midr0 = [(30, y) for y in range(34, 46) if int(g[y, 30]) == 0]
    sp = sprite(g)
    return {"tops": t, "gap0": gap0, "midr0": midr0,
            "body": sp["body"] if sp else None,
            "acc": sp["accent"] if sp else None,
            "cells": {(26, 44): int(g[44, 26]), (26, 45): int(g[45, 26]), (26, 46): int(g[46, 26]),
                      (30, 45): int(g[45, 30]), (30, 46): int(g[46, 30]), (30, 49): int(g[49, 30])}}


def maybe_clear(d, g, sess, out):
    if int(d.get("levels_completed") or 0) < 4:
        return False
    print("CLEAR", d.get("levels_completed"))
    (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
        json.dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2), encoding="utf-8")
    d1 = sess.action("ACTION1")
    (ROOT / "tests/fixtures/vc33_l5_frame_live.json").write_text(
        json.dumps({"frame": d1["frame"], "levels": d1.get("levels_completed")}, indent=2), encoding="utf-8")
    out["cleared"] = True
    return True


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"trials": []}
    try:
        sess.open()

        # A: left climb raise pit, measure, sink convert, arm, hop — land tops?
        print("\n=== A left-pit carry hop")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        print("enter", crit(g))
        d, g, _ = pad(sess, d, g, 9, "Aup ")  # to left ceil
        print("left ceil", crit(g))
        dump(g, 38, 56, 0, 30)
        out["trials"].append({"name": "A_left_ceil", **crit(g)})
        # sink to convert
        while int((g == 12).sum()) == 0:
            d, g, info = pad(sess, d, g, 15, "As ")
            if abs(info.get("dy") or 0) < 0.1:
                break
        print("converted", crit(g), "h12", int((g == 12).sum()))
        out["trials"].append({"name": "A_converted", **crit(g)})
        dump(g, 40, 58, 0, 30)
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g, d = plane(d2["frame"]), d2
        # hop via 39 and via 9 (diag)
        for hop in (39, 9, 15):
            # fresh convert+arm each hop type
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            d, g, _ = pad(sess, d, g, 9, "pre ")
            while int((g == 12).sum()) == 0:
                d, g, info = pad(sess, d, g, 15, "s ")
                if abs(info.get("dy") or 0) < 0.1:
                    break
            if int((g == 12).sum()) == 0:
                print("no c12 for hop", hop)
                continue
            c = components(g, 12, 1, 80)[0]
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            g, d = plane(d2["frame"]), d2
            pre = crit(g)
            d, g, info = pad(sess, d, g, hop, f"hop{hop} ")
            land = crit(g)
            print(f"LAND hop{hop}", land)
            dump(g, 40, 58, 15, 35)
            row = {"name": f"A_hop{hop}", "pre": pre, "land": land, "info": info}
            out["trials"].append(row)
            if land["gap0"] or land["midr0"] or (land["body"] and land["body"]["y0"] < 40):
                print("HIT land")
            # one climb if not at ceil
            if land["body"] and land["body"]["y0"] > 40:
                d, g, info = pad(sess, d, g, 15, "climb1 ")
                c2 = crit(g)
                print("after 1 climb", c2)
                out["trials"].append({"name": f"A_hop{hop}_up1", **c2})
                if c2["gap0"] or c2["midr0"] or (c2["body"] and c2["body"]["y0"] < 40):
                    print("HIT after climb")
                    out["hits"] = out.get("hits", []) + [f"hop{hop}_up1"]
            if maybe_clear(d, g, sess, out):
                OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                return

        # B: standard bay1 ceil — click color5 under mid (y46-50 x27-29) and beam
        print("\n=== B mid-under color5 clicks")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _ = pad(sess, d, g, 15, "Bs ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g, d = plane(d2["frame"]), d2
        d, g, _ = pad(sess, d, g, 39, "Bhz ")
        for i in range(5):
            d, g, info = pad(sess, d, g, 15, f"Bup{i} ")
            if abs(info.get("dy") or 0) < 0.1:
                break
        print("B ceil", crit(g))
        dump(g, 32, 52, 18, 40)
        targets = []
        for y in range(46, 54):
            for x in range(26, 31):
                targets.append((x, y, int(g[y, x])))
        for y in range(32, 36):
            for x in range(26, 32):
                targets.append((x, y, int(g[y, x])))
        # gap11 + beam toward gap
        gp = gap11(g)
        if gp:
            for y in range(gp["y0"] - 2, gp["y1"] + 3):
                for x in range(gp["x0"] - 2, gp["x1"] + 3):
                    targets.append((x, y, int(g[y, x])))
        seen = set()
        for x, y, col in targets:
            if (x, y) in seen or col == 3:
                continue
            seen.add((x, y))
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            if nd:
                print(f"Bclick({x},{y}) col={col} nd={nd} ch={body_changes(g0,g2)} "
                      f"lv={d2.get('levels_completed')} crit={crit(g2)}")
                g, d = g2, d2
                out.setdefault("hits", []).append({"xy": [x, y], "col": col, "ch": body_changes(g0, g2)})
                if crit(g)["gap0"] or crit(g)["midr0"] or int(d.get("levels_completed") or 0) >= 4:
                    print("HIT B")
            if maybe_clear(d, g, sess, out):
                OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                return
        # after beam clicks, retry up / mid convert check
        d, g, info = pad(sess, d, g, 15, "Bretry ")
        print("B final", crit(g), "mid12", info.get("mid12"), "lv", info.get("lv"))
        out["trials"].append({"name": "B_final", **crit(g), "info": info})

        # C: at ceil — does accent-on-empty (26,45) leave trail if we step dn/up?
        # compare (26,45) before/after single dn from ceil with sprite shifted? 
        print("\n=== C accent trail into (26,45)")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _ = pad(sess, d, g, 15, "Cs ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g, d = plane(d2["frame"]), d2
        d, g, _ = pad(sess, d, g, 39, "Chz ")
        for i in range(5):
            d, g, info = pad(sess, d, g, 15, f"Cup{i} ")
            if abs(info.get("dy") or 0) < 0.1:
                break
        # body is x18-23; need accent over x24-26 — can't without +x
        # try click accent rightmost cells then pads
        sp = sprite(g)
        acc = sp["accent"]
        for x in range(acc["x1"], acc["x1"] + 4):
            for y in range(acc["y0"], acc["y1"] + 1):
                if x < 64 and int(g[y, x]) in (3, 0, 11):
                    g0 = g
                    d2 = click(sess, x, y)
                    if d2 is None:
                        break
                    g2 = plane(d2["frame"])
                    if body_ndiff(g0, g2):
                        print(f"Cclick({x},{y}) ch={body_changes(g0,g2)}")
                        g, d = g2, d2
        print("C done", crit(g), "lv", d.get("levels_completed"))
        out["trials"].append({"name": "C_final", **crit(g), "lv": d.get("levels_completed")})

        out["final_lv"] = d.get("levels_completed")
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("done lv", out["final_lv"], "hits", out.get("hits"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
