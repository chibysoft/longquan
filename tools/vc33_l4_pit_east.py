"""L4: track color0 top vs climb; pad9 diagonal hop; env paint at floor; east scan."""
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

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C", 9: "P"}
OUT = ROOT / "tests/fixtures/vc33_l4_pit_east.json"


def dump(g, y0=28, y1=63, x0=0, x1=63):
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


def pit_stats(g):
    """color0 tops in key columns + global min-y of color0 in playfield."""
    tops = {}
    for x in range(0, 64):
        ys = [y for y in range(64) if int(g[y, x]) == 0]
        if ys:
            tops[x] = min(ys)
    near = {x: tops[x] for x in range(18, 32) if x in tops}
    mid_gap = [(x, y) for x in (24, 25, 26) for y in range(34, 46) if int(g[y, x]) == 0]
    return {
        "min_y_global": min(tops.values()) if tops else None,
        "tops_18_31": near,
        "mid_gap0": mid_gap,
        "n0": int((g == 0).sum()),
    }


def arm_hop(sess, hop_pad=39):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _, _ = pad(sess, d, g, 15, "sink ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d, g, dx, dy = pad(sess, d, g, hop_pad, f"hop{hop_pad} ")
    return d, g


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()

        # A: hop39, climb step-by-step logging pit
        print("\n==== A pit vs climb ====")
        d, g = arm_hop(sess, 39)
        steps = []
        for i in range(6):
            st = pit_stats(g)
            sp = sprite(g)
            print(f"step{i} cy={sp['body']['cy']} y0={sp['body']['y0']} pit={st}")
            steps.append({"i": i, "cy": sp["body"]["cy"], "y0": sp["body"]["y0"], **st})
            d, g, _, dy = pad(sess, d, g, 15, f"up{i} ")
            if abs(dy) < 0.1:
                st = pit_stats(g)
                print(f"CEILING pit={st}")
                steps.append({"i": "ceil", "cy": sprite(g)["body"]["cy"], **st})
                dump(g, 34, 55, 15, 45)
                break
        out["pit_climb"] = steps

        # B: pad9 diagonal hop (should land higher)
        print("\n==== B pad9 hop (diagonal) ====")
        d, g = arm_hop(sess, 9)
        st = pit_stats(g)
        print("land", sprite(g), st)
        out["pad9_land"] = {"sprite": sprite(g), **st}
        dump(g, 34, 56, 0, 50)
        for i in range(6):
            d, g, _, dy = pad(sess, d, g, 15, f"Bup{i} ")
            print(f"  pit={pit_stats(g)}")
            if abs(dy) < 0.1:
                print("B ceiling", sprite(g))
                dump(g, 34, 50, 15, 35)
                break
            if pit_stats(g)["mid_gap0"] or any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("B HIT", pit_stats(g))
                break

        # C: hop39 keep c12, at floor spam env; watch mid_gap0 and east opens
        print("\n==== C floor env paint ====")
        d, g = arm_hop(sess, 39)
        print("floor", sprite(g), pit_stats(g))
        dump(g, 40, 63, 0, 63)
        paint_log = []
        for round_i in range(3):
            for x0 in (39, 45, 51, 57):
                g0 = g
                d, g, dx, dy = pad(sess, d, g, x0, f"C{round_i} ")
                st = pit_stats(g)
                ch = body_changes(g0, g)
                # note flips in x24-29 y34-50
                flips = []
                for y in range(34, 51):
                    for x in range(24, 30):
                        if int(g0[y, x]) != int(g[y, x]):
                            flips.append((x, y, int(g0[y, x]), int(g[y, x])))
                if flips or st["mid_gap0"] or abs(dx) > 0.1:
                    print(f"  INTEREST flips={flips[:20]} mid0={st['mid_gap0']} dx={dx}")
                paint_log.append({"pad": x0, "flips_midband": flips, "pit": st, "dx": dx, "ch": ch})
                if st["mid_gap0"]:
                    print("PAINTED mid gap0")
                    dump(g, 34, 52, 20, 35)
                    # try convert nudge
                    d, g, _, _ = pad(sess, d, g, 15, "Cn ")
                    d, g, _, _ = pad(sess, d, g, 9, "Cn2 ")
                    print("after nudge", components(g, 12, 1, 80), pit_stats(g))
        out["floor_env"] = paint_log

        # D: from floor bay1 kill c12 with one up, dig, full east map, try env corridors
        print("\n==== D east corridor after dig ====")
        d, g = arm_hop(sess, 39)
        d, g, _, _ = pad(sess, d, g, 15, "kill12 ")
        for i in range(8):
            d, g, _, dy = pad(sess, d, g, 9, f"dig{i} ")
            if abs(dy) < 0.1:
                break
        print("deep", sprite(g))
        dump(g, 48, 63, 0, 63)
        # look for color0 corridors east of x30
        east0 = [(int(x), int(y)) for y, x in np.argwhere(g == 0) if x >= 30]
        print("east0 sample", east0[:40], "n", len(east0))
        # try each env twice looking for +x
        for x0 in (39, 45, 51, 57, 39, 45, 51, 57, 15, 9):
            d, g, dx, dy = pad(sess, d, g, x0, "De ")
            if abs(dx) > 0.1:
                print("EAST HZ", dx, sprite(g))
                dump(g)
                out["east_hz"] = {"dx": dx, "sprite": sprite(g)}
                break

        # E: soft y-align attempt — can accent reach gap y=29 somehow on left?
        print("\n==== E left max climb (no gate) toward gap y ====")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        # start cy45; pad9 = up
        for i in range(12):
            sp = sprite(g)
            gp = summarize(g)["gap"]
            print(f"E{i} cy={sp['body']['cy']} acc_y={sp['accent']['y0']} gap={gp} lv={d.get('levels_completed')}")
            if int(d.get("levels_completed") or 0) >= 4:
                print("SOFT CLEAR?!")
                break
            d, g, _, dy = pad(sess, d, g, 9, f"Eup{i} ")
            if abs(dy) < 0.1:
                print("left max", sprite(g))
                dump(g, 28, 50, 0, 50)
                # env at left max
                for e in (39, 45, 51, 57):
                    d, g, _, _ = pad(sess, d, g, e, f"Ee{e} ")
                    d, g, _, dy2 = pad(sess, d, g, 9, "Eretry ")
                    if abs(dy2) > 0.1:
                        print("broke left ceiling via env")
                        break
                break

        out["final_levels"] = d.get("levels_completed")
        OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
        print("wrote", OUT, "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
