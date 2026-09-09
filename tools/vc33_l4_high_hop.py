"""L4: convert left, climb UNARMED, then arm+hop at height; watch mid gap0 / 1→12."""
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

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}
OUT = ROOT / "tests/fixtures/vc33_l4_high_hop.json"


def dump(g, y0=28, y1=56, x0=0, x1=50):
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
        return d, g, 0.0, 0.0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0.0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0.0
    print(
        f"{tag}x{x0} Δ=({dx},{dy}) cx={s1['body']['cx'] if s1 else None} "
        f"cy={s1['body']['cy'] if s1 else None} h12={int((g2==12).sum())} "
        f"lv={d2.get('levels_completed')}"
    )
    return d2, g2, dx, dy


def mid_gap0(g):
    cells = [(x, y) for x in (24, 25, 26) for y in range(34, 46) if int(g[y, x]) == 0]
    return cells


def mid_left_col(g):
    mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    m = (mid12 or mid or [None])[0]
    if not m:
        return None, []
    col = [int(g[y, m["x0"] - 1]) for y in range(m["y0"], m["y1"] + 1)]
    return m, col


def arm_left(sess, d, g):
    c = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
    if not c:
        return d, g, False
    d2 = click(sess, round(c[0]["cx"]), round(c[0]["cy"]))
    if d2 is None:
        return d, g, False
    return d2, plane(d2["frame"]), True


