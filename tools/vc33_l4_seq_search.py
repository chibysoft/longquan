"""L4: targeted search — ceil pad-corners; hop9 path; mid12/+x/levels."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite, summarize  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_seq_search.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


def dump(g, y0=34, y1=50, x0=15, x1=45):
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(x0, x1 + 1))
        print(f"{y:02d}|{row}")


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0, tag="", corner=0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    if corner == 0:
        xy = (int(round(p["cx"])), int(round(p["cy"])))
    else:
        corners = [
            (p["x0"], p["y0"]),
            (p["x1"], p["y0"]),
            (p["x0"], p["y1"]),
            (p["x1"], p["y1"]),
        ]
        xy = corners[corner - 1]
    g0, s0 = g, sprite(g)
    d2 = click(sess, *xy)
    if d2 is None:
        return d, g, {}
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    info = {
        "xy": xy,
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cx": s1["body"]["cx"] if s1 else None,
        "cy": s1["body"]["cy"] if s1 else None,
        "h12": int((g2 == 12).sum()),
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "lv": d2.get("levels_completed"),
        "acts": d2.get("available_actions"),
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
    }
    flag = ""
    if info["mid12"] or int(info["lv"] or 0) >= 4 or (info["cx"] or 0) > 28 or abs(info["dx"]) > 0.1:
        flag = " ***"
    if abs(info["dx"]) + abs(info["dy"]) > 0.1 or info["nd"] > 0 or flag:
        print(
            f"{tag}x{x0}c{corner}{xy} Δ=({info['dx']},{info['dy']}) "
            f"cy={info['cy']} cx={info['cx']} mid12={info['mid12']} lv={info['lv']} "
            f"acts={info['acts']}{flag}"
        )
    return d2, g2, info


def xy_click(sess, d, g, x, y, tag=""):
    g0, s0 = g, sprite(g)
    d2 = click(sess, x, y)
    if d2 is None:
        return d, g, {}
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cx": s1["body"]["cx"] if s1 else None,
        "cy": s1["body"]["cy"] if s1 else None,
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "lv": d2.get("levels_completed"),
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
        "acts": d2.get("available_actions"),
    }
    if info["nd"] or abs(info["dx"]) + abs(info["dy"]) > 0.1:
        print(f"{tag}({x},{y}) Δ=({info['dx']},{info['dy']}) nd={info['nd']} "
              f"ch={info['ch']} mid12={info['mid12']} lv={info['lv']} acts={info['acts']}")
    return d2, g2, info


def arm_hop(sess, hop=39):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    print("enter acts", d.get("available_actions"), "lv", d.get("levels_completed"))
    while int((g == 12).sum()) == 0:
        d, g, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"])
    d = d2
    d, g, info = pad(sess, d, g, hop, "hz ")
    return d, g


def climb_ceil(sess, d, g):
    for i in range(5):
        d, g, info = pad(sess, d, g, 15, f"up{i} ")
        if abs(info.get("dy") or 0) < 0.1:
            break
    return d, g


def maybe_clear(d, g, sess):
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
    print("L5", d1.get("levels_completed"))
    return True


def main():
    key = _api_key()
    sess = Sess(key)
    hits = []
    try:
        sess.open()

        # A: hop39, ceil, pad corners + special clicks
        print("\n=== A ceil corners")
        d, g = arm_hop(sess, 39)
        d, g = climb_ceil(sess, d, g)
        dump(g)
        print("crit", {(x, y): int(g[y, x]) for x, y in [(26, 44), (26, 45), (26, 46), (27, 45), (27, 46)]})
        for x0 in (9, 15, 39, 45, 51, 57):
            for corner in range(0, 5):
                # fresh ceil each time would be too slow — cumulative with restore via dn/up
                d0, g0 = d, g
                d, g, info = pad(sess, d, g, x0, f"A ", corner=corner)
                if info.get("mid12") or int(info.get("lv") or 0) >= 4 or (info.get("cx") or 0) > 28:
                    hits.append({"where": "ceil_corner", "x0": x0, "corner": corner, **info})
                if maybe_clear(d, g, sess):
                    return
                # restore to ceil if moved down
                if (info.get("dy") or 0) > 0.1:
                    d, g, _ = pad(sess, d, g, 15, "restore ")
                elif abs(info.get("dx") or 0) > 0.1:
                    # lost bay — abort A
                    print("left bay, stop A")
                    break
            else:
                continue
            break

        # B: hop9 diagonal land cy54, dig/climb map, hunt
        print("\n=== B hop9 diagonal")
        d, g = arm_hop(sess, 9)
        dump(g)
        print("land", sprite(g), "crit46", int(g[46, 26]) if g.shape[0] > 46 else None)
        # climb all the way
        d, g = climb_ceil(sess, d, g)
        dump(g)
        print("crit", {(x, y): int(g[y, x]) for x, y in [(26, 44), (26, 45), (26, 46)]})
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
        gp = gap11(g)
        for x, y, tag in [
            (28, 40, "mid"),
            (28, 45, "midbot"),
            (26, 45, "gap3"),
            (26, 46, "c0"),
            (round(gp["cx"]), round(gp["cy"]), "gap11") if gp else (43, 29, "gap11"),
        ]:
            d, g, info = xy_click(sess, d, g, int(x), int(y), tag)
            if maybe_clear(d, g, sess):
                return
            if info.get("mid12") or (info.get("cx") or 0) > 28:
                hits.append({"where": "hop9_ceil_click", "tag": tag, **info})

        # C: at ceil with color0@y46 — try DOWN then immediately click mid / (26,45)
        print("\n=== C press into mid")
        d, g = arm_hop(sess, 39)
        d, g = climb_ceil(sess, d, g)
        d, g, _ = pad(sess, d, g, 9, "press ")  # down
        print("after dn crit", {(x, y): int(g[y, x]) for x, y in [(26, 44), (26, 45), (26, 46), (23, 45)]})
        dump(g, 40, 50, 15, 35)
        for x, y, tag in [(28, 45, "mid"), (26, 45, "seam"), (27, 45, "win"), (26, 46, "c0")]:
            d, g, info = xy_click(sess, d, g, x, y, tag)
            if maybe_clear(d, g, sess):
                return

        # D: unarmed left — climb ceil left bay, then sink convert, arm, hop15, see if mid already 12?
        print("\n=== D left-ceil then convert hop")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d, g, _ = pad(sess, d, g, 9, "Lup ")  # up to left ceil
        print("left ceil", sprite(g))
        for _ in range(4):
            d, g, info = pad(sess, d, g, 15, "Ldn ")
            if int((g == 12).sum()):
                break
        print("converted?", int((g == 12).sum()), sprite(g))
        if int((g == 12).sum()):
            c = components(g, 12, 1, 80)[0]
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            g = plane(d2["frame"])
            d = d2
            d, g, info = pad(sess, d, g, 15, "Lhz ")  # high hop
            print("after high hop mid12", bool([c for c in components(g, 12, 1, 80) if c["cx"] > 20]), sprite(g))
            dump(g)
            if maybe_clear(d, g, sess):
                return

        OUT.write_text(json.dumps({"hits": hits, "final_lv": d.get("levels_completed")}, indent=2, default=str), encoding="utf-8")
        print("done hits", hits, "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
