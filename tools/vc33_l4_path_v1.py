"""L4 deliberate path: gate1 → +x → map pads → mid gate → +x → climb to gap."""
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

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 7: "U", 9: "P", 11: "A", 12: "C"}
OUT = ROOT / "tests/fixtures/vc33_l4_path_v1.json"


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
    xy = (int(round(p["cx"])), int(round(p["cy"])))
    g0, s0 = g, sprite(g)
    d2 = click(sess, *xy)
    if d2 is None:
        return d, g, 0.0, 0.0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0.0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0.0
    print(
        f"{tag}x{x0} nd={body_ndiff(g0,g2)} Δ=({dx},{dy}) lv={d2.get('levels_completed')} "
        f"body={s1['body'] if s1 else None} acc={s1.get('accent') if s1 else None} "
        f"h1={(g2==1).sum()} h12={(g2==12).sum()} al={summarize(g2)['aligned']}"
    )
    return d2, g2, dx, dy


def gate_click(sess, d, g, tag=""):
    c12 = components(g, 12, 1, 80)
    if not c12:
        print(f"{tag}no c12")
        return d, g, False
    c = min(c12, key=lambda t: abs(t["cx"] - (sprite(g)["body"]["cx"] if sprite(g) else 0)))
    xy = (int(round(c["cx"])), int(round(c["cy"])))
    g0 = g
    d2 = click(sess, *xy)
    if d2 is None:
        return d, g, False
    g2 = plane(d2["frame"])
    print(f"{tag}gate{xy} nd={body_ndiff(g0,g2)} ch={body_changes(g0,g2)}")
    return d2, g2, True


