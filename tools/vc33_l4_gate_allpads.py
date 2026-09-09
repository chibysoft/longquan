"""L4: after left gate, map EVERY pad; then pursue mid from diagonal landings."""
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
from tools.vc33_l4_pad_map import components, enter_l4, sprite, summarize  # noqa: E402

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}
OUT = ROOT / "tests/fixtures/vc33_l4_gate_pad_map.json"


def dump(g, y0=28, y1=56, x0=0, x1=55):
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
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(
        f"{tag}x{x0} nd={body_ndiff(g0,g2)} Δ=({dx},{dy}) "
        f"cx={s1['body']['cx'] if s1 else None} cy={s1['body']['cy'] if s1 else None} "
        f"h12={int((g2==12).sum())} ch={body_changes(g0,g2)} "
        f"lv={d2.get('levels_completed')} al={summarize(g2)['aligned']}"
    )
    return d2, g2, dx, dy


def to_armed_left(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        # use whichever pad goes down from start
        d, g, dx, dy = pad(sess, d, g, 15, tag="sink ")
        if abs(dy) < 0.1 and int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 9, tag="sinkb ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"])
    print("GATE", c)
    return d2, g


def main():
    key = _api_key()
    sess = Sess(key)
    results = []
    try:
        sess.open()
        for x0 in (9, 15, 39, 45, 51, 57):
            print(f"\n==== armed-left then pad{x0}")
            d, g = to_armed_left(sess)
            sp0 = sprite(g)
            d, g, dx, dy = pad(sess, d, g, x0, tag="map ")
            results.append({
                "after_gate_pad": x0,
                "dx": dx,
                "dy": dy,
                "sp0": sp0,
                "sp1": sprite(g),
                "h12": int((g == 12).sum()),
                "levels": d.get("levels_completed"),
            })
            dump(g)

        # Pursuit: gate + pad9 (diagonal), then try to convert mid / further hz
        print("\n==== PURSUIT gate+9 then explore")
        d, g = to_armed_left(sess)
        d, g, _, _ = pad(sess, d, g, 9, tag="diag ")
        dump(g)
        # at cy=54 bay1: try climb and watch mid; also rearm at 51
        for i in range(8):
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID12", components(g, 12, 1, 80))
                c = [c for c in components(g, 12, 1, 80) if c["cx"] > 20][0]
                d2 = click(sess, round(c["cx"]), round(c["cy"]))
                g = plane(d2["frame"]); d = d2
                for e in (9, 15, 39, 45, 51, 57):
                    d, g, dx, dy = pad(sess, d, g, e, tag="mhz ")
                    if abs(dx) > 0.1:
                        print("MID HOP", dx)
                        dump(g)
                        break
                break
            # prefer moving toward mid / up
            sp = sprite(g)
            print(f"pursue{i}", sp, "c12", components(g, 12, 1, 80))
            if sp and abs(sp["body"]["cy"] - 51) < 1 and int((g == 12).sum()) > 0:
                # at activation band with left c12 — don't click left; try climb
                d, g, _, _ = pad(sess, d, g, 15, tag="pup ")
                continue
            # try pads that move
            moved = False
            for x0 in (15, 9, 39, 45, 51, 57):
                d, g, dx, dy = pad(sess, d, g, x0, tag="p ")
                if abs(dx) + abs(dy) > 0.1:
                    moved = True
                    break
            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR")
                break
            if not moved:
                print("stuck"); dump(g); break

        OUT.write_text(json.dumps({"map": results, "final": summarize(g)}, indent=2, default=float), encoding="utf-8")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
