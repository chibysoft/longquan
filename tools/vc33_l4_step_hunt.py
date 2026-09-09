"""L4: hunt non-3 step / 1px ceiling break; dig top tracks accent_y1+1."""
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
from tools.vc33_l4_pad_map import components, enter_l4, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_step_hunt.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def dig_top(g, x0=15, x1=26):
    ys = [int(y) for y, x in np.argwhere(g == 0) if x0 <= x <= x1]
    return min(ys) if ys else None


def gap0(g):
    return [(x, y) for x in (24, 25, 26) for y in range(34, 46) if int(g[y, x]) == 0]


def snap(g, d=None):
    sp = sprite(g)
    return {
        "cy": sp["body"]["cy"] if sp else None,
        "y0": sp["body"]["y0"] if sp else None,
        "acc_y1": sp["accent"]["y1"] if sp else None,
        "dig_top": dig_top(g),
        "gap0": gap0(g),
        "mid12": bool([c for c in components(g, 12, 1, 80) if c["cx"] > 20]),
        "lv": d.get("levels_completed") if d else None,
        "acts": d.get("available_actions") if d else None,
    }


def pad_xy(sess, d, g, x, y, tag=""):
    g0, s0 = g, sprite(g)
    d2 = click(sess, int(x), int(y))
    if d2 is None:
        return d, g, {}
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    info = {
        "xy": (int(x), int(y)),
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
        **snap(g2, d2),
    }
    interesting = (
        abs(info["dy"]) not in (0.0, 3.0)
        or abs(info["dx"]) not in (0.0, 15.0)
        or info["gap0"]
        or info["mid12"]
        or int(info["lv"] or 0) >= 4
        or info["nd"] > 0
        and abs(info["dx"]) + abs(info["dy"]) < 0.1
    )
    if abs(info["dx"]) + abs(info["dy"]) > 0.1 or info["nd"] or interesting:
        print(
            f"{tag}{info['xy']} Δ=({info['dx']},{info['dy']}) y0={info['y0']} "
            f"dig={info['dig_top']} gap0={info['gap0']} mid12={info['mid12']} "
            f"lv={info['lv']} nd={info['nd']}"
        )
    return d2, g2, info


def pad(sess, d, g, x0, tag=""):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    return pad_xy(sess, d, g, round(p["cx"]), round(p["cy"]), tag)


def to_ceil(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d, g, _ = pad(sess, d, g, 39, "hz ")
    for i in range(5):
        d, g, info = pad(sess, d, g, 15, f"up{i} ")
        if abs(info.get("dy") or 0) < 0.1:
            break
    print("CEIL", snap(g, d))
    return d, g


def maybe_clear(d, sess):
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
    return True


def main():
    key = _api_key()
    sess = Sess(key)
    hits = []
    try:
        sess.open()
        d, g = to_ceil(sess)
        if maybe_clear(d, sess):
            return

        # A: env then retry up — watch dy magnitude
        print("\n=== A env then up")
        for e in (39, 45, 51, 57):
            d, g, info = pad(sess, d, g, e, "e ")
        d, g, info = pad(sess, d, g, 15, "retry ")
        if abs(info.get("dy") or 0) not in (0.0, 3.0) or info.get("gap0"):
            hits.append({"A": info})
        if maybe_clear(d, sess):
            return

        # B: dense pad micro-grid (every cell of each pad)
        print("\n=== B pad microgrid")
        for p in pads_sorted(g):
            for y in range(p["y0"], p["y1"] + 1):
                for x in range(p["x0"], p["x1"] + 1):
                    d0, g0 = d, g
                    d, g, info = pad_xy(sess, d, g, x, y, f"p{p['x0']} ")
                    if abs(info.get("dy") or 0) not in (0.0, 3.0):
                        hits.append({"micro_dy": info})
                        print("NON3", info)
                    if info.get("gap0") or info.get("mid12") or int(info.get("lv") or 0) >= 4:
                        hits.append({"micro_hit": info})
                    if maybe_clear(d, sess):
                        return
                    # restore ceil if moved down
                    if (info.get("dy") or 0) > 0.1:
                        d, g, _ = pad(sess, d, g, 15, "rest ")
                    elif abs(info.get("dx") or 0) > 0.1:
                        print("left bay via micro", info)
                        d, g = to_ceil(sess)
                        break
                else:
                    continue
                break

        # C: click flank-like seam cells + sprite edge + mid edge
        print("\n=== C seam/sprite clicks")
        d, g = to_ceil(sess)
        sp = sprite(g)
        targets = []
        for x in range(sp["body"]["x1"], sp["body"]["x1"] + 5):
            for y in range(sp["accent"]["y0"] - 1, sp["accent"]["y1"] + 2):
                targets.append((x, y, "seam"))
        for x, y in [(26, 45), (25, 45), (24, 45), (26, 44), (30, 45), (28, 45), (27, 45)]:
            targets.append((x, y, "mid"))
        for x, y, tag in targets:
            d, g, info = pad_xy(sess, d, g, x, y, tag)
            if info.get("gap0") or info.get("mid12") or abs(info.get("dy") or 0) not in (0.0, 3.0):
                hits.append({"C": info})
            if maybe_clear(d, sess):
                return

        # D: convert, click flank dots BEFORE arm, then various
        print("\n=== D flank-before-arm")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _ = pad(sess, d, g, 15, "s ")
        print("pre-arm flanks", [(x, y) for y, x in np.argwhere(g == 0) if y <= 45])
        for x, y in [(10, 45), (16, 45), (10, 46), (16, 46)]:
            d, g, info = pad_xy(sess, d, g, x, y, "flank ")
            if info.get("nd") or abs(info.get("dx") or 0) + abs(info.get("dy") or 0) > 0.1:
                hits.append({"flank": info})
            if maybe_clear(d, sess):
                return
        # arm via flank? if still c12
        if int((g == 12).sum()):
            c = components(g, 12, 1, 80)[0]
            # click edge of CCC not center
            d, g, info = pad_xy(sess, d, g, c["x0"], c["y0"], "c12corner ")
            d, g, info = pad(sess, d, g, 39, "hz ")
            print("after edge-arm hop", snap(g, d))
            for i in range(5):
                d, g, info = pad(sess, d, g, 15, f"Du{i} ")
                if info.get("gap0") or info.get("mid12"):
                    hits.append({"Dclimb": info})
                if abs(info.get("dy") or 0) < 0.1:
                    break
                if maybe_clear(d, sess):
                    return

        OUT.write_text(json.dumps({"hits": hits, "final": snap(g, d)}, indent=2, default=str), encoding="utf-8")
        print("done hits", len(hits), "final", snap(g, d))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
