"""L4 H49: can gap11 y move down toward accent? any other align targets?"""
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

OUT = ROOT / "tests/fixtures/vc33_l4_y_align.json"


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
    gp0, gp1 = gap11(g0), gap11(g2)
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cy": s1["body"]["cy"] if s1 else None,
        "acc_y": (s1["accent"]["y0"], s1["accent"]["y1"]) if s1 else None,
        "gap_y": (gp1["y0"], gp1["y1"]) if gp1 else None,
        "gap_moved": (gp0 != gp1) if gp0 and gp1 else gp0 != gp1,
        "lv": d2.get("levels_completed"),
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
        "y_overlap": False,
    }
    if s1 and gp1:
        info["y_overlap"] = not (s1["accent"]["y1"] < gp1["y0"] or s1["accent"]["y0"] > gp1["y1"])
        info["dy_gap"] = s1["accent"]["cy"] - gp1["cy"]
    if info["gap_moved"] or info["y_overlap"] or int(info["lv"] or 0) >= 4:
        print(f"{tag}x{x0} GAP_MOVE={info['gap_moved']} y_ov={info['y_overlap']} "
              f"acc={info['acc_y']} gap={info['gap_y']} lv={info['lv']} ch={info['ch']}")
    return d2, g2, info


def all_11(g):
    return components(g, 11, min_n=1, max_n=10**9)


def maybe_clear(d, sess):
    if int(d.get("levels_completed") or 0) < 4:
        return False
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
    return True


def to_ceil(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d, g, _ = pad(sess, d, g, 39, "hz ")
    for _ in range(5):
        d, g, info = pad(sess, d, g, 15, "up ")
        if abs(info.get("dy") or 0) < 0.1:
            break
    return d, g


def main():
    key = _api_key()
    sess = Sess(key)
    log = []
    hits = []
    try:
        sess.open()

        # A: inventory all color11 at enter / ceil
        print("\n==== A color11 inventory")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        print("enter c11", all_11(g), "gap", gap11(g), "acc", sprite(g)["accent"])
        log.append({"enter_c11": all_11(g), "gap": gap11(g)})

        d, g = to_ceil(sess)
        sp = sprite(g)
        gp = gap11(g)
        print("ceil c11", all_11(g))
        print("ceil acc", sp["accent"], "gap", gp,
              "dy", sp["accent"]["cy"] - gp["cy"] if gp else None)
        log.append({"ceil_c11": all_11(g), "acc": sp["accent"], "gap": gp})

        # B: env spam watching gap y
        print("\n==== B env vs gap y")
        for i, e in enumerate([39, 45, 51, 57] * 5):
            d, g, info = pad(sess, d, g, e, f"B{i} ")
            if info.get("gap_moved") or info.get("y_overlap"):
                hits.append(info)
            if maybe_clear(d, sess):
                return
        print("gap after env", gap11(g))

        # C: click gap cells + beam above/below gap — does gap relocate?
        print("\n==== C click gap neighborhood")
        gp = gap11(g)
        if gp:
            for y in range(gp["y0"] - 3, gp["y1"] + 4):
                for x in range(gp["x0"] - 2, gp["x1"] + 3):
                    if not (0 <= x < 64 and 0 <= y < 64):
                        continue
                    g0, gp0 = g, gap11(g)
                    d2 = click(sess, x, y)
                    if d2 is None:
                        break
                    g2 = plane(d2["frame"])
                    gp1 = gap11(g2)
                    nd = body_ndiff(g0, g2)
                    moved = gp0 != gp1
                    if nd or moved or d2.get("levels_completed") != d.get("levels_completed"):
                        print(f"  ({x},{y}) nd={nd} gap {gp0} -> {gp1} lv={d2.get('levels_completed')}")
                        hits.append({"xy": (x, y), "moved": moved, "lv": d2.get("levels_completed")})
                    g = g2; d = d2
                    if maybe_clear(d, sess):
                        return

        # D: dn/up while watching dy_gap minimize; click gap at best
        print("\n==== D minimize dy_gap then click gap")
        best = None
        for _ in range(4):
            d, g, info = pad(sess, d, g, 9, "dn ")
            sp, gp = sprite(g), gap11(g)
            if sp and gp:
                dy = abs(sp["accent"]["cy"] - gp["cy"])
                print(f"  cy={sp['body']['cy']} acc_cy={sp['accent']['cy']} gap_cy={gp['cy']} |dy|={dy}")
                if best is None or dy < best[0]:
                    best = (dy, sp["accent"], gp)
            if maybe_clear(d, sess):
                return
        for _ in range(6):
            d, g, info = pad(sess, d, g, 15, "up ")
            sp, gp = sprite(g), gap11(g)
            if sp and gp:
                dy = abs(sp["accent"]["cy"] - gp["cy"])
                print(f"  cy={sp['body']['cy']} acc_cy={sp['accent']['cy']} gap_cy={gp['cy']} |dy|={dy}")
                if best is None or dy < best[0]:
                    best = (dy, sp["accent"], gp)
            if abs(info.get("dy") or 0) < 0.1:
                break
        print("best", best)
        if best and best[2]:
            gp = best[2]
            d2 = click(sess, round(gp["cx"]), round(gp["cy"]))
            if d2:
                print("best-gap click lv", d2.get("levels_completed"),
                      "nd", body_ndiff(g, plane(d2["frame"])))
                g = plane(d2["frame"]); d = d2
                if maybe_clear(d, sess):
                    return

        # E: any color14/15 like L2/L3? hist check at ceil
        u, c = np.unique(g, return_counts=True)
        print("ceil hist", dict(zip(map(int, u), map(int, c))))
        for col in (12, 14, 15, 2, 8, 10, 13):
            comps = components(g, col, 1, 10**9)
            if comps:
                print(f"  unexpected color{col}", comps)

        OUT.write_text(json.dumps({"log": log, "hits": hits, "best": best,
                                    "final_lv": d.get("levels_completed"),
                                    "final_gap": gap11(g),
                                    "final_acc": sprite(g)["accent"] if sprite(g) else None},
                                   indent=2, default=str), encoding="utf-8")
        print("done hits", hits, "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
