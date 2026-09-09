"""L4 path v2: after first +x, climb bay1; never re-click left gate; hunt mid gate."""
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

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 7: "U", 9: "P", 11: "A", 12: "C"}


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
    al = summarize(g2)["aligned"]
    print(
        f"{tag}x{x0} nd={body_ndiff(g0,g2)} Δ=({dx},{dy}) lv={d2.get('levels_completed')} "
        f"cy={s1['body']['cy'] if s1 else None} cx={s1['body']['cx'] if s1 else None} "
        f"h1={int((g2==1).sum())} h12={int((g2==12).sum())} al={al}"
    )
    return d2, g2, dx, dy


def click_gate_at(sess, d, g, x_min, x_max, tag=""):
    c12 = [c for c in components(g, 12, 1, 80) if x_min <= c["cx"] <= x_max]
    if not c12:
        print(f"{tag}no c12 in x[{x_min},{x_max}]")
        return d, g, False
    c = c12[0]
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
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]

        while int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
        d, g, ok = click_gate_at(sess, d, g, 0, 20, tag="L ")
        assert ok
        d, g, dx, _ = pad(sess, d, g, 39, tag="hz1 ")
        assert abs(dx) > 0.1
        print("\nBAY1")
        dump(g)

        # In bay1: pad15=up, pad9=down (from prior run). Climb with 15.
        # Also probe other env for further +x without touching left gate.
        print("\nProbe env for more +x at bay1 floor")
        for x0 in (45, 51, 57, 39):
            d, g, dx, dy = pad(sess, d, g, x0, tag="probe ")
            if abs(dx) > 0.1:
                print("extra hz!", dx)
                dump(g)

        # Climb up with pad15; if noop try env unblock; watch mid c1→12
        for i in range(15):
            sm = summarize(g)
            if sm["aligned"] or int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR early", d.get("levels_completed")); break
            sp = sprite(g)
            mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] >= 20]
            if mid12:
                print("MID GATE ACTIVE", mid12)
                break
            mid1 = [c for c in components(g, 1, 4, 80) if c["cx"] >= 20]
            print(f"climb{i} sp={sp} mid1={mid1} left12={components(g,12,1,80)}")

            d, g, dx, dy = pad(sess, d, g, 15, tag=f"up{i} ")
            if abs(dy) < 0.1 and abs(dx) < 0.1:
                unblocked = False
                for e in (39, 45, 51, 57, 9):
                    d, g, _, _ = pad(sess, d, g, e, tag="ublk ")
                    # if 9 moved us, note
                    d, g, dx, dy = pad(sess, d, g, 15, tag="retry ")
                    if abs(dy) + abs(dx) > 0.1:
                        unblocked = True
                        break
                if not unblocked:
                    print("stuck climb"); dump(g); break
            # if we somehow got mid12 during up
            if any(c["cx"] >= 20 for c in components(g, 12, 1, 80)):
                print("mid activated during climb")
                break

        mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] >= 20]
        if mid12:
            d, g, ok = click_gate_at(sess, d, g, 20, 40, tag="M ")
            for x0 in (39, 45, 51, 57):
                d, g, dx, dy = pad(sess, d, g, x0, tag="hz2 ")
                if abs(dx) > 0.1:
                    break
            print("AFTER HZ2"); dump(g)

        # If mid not active: try sink into mid from beside it
        if not mid12:
            print("\nTry approach mid by x then sink")
            # dump current
            dump(g)
            # try pad9 down a bit then see if overlapping converts when climbing into window from side
            # Maybe need another +x first — scan all pads once
            for x0 in (9, 15, 39, 45, 51, 57):
                d0, g0 = d, g
                d, g, dx, dy = pad(sess, d, g, x0, tag="scan ")
                if abs(dx) > 0.1:
                    print("got hz", dx); dump(g)
                    break
                # revert not possible — continue from new state carefully
                if any(c["cx"] >= 20 for c in components(g, 12, 1, 80)):
                    print("mid via scan"); break

        # Final: climb/align
        for i in range(20):
            sm = summarize(g)
            print(f"fin{i} al={sm['aligned']} lv={d.get('levels_completed')} {sm['sprite']} gap={sm['gap']}")
            if sm["aligned"] or int(d.get("levels_completed") or 0) >= 4:
                print("SUCCESS", d.get("levels_completed"))
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
                    print("L5", d1.get("levels_completed"))
                break
            sp, gp = sm["sprite"], sm["gap"]
            if not sp or not gp:
                break
            need_dy = gp["cy"] - sp["accent"]["cy"]
            need_dx = gp["cx"] - sp["accent"]["cx"]
            moved = False
            # mid gate click if any
            mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] >= 20]
            if mid12 and abs(need_dx) > 2:
                d, g, _ = click_gate_at(sess, d, g, 20, 40, tag="M2 ")
                for x0 in (39, 45, 51, 57):
                    d, g, dx, dy = pad(sess, d, g, x0, tag="hz ")
                    if abs(dx) > 0.1:
                        moved = True
                        break
            if not moved:
                # try pads favoring needed direction
                order = (15, 9, 39, 45, 51, 57) if need_dy < 0 else (9, 15, 39, 45, 51, 57)
                for x0 in order:
                    d, g, dx, dy = pad(sess, d, g, x0, tag="mv ")
                    if need_dy < 0 and dy < -0.1:
                        moved = True
                        break
                    if need_dx > 2 and dx > 0.1:
                        moved = True
                        break
                    if need_dx < -2 and dx < -0.1:
                        moved = True
                        break
                    if abs(dx) + abs(dy) > 0.1 and abs(need_dx) + abs(need_dy) < 8:
                        moved = True
                        break
            if not moved:
                print("stalled"); dump(g); break

        (ROOT / "tests/fixtures/vc33_l4_path_v2.json").write_text(
            json.dumps({"final": summarize(g), "levels": d.get("levels_completed")}, indent=2, default=float),
            encoding="utf-8",
        )
    finally:
        sess.close()


if __name__ == "__main__":
    main()
