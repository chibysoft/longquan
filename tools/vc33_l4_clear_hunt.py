"""L4 clear hunt: 2down → click c12 → +x → climb mid gate → align gap11."""
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
from tools.vc33_l4_pad_map import (  # noqa: E402
    FIXTURE_L4_CLEAR,
    FIXTURE_L5,
    components,
    enter_l4,
    gap11,
    sprite,
    summarize,
)

OUT = ROOT / "tests/fixtures/vc33_l4_clear_hunt.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 7: "U", 9: "P", 11: "A", 12: "C"}


def dump(g, y0=28, y1=56, x0=0, x1=55):
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(x0, x1 + 1))
        print(f"{y:02d}|{row}")


def try_click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print(f"  HTTP {e}")
        return None


def click_pad(sess, d, g, x0, tag=""):
    pad = next(p for p in pads_sorted(g) if p["x0"] == x0)
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    g0, s0 = g, sprite(g)
    d2 = try_click(sess, *xy)
    if d2 is None:
        return d, g, 0, 0, False
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    ddx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    ddy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(
        f"{tag}pad{x0} body={body_ndiff(g0,g2)} Δ=({ddx},{ddy}) "
        f"lv={d2.get('levels_completed')} sp={sprite(g2)} "
        f"c1={len(components(g2,1,4,80))} c12={len(components(g2,12,1,80))} "
        f"aligned={summarize(g2)['aligned']}"
    )
    return d2, g2, ddx, ddy, True


def click_xy(sess, d, g, x, y, tag=""):
    g0 = g
    d2 = try_click(sess, x, y)
    if d2 is None:
        return d, g, False
    g2 = plane(d2["frame"])
    print(f"{tag}click({x},{y}) body={body_ndiff(g0,g2)} ch={body_changes(g0,g2)} lv={d2.get('levels_completed')}")
    return d2, g2, True


def best_vertical(sess, d, g, want_dy_sign):
    """Try pad9 and pad15; return the one that moves with desired dy sign (-1 up, +1 down)."""
    best = None
    for x0 in (9, 15):
        # probe by actually clicking — caller should prefer small steps
        d2, g2, dx, dy, ok = click_pad(sess, d, g, x0, tag="  probe ")
        if not ok:
            return d, g, False
        if dy * want_dy_sign > 0.1:
            return d2, g2, True
        # undo if wrong direction and opposite pad exists — can't undo; track
        d, g = d2, g2
        if abs(dy) > 0.1:
            best = (d2, g2, dy)
    return d, g, abs(best[2]) > 0.1 if best else False


def main():
    key = _api_key()
    sess = Sess(key)
    log = []
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        print("START", summarize(g)["sprite"])

        # Phase A: sink until left gate 1→12
        for i in range(4):
            c12 = components(g, 12, 1, 80)
            if c12:
                print(f"gate12 after {i} downs", c12[0])
                break
            d, g, _, _, ok = click_pad(sess, d, g, 15, tag=f"sink{i} ")
            if not ok:
                return
        else:
            print("no c12"); dump(g); return

        # click activated gate
        c = components(g, 12, 1, 80)[0]
        d, g, ok = click_xy(sess, d, g, round(c["cx"]), round(c["cy"]), tag="gate ")
        if not ok:
            return

        # Phase B: try env pads for +x
        moved_x = False
        for x0 in (39, 45, 51, 57, 9, 15):
            d, g, dx, dy, ok = click_pad(sess, d, g, x0, tag="hz ")
            if not ok:
                return
            if abs(dx) > 0.1:
                moved_x = True
                log.append({"phase": "hz1", "x0": x0, "dx": dx})
                break
        if not moved_x:
            print("no +x after gate"); dump(g); return

        print("\nAFTER +x")
        dump(g)

        # Phase C: navigate — prefer climbing toward gap y=29, convert mid gate
        for step in range(40):
            sm = summarize(g)
            sp, gp = sm["sprite"], sm["gap"]
            if sm["aligned"] or int(d.get("levels_completed") or 0) >= 4:
                print("SUCCESS", sm)
                break
            if not sp or not gp:
                print("lost sprite/gap"); break

            a = sp["accent"]
            need_dx = gp["cx"] - a["cx"]
            need_dy = gp["cy"] - a["cy"]  # negative => need up
            print(f"\nstep{step} need=({need_dx:.1f},{need_dy:.1f}) {sp}")

            c12s = components(g, 12, 1, 80)
            # if a c12 exists near sprite x, click it
            if c12s:
                for c in c12s:
                    if abs(c["cx"] - sp["body"]["cx"]) < 20:
                        d, g, ok = click_xy(sess, d, g, round(c["cx"]), round(c["cy"]), tag="gate2 ")
                        if not ok:
                            return
                        # try +x
                        for x0 in (39, 45, 51, 57):
                            d, g, dx, dy, ok = click_pad(sess, d, g, x0, tag="hz2 ")
                            if not ok:
                                return
                            if abs(dx) > 0.1:
                                break
                        break

            # convert nearby c1 by overlapping (go down into it if x-aligned enough)
            c1s = components(g, 1, 4, 80)
            for c in c1s:
                if abs(c["cx"] - sp["body"]["cx"]) < 12 and sp["body"]["y1"] < c["y1"] + 2:
                    # try sink into it
                    for x0 in (9, 15):
                        d, g, dx, dy, ok = click_pad(sess, d, g, x0, tag="sink2 ")
                        if not ok:
                            return
                        if dy > 0.1:
                            break
                    break

            # move toward gap: try both vertical pads, pick useful
            moved = False
            # prefer horizontal if need_dx large and we have gate ready — already tried
            order = (9, 15, 39, 45, 51, 57)
            if need_dy < -1:
                # need up: try both verts
                for x0 in (9, 15):
                    d, g, dx, dy, ok = click_pad(sess, d, g, x0, tag="up ")
                    if not ok:
                        return
                    if dy < -0.1 or abs(dx) > 0.1:
                        moved = True
                        break
                    if dy > 0.1:
                        # went down, try reverse next
                        continue
            elif need_dy > 1:
                for x0 in (15, 9):
                    d, g, dx, dy, ok = click_pad(sess, d, g, x0, tag="dn ")
                    if not ok:
                        return
                    if dy > 0.1 or abs(dx) > 0.1:
                        moved = True
                        break
            else:
                # y close — hunt x
                for x0 in (39, 45, 51, 57, 9, 15):
                    d, g, dx, dy, ok = click_pad(sess, d, g, x0, tag="fin ")
                    if not ok:
                        return
                    if abs(dx) + abs(dy) > 0.1:
                        moved = True
                        break

            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEARED levels>=4")
                FIXTURE_L4_CLEAR.write_text(
                    json.dumps({"frame": d["frame"], "levels_completed": d.get("levels_completed")}, indent=2),
                    encoding="utf-8",
                )
                # sync L5
                d1 = sess.action("ACTION1")
                FIXTURE_L5.write_text(
                    json.dumps({"frame": d1["frame"], "levels_completed": d1.get("levels_completed")}, indent=2),
                    encoding="utf-8",
                )
                print("L5 sync", d1.get("levels_completed"), summarize(plane(d1["frame"])))
                break

            if summarize(g)["aligned"]:
                print("ALIGNED but levels?", d.get("levels_completed"))
                dump(g)
                break

            if not moved:
                print("stalled"); dump(g); break

        out = {"log": log, "final": summarize(g), "levels": d.get("levels_completed")}
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