def main():
    key = _api_key()
    sess = Sess(key)
    steps = []
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]

        # sink to activate left gate
        while (g == 12).sum() == 0:
            d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
        d, g, ok = gate_click(sess, d, g, tag="A ")
        assert ok

        # +x via env (prefer 39)
        for x0 in (39, 45, 51, 57):
            d, g, dx, dy = pad(sess, d, g, x0, tag="Ahz ")
            if abs(dx) > 0.1:
                steps.append(("hz1", x0, dx))
                break
        else:
            print("FAIL no hz1"); dump(g); return

        print("\n=== bay1")
        dump(g)

        # map vertical: which pad goes up?
        print("\n=== map verts (will displace)")
        # save by re-deriving: click 9 then 15 note signs from current
        d, g, dx, dy = pad(sess, d, g, 9, tag="map ")
        sign9 = dy
        d, g, dx, dy = pad(sess, d, g, 15, tag="map ")
        sign15 = dy
        print(f"pad9 dy-sign≈{sign9}, pad15 dy-sign≈{sign15}")

        # climb toward mid window (y34-45). Accent should enter/overlap c1
        # Prefer pad with negative dy (up)
        up_pad = 9 if sign9 < -0.1 else (15 if sign15 < -0.1 else None)
        dn_pad = 15 if sign15 > 0.1 else (9 if sign9 > 0.1 else None)
        # After map clicks we may have moved; re-detect
        if up_pad is None:
            # probe again from current
            for x0 in (9, 15):
                d, g, dx, dy = pad(sess, d, g, x0, tag="remap ")
                if dy < -0.1:
                    up_pad = x0
                if dy > 0.1:
                    dn_pad = x0

        print(f"up_pad={up_pad} dn_pad={dn_pad}")

        # Climb until we can activate mid c1 (1→12) or reach gap y
        for i in range(12):
            sm = summarize(g)
            if sm["aligned"] or int(d.get("levels_completed") or 0) >= 4:
                print("EARLY CLEAR", sm); break
            if (g == 12).sum() > 0:
                print("c12 present", components(g, 12, 1, 80))
                break
            # if overlapping mid c1 vertically enough while to its left/right — sink
            sp = sprite(g)
            mid = [c for c in components(g, 1, 4, 80) if c["x0"] >= 20]
            if sp and mid:
                m = mid[0]
                # if sprite x past left of mid and y near mid bottom, sink
                if sp["body"]["x0"] >= m["x0"] - 8 and sp["body"]["y0"] <= m["y1"] + 3:
                    print("near mid, sink to convert")
                    if dn_pad is not None:
                        d, g, _, _ = pad(sess, d, g, dn_pad, tag="conv ")
                    continue
            if up_pad is None:
                for x0 in (9, 15):
                    d, g, dx, dy = pad(sess, d, g, x0, tag="findup ")
                    if dy < -0.1:
                        up_pad = x0
                        break
                if up_pad is None:
                    print("no up"); dump(g); break
            d, g, dx, dy = pad(sess, d, g, up_pad, tag=f"climb{i} ")
            if abs(dy) < 0.1 and abs(dx) < 0.1:
                # blocked — env then retry
                for e in (39, 45, 51, 57):
                    d, g, _, _ = pad(sess, d, g, e, tag="env ")
                    d, g, dx, dy = pad(sess, d, g, up_pad, tag="retry ")
                    if abs(dy) + abs(dx) > 0.1:
                        break
                else:
                    print("climb stuck"); dump(g); break

        if (g == 12).sum() > 0:
            d, g, ok = gate_click(sess, d, g, tag="B ")
            for x0 in (39, 45, 51, 57):
                d, g, dx, dy = pad(sess, d, g, x0, tag="Bhz ")
                if abs(dx) > 0.1:
                    steps.append(("hz2", x0, dx))
                    break
            print("\n=== after hz2")
            dump(g)

        # final align hunt
        for i in range(25):
            sm = summarize(g)
            print(f"align{i}", sm["sprite"], "gap", sm["gap"], "al", sm["aligned"], "lv", d.get("levels_completed"))
            if sm["aligned"] or int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR?", d.get("levels_completed"))
                if int(d.get("levels_completed") or 0) >= 4:
                    (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
                        json.dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
                        encoding="utf-8",
                    )
                    d1 = sess.action("ACTION1")
                    (ROOT / "tests/fixtures/vc33_l5_frame_live.json").write_text(
                        json.dumps({"frame": d1["frame"], "levels": d1.get("levels_completed")}, indent=2),
                        encoding="utf-8",
                    )
                    print("synced L5", d1.get("levels_completed"))
                break
            sp, gp = sm["sprite"], sm["gap"]
            if not sp or not gp:
                break
            need_dy = gp["cy"] - sp["accent"]["cy"]
            need_dx = gp["cx"] - sp["accent"]["cx"]
            # pick pad
            tried = False
            if abs(need_dx) > abs(need_dy) and abs(need_dx) > 2:
                for x0 in (39, 45, 51, 57):
                    d, g, dx, dy = pad(sess, d, g, x0, tag="finx ")
                    tried = True
                    if abs(dx) > 0.1:
                        break
            else:
                # vertical toward need_dy
                for x0 in (9, 15):
                    d, g, dx, dy = pad(sess, d, g, x0, tag="finy ")
                    tried = True
                    if need_dy < 0 and dy < -0.1:
                        break
                    if need_dy > 0 and dy > 0.1:
                        break
                    if abs(dx) > 0.1:
                        break
            if not tried:
                break
            if abs(dx) + abs(dy) < 0.1 and abs(need_dx) + abs(need_dy) > 2:
                # stuck
                for e in (39, 45, 51, 57, 9, 15):
                    d, g, dx, dy = pad(sess, d, g, e, tag="unstuck ")
                    if abs(dx) + abs(dy) > 0.1:
                        break
                else:
                    print("final stuck"); dump(g); break

        OUT.write_text(
            json.dumps({"steps": steps, "final": summarize(g), "levels": d.get("levels_completed")}, indent=2, default=float),
            encoding="utf-8",
        )
    finally:
        sess.close()


if __name__ == "__main__":
    main()
