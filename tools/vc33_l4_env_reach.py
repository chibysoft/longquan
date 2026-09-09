"""L4: env min-y reach beside mid; alt clicks; actions scan."""
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

OUT = ROOT / "tests/fixtures/vc33_l4_env_reach.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 7: "U", 9: "P", 11: "A", 12: "C"}


def dump(g, y0=28, y1=55, x0=20, x1=50):
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
    to0 = np.argwhere((g0 == 3) & (g2 == 0))
    to3 = np.argwhere((g0 == 0) & (g2 == 3))

    def bb(a):
        if len(a) == 0:
            return None
        return [int(a[:, 1].min()), int(a[:, 1].max()), int(a[:, 0].min()), int(a[:, 0].max())]

    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cy": s1["body"]["cy"] if s1 else None,
        "cx": s1["body"]["cx"] if s1 else None,
        "to0": bb(to0),
        "to3": bb(to3),
        "min0y_x30": min_zero_y(g2, 30, 35),
        "mid_right0": mid_right_zeros(g2),
        "gap0_midy": gap0_in_midy(g2),
        "h12": int((g2 == 12).sum()),
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "lv": d2.get("levels_completed"),
        "acts": d2.get("available_actions"),
        "nd": body_ndiff(g0, g2),
    }
    print(
        f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) cy={info['cy']} "
        f"3→0={info['to0']} midR0={info['mid_right0']} gap0={info['gap0_midy']} "
        f"mid12={info['mid12']} lv={info['lv']} acts={info['acts']}"
    )
    return d2, g2, info


def min_zero_y(g, x0, x1):
    ys = [int(y) for y, x in np.argwhere(g == 0) if x0 <= x <= x1]
    return min(ys) if ys else None


def mid_right_zeros(g):
    # x30 (just right of mid x29) within mid y 34-45
    return [(30, y) for y in range(34, 46) if int(g[y, 30]) == 0]


def gap0_in_midy(g):
    return [(x, y) for x in (24, 25, 26) for y in range(34, 46) if int(g[y, x]) == 0]


def xy(sess, d, g, x, y, tag=""):
    g0, s0 = g, sprite(g)
    d2 = click(sess, x, y)
    if d2 is None:
        return d, g, {}
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    info = {
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "lv": d2.get("levels_completed"),
        "acts": d2.get("available_actions"),
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "gap0": gap0_in_midy(g2),
        "midR0": mid_right_zeros(g2),
    }
    if info["nd"] or abs(info["dx"]) + abs(info["dy"]) > 0.1 or info["mid12"] or int(info["lv"] or 0) >= 4:
        print(f"{tag}({x},{y}) nd={info['nd']} ch={info['ch']} Δ=({info['dx']},{info['dy']}) "
              f"mid12={info['mid12']} lv={info['lv']} acts={info['acts']} gap0={info['gap0']}")
    return d2, g2, info


def arm_hop(sess, hop=39):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"])
    d = d2
    d, g, _ = pad(sess, d, g, hop, "hz ")
    return d, g


def climb(sess, d, g):
    for i in range(6):
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
    return True


