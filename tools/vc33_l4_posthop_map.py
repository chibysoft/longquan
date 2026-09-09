"""L4: after gate hop, map color0 vs mid; try bottom-right path; ceiling adj moves."""
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
OUT = ROOT / "tests/fixtures/vc33_l4_posthop_map.json"


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
        f"mid12={bool([c for c in components(g2,12,1,80) if c['cx']>20])} "
        f"lv={d2.get('levels_completed')}"
    )
    return d2, g2, dx, dy


def arm_hop(sess, hop="gate"):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"])
    d = d2
    if hop == "gate":
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"])
        d = d2
        print("hop via gate2", sprite(g))
    else:
        d, g, _, _ = pad(sess, d, g, int(hop), tag="hop ")
    return d, g


def color0_touch_mid(g):
    mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if not mid:
        mid = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    if not mid:
        return {"adj4": [], "adj8": [], "in_win_y_gap": []}
    m = mid[0]
    cells0 = [(int(x), int(y)) for y, x in np.argwhere(g == 0)]
    adj4, adj8, in_gap = [], [], []
    for x, y in cells0:
        if m["x0"] - 1 <= x <= m["x1"] + 1 and m["y0"] <= y <= m["y1"]:
            if x < m["x0"] or x > m["x1"]:
                in_gap.append((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if m["x0"] <= nx <= m["x1"] and m["y0"] <= ny <= m["y1"]:
                adj4.append((x, y))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if m["x0"] <= nx <= m["x1"] and m["y0"] <= ny <= m["y1"]:
                    adj8.append((x, y))
    return {
        "adj4": sorted(set(adj4)),
        "adj8": sorted(set(adj8)),
        "in_win_y_gap": sorted(set(in_gap)),
        "mid": m,
    }


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        d, g = arm_hop(sess, "gate")
        touch = color0_touch_mid(g)
        print("POST HOP touch", touch)
        print("POST HOP full")
        dump(g)
        out["post_hop"] = {"sprite": sprite(g), "touch": touch, "hist": summarize(g)["hist"]}

        # env while c12 still on — watch touch
        print("\nENV with c12")
        for x0 in (39, 45, 51, 57, 39, 45):
            d, g, dx, dy = pad(sess, d, g, x0, tag="env ")
            t = color0_touch_mid(g)
            if t["adj4"] or t["in_win_y_gap"] or abs(dx) > 0.1:
                print("  touch", t)
            if abs(dx) > 0.1:
                dump(g)
                break

        # deep then env — bottom right corridor?
        print("\nDEEP + ENV")
        for i in range(6):
            d, g, dx, dy = pad(sess, d, g, 9, tag=f"dn{i} ")
            if abs(dy) < 0.1:
                break
        dump(g, 48, 63, 0, 63)
        for x0 in (39, 45, 51, 57, 39, 45, 51, 57):
            d, g, dx, dy = pad(sess, d, g, x0, tag="benv ")
            if abs(dx) > 0.1:
                print("BOTTOM HZ", dx)
                dump(g)
                break
        out["deep"] = {"sprite": sprite(g), "touch": color0_touch_mid(g)}

        # fresh: hop, climb ceiling, at diagonal-touch state try every pad once
        print("\nCEILING PAD SWEEP")
        d, g = arm_hop(sess, 39)
        for i in range(5):
            d, g, _, dy = pad(sess, d, g, 15, tag=f"up{i} ")
            if abs(dy) < 0.1:
                break
        print("ceiling touch", color0_touch_mid(g))
        dump(g, 40, 50, 15, 35)
        for x0 in (9, 15, 39, 45, 51, 57):
            d, g, dx, dy = pad(sess, d, g, x0, tag="sweep ")
            t = color0_touch_mid(g)
            if t["adj4"] or any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("  INTEREST", t)
            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR")
                break
            # restore height if we went down
            if dy > 0.1:
                d, g, _, _ = pad(sess, d, g, 15, tag="restore ")

        out["final"] = summarize(g)
        OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