def to_convert(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _, _ = pad(sess, d, g, 15, "sink ")
    return d, g


def report(label, g, d):
    m, col = mid_left_col(g)
    g0 = mid_gap0(g)
    mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    print(
        f"[{label}] sp={sprite(g)} gap0={g0} mid12={bool(mid12)} "
        f"leftcol0={col.count(0) if col else None} lv={d.get('levels_completed')}"
    )
    if col:
        print(f"  leftcol={col}")
    return {
        "sprite": sprite(g),
        "gap0": g0,
        "mid12": mid12,
        "leftcol": col,
        "levels": d.get("levels_completed"),
        "aligned": summarize(g)["aligned"],
    }


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"trials": []}
    try:
        sess.open()

        # Trial A: convert, climb unarmed as high as possible, arm+hop39
        print("\n==== A unarmed climb then hop39 ====")
        d, g = to_convert(sess)
        report("converted", g, d)
        dump(g)
        for i in range(10):
            d, g, dx, dy = pad(sess, d, g, 9, f"climb{i} ")
            if abs(dx) > 0.1:
                print("HZ while unarmed!")
                dump(g)
                break
            if abs(dy) < 0.1:
                print("left ceiling")
                break
            if int((g == 12).sum()) == 0:
                print("c12 cleared during climb")
                break
        report("pre-arm climb", g, d)
        dump(g, 28, 56, 0, 50)
        if int((g == 12).sum()):
            d, g, ok = arm_left(sess, d, g)
            print("armed", ok, sprite(g))
            d, g, dx, dy = pad(sess, d, g, 39, "hop39 ")
            row = report("post hop39 from height", g, d)
            out["trials"].append({"name": "A", **row})
            dump(g)
            if row["gap0"] or row["mid12"] or int(d.get("levels_completed") or 0) >= 4:
                print("HIT A")

        # Trial B: convert, climb unarmed to various heights, hop each time (fresh)
        # Heights: try after 1,2,3 ups — each fresh enter
        for n_up in (1, 2, 3, 4):
            print(f"\n==== B n_up={n_up} hop39 ====")
            d, g = to_convert(sess)
            for i in range(n_up):
                d, g, dx, dy = pad(sess, d, g, 9, f"u{i} ")
                if abs(dy) < 0.1 or int((g == 12).sum()) == 0:
                    break
            cy = sprite(g)["body"]["cy"] if sprite(g) else None
            if int((g == 12).sum()) == 0:
                print("lost c12 at cy", cy)
                out["trials"].append({"name": f"B{n_up}", "lost_c12": True, "cy": cy})
                continue
            d, g, ok = arm_left(sess, d, g)
            d, g, dx, dy = pad(sess, d, g, 39, "hop ")
            row = report(f"B{n_up}", g, d)
            out["trials"].append({"name": f"B{n_up}", "pre_cy": cy, **row})
            dump(g, 34, 52, 15, 35)
            # if gap0, try one more sink/up to convert
            if row["gap0"]:
                print("gap0 present — try nudge")
                d, g, _, _ = pad(sess, d, g, 15, "nudge_up ")
                report("after nudge", g, d)
                d, g, _, _ = pad(sess, d, g, 9, "nudge_dn ")
                report("after nudge dn", g, d)
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID CONVERTED")
                mid = [c for c in components(g, 12, 1, 80) if c["cx"] > 20][0]
                d2 = click(sess, round(mid["cx"]), round(mid["cy"]))
                g = plane(d2["frame"]); d = d2
                for x0 in (39, 45, 51, 57, 9, 15):
                    d, g, dx, dy = pad(sess, d, g, x0, "mhz ")
                    if abs(dx) > 0.1:
                        print("MID HOP", dx)
                        dump(g)
                        break
            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR")
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
                break

        # Trial C: convert, climb, arm, hop via SECOND gate click (not pad)
        print("\n==== C climb then gate2 hop ====")
        d, g = to_convert(sess)
        for i in range(3):
            d, g, _, dy = pad(sess, d, g, 9, f"Cu{i} ")
            if abs(dy) < 0.1 or int((g == 12).sum()) == 0:
                break
        if int((g == 12).sum()):
            c = components(g, 12, 1, 80)[0]
            d2 = click(sess, round(c["cx"]), round(c["cy"]))  # arm
            g = plane(d2["frame"]); d = d2
            d2 = click(sess, round(c["cx"]), round(c["cy"]))  # hop
            g = plane(d2["frame"]); d = d2
            row = report("C gate2 hop", g, d)
            out["trials"].append({"name": "C", **row})
            dump(g, 34, 52, 15, 35)

        # Trial D: hop39 at floor, climb; at ceiling try pad9 hop back then
        # immediately hop again without re-climb? (phase)
        print("\n==== D phase hop west then east at cy42 ====")
        d, g = to_convert(sess)
        d, g, ok = arm_left(sess, d, g)
        d, g, _, _ = pad(sess, d, g, 39, "Dhz ")
        for i in range(5):
            d, g, _, dy = pad(sess, d, g, 15, f"Dup{i} ")
            if abs(dy) < 0.1:
                break
        report("D ceiling", g, d)
        # re-arm left if c12
        if int((g == 12).sum()) == 0:
            # go down to get c12
            while int((g == 12).sum()) == 0 and sprite(g)["body"]["cy"] < 52:
                d, g, _, dy = pad(sess, d, g, 9, "Ddn ")
                if abs(dy) < 0.1:
                    break
        if int((g == 12).sum()):
            # climb back to ceiling WITH c12? unarmed climb clears?
            # instead: arm and hop west at floor, then from left climb+hop high
            d, g, ok = arm_left(sess, d, g)
            d, g, dx, _ = pad(sess, d, g, 39, "Dwest ")
            print("after west", sprite(g), "dx", dx)
            # if on left, climb unarmed if c12 else reconvert
            if sprite(g)["body"]["cx"] < 12:
                if int((g == 12).sum()) == 0:
                    while int((g == 12).sum()) == 0:
                        d, g, _, _ = pad(sess, d, g, 15, "Dsink ")
                for i in range(4):
                    d, g, _, dy = pad(sess, d, g, 9, f"Dcu{i} ")
                    if abs(dy) < 0.1 or int((g == 12).sum()) == 0:
                        break
                if int((g == 12).sum()):
                    d, g, ok = arm_left(sess, d, g)
                    d, g, _, _ = pad(sess, d, g, 39, "Dhihop ")
                    row = report("D hi hop", g, d)
                    out["trials"].append({"name": "D", **row})
                    dump(g)

        out["final"] = summarize(g) if g is not None else None
        OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