def main():
    key = _api_key()
    sess = Sess(key)
    log = []
    try:
        sess.open()

        # A: floor env spam — how high can 3→0 go at x30+?
        print("\n=== A floor env reach")
        d, g = arm_hop(sess, 39)
        for e in (39, 45, 51, 57, 45, 51, 57, 39):
            d, g, info = pad(sess, d, g, e, "A ")
            log.append({"phase": "floor_env", **info})
            if maybe_clear(d, g, sess):
                return
        print("floor dump")
        dump(g)
        print("min0y x30-40", min_zero_y(g, 30, 40), "midR0", mid_right_zeros(g), "gap0", gap0_in_midy(g))

        # B: climb interleaved with env — track mid-right zeros
        print("\n=== B climb+env")
        d, g = arm_hop(sess, 39)
        for i in range(5):
            d, g, info = pad(sess, d, g, 15, f"Bup{i} ")
            log.append({"phase": f"climb{i}", **info})
            if abs(info.get("dy") or 0) < 0.1:
                break
            for e in (39, 45, 51):
                d, g, info = pad(sess, d, g, e, f"Be{i} ")
                log.append({"phase": f"env@{info.get('cy')}", **info})
                if info.get("mid_right0") or info.get("gap0_midy") or info.get("mid12"):
                    print("HIT", info)
                if maybe_clear(d, g, sess):
                    return
        print("ceil+env dump")
        dump(g, 28, 50, 18, 48)
        print("crit", {
            "gap0": gap0_in_midy(g),
            "midR0": mid_right_zeros(g),
            "x30col": [int(g[y, 30]) for y in range(34, 50)],
            "x26col": [int(g[y, 26]) for y in range(34, 50)],
            "min0y30": min_zero_y(g, 30, 40),
        })

        # C: at ceil — click beam/gap/unique colors + mid right edge
        print("\n=== C alt clicks at ceil")
        d, g = arm_hop(sess, 39)
        d, g = climb(sess, d, g)
        gp = gap11(g)
        targets = [
            (30, 45, "midR"),
            (30, 40, "midR2"),
            (30, 46, "midR3"),
            (26, 46, "c0"),
            (26, 45, "seam"),
            (28, 45, "midbot"),
            (28, 34, "midtop"),
            (42, 46, "beam"),
            (round(gp["cx"]), round(gp["cy"]), "gap") if gp else (43, 29, "gap"),
            (43, 35, "beam2"),
            (20, 40, "above"),
            (23, 42, "bodyR"),
        ]
        # also sample color5/7 if present near
        for y, x in np.argwhere((g == 5) | (g == 7)):
            if 25 <= x <= 45 and 28 <= y <= 50:
                targets.append((int(x), int(y), f"c{int(g[y,x])}"))
                if len(targets) > 30:
                    break
        seen = set()
        for x, y, tag in targets:
            if (x, y) in seen:
                continue
            seen.add((x, y))
            d, g, info = xy(sess, d, g, int(x), int(y), tag)
            if info.get("mid12") or int(info.get("lv") or 0) >= 4:
                log.append({"phase": "alt", "tag": tag, **info})
            if maybe_clear(d, g, sess):
                return

        # D: falsify mid-gate — from left bay only, env+climb+gap spam for levels
        print("\n=== D left-only levels hunt")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d, g, _ = pad(sess, d, g, 9, "Lup ")
        for e in (39, 45, 51, 57):
            d, g, info = pad(sess, d, g, e, "Lenv ")
            if maybe_clear(d, g, sess):
                return
        gp = gap11(g)
        if gp:
            d, g, info = xy(sess, d, g, round(gp["cx"]), round(gp["cy"]), "Lgap")
        # sink convert arm hop oscillate
        while int((g == 12).sum()) == 0 and sprite(g)["body"]["cy"] < 54:
            d, g, info = pad(sess, d, g, 15, "Ldn ")
        if int((g == 12).sum()):
            c = components(g, 12, 1, 80)[0]
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            g = plane(d2["frame"]); d = d2
            for _ in range(4):
                d, g, info = pad(sess, d, g, 39, "Lhz ")
                if maybe_clear(d, g, sess):
                    return
                if abs(info.get("dx") or 0) < 0.1:
                    # rearm
                    if int((g == 12).sum()):
                        c = components(g, 12, 1, 80)[0]
                        d2 = click(sess, round(c["cx"]), round(c["cy"]))
                        g = plane(d2["frame"]); d = d2

        OUT.write_text(json.dumps({"log_tail": log[-30:], "final_lv": d.get("levels_completed")}, indent=2, default=str), encoding="utf-8")
        print("done lv", d.get("levels_completed"), "gap0", gap0_in_midy(g), "midR0", mid_right_zeros(g))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
