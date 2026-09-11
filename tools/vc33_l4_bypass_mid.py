"""L4 H57 (d): can levels 3→4 while mid stays kind=1?

Does NOT try to convert mid. Success = levels>=4 with mid never kind=12.

Families (fresh enter each):
  G  bay1 ceiling — env parity + gap/accent ritual
  L  bay0 c12 — unarmed/armed env+gap
  S  shuttle bay0↔bay1 + gap each land
  F  deep floor bay1 + env + gap
  N  no-left-convert — up/env/gap/mid only
  C  convert@51 then gap (unarmed/armed/hop15)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_bypass_mid.json"
CLEAR = ROOT / "tests/fixtures/vc33_l4_clear_frame.json"
L5 = ROOT / "tests/fixtures/vc33_l5_frame_live.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    return click(sess, int(round(p["cx"])), int(round(p["cy"])))


def mid_kind(g):
    if [c for c in components(g, 12, 1, 80) if c["cx"] > 20]:
        return 12
    if [c for c in components(g, 1, 4, 80) if c["cx"] > 20]:
        return 1
    return None


def left12(g):
    cs = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
    return cs[0] if cs else None


def snap(d, g):
    sp = sprite(g)
    gp = gap11(g)
    acc = sp["accent"] if sp else None
    return {
        "lv": d.get("levels_completed"),
        "mid": mid_kind(g),
        "h12": int((g == 12).sum()),
        "cx": sp["body"]["cx"] if sp else None,
        "cy": sp["body"]["cy"] if sp else None,
        "dx": (gp["x0"] - acc["x1"]) if gp and acc else None,
        "dy": (gp["y0"] - acc["y1"]) if gp and acc else None,
    }


def save_clear(d, sess):
    CLEAR.write_text(
        json.dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
        encoding="utf-8",
    )
    try:
        d1 = sess.action("ACTION1")
        L5.write_text(
            json.dumps({"frame": d1["frame"], "levels": d1.get("levels_completed")}, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print("ACTION1 after clear failed", e)


def check(d, g, label, mid_seen, sess):
    mk = mid_kind(g)
    mid_seen.add(mk)
    lv = int(d.get("levels_completed") or 0)
    if mk == 12:
        print(f"  !! mid became 12 during {label}")
    if lv >= 4:
        print(f"*** CLEAR {label} lv={lv} mid={mk}")
        if mk != 12:
            save_clear(d, sess)
        return True
    return False


def setup_convert(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    for _ in range(8):
        if left12(g):
            break
        d2 = pad(sess, g, 15)
        if d2 is None:
            break
        g = plane(d2["frame"]); d = d2
    return d, g


def arm_hop(sess, d, g, hop=39):
    c = left12(g)
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d2 = pad(sess, g, hop)
    return d2, plane(d2["frame"])


def climb_ceil(sess, d, g, max_ups=6):
    for _ in range(max_ups):
        cy0 = sprite(g)["body"]["cy"]
        d2 = pad(sess, g, 15)
        if d2 is None:
            break
        g2 = plane(d2["frame"])
        if abs(sprite(g2)["body"]["cy"] - cy0) < 0.1:
            return d2, g2
        g = g2; d = d2
    return d, g


def click_gap(sess, g):
    gp = gap11(g)
    return click(sess, round(gp["cx"]), round(gp["cy"]))


def click_accent(sess, g):
    a = sprite(g)["accent"]
    return click(sess, round(a["cx"]), round(a["cy"]))


def run_family(sess, label, fn):
    print(f"\n## {label}")
    mid_seen = set()
    log = []
    d, g, cleared = fn(sess, mid_seen, log)
    s = snap(d, g)
    row = {
        "label": label,
        "final": s,
        "mid_seen": sorted(x for x in mid_seen if x is not None),
        "cleared": cleared,
        "log_n": len(log),
        "log_tail": log[-6:],
    }
    print(
        f"  final lv={s['lv']} mid={s['mid']} cy={s['cy']} cx={s['cx']} "
        f"dx={s['dx']} dy={s['dy']} mid_seen={row['mid_seen']}"
    )
    return row, cleared


def main():
    key = _api_key()
    sess = Sess(key)
    rows = []
    try:
        sess.open()

        def G_ceil(sess, mid_seen, log):
            d, g = setup_convert(sess)
            d, g = arm_hop(sess, d, g, 39)
            d, g = climb_ceil(sess, d, g)
            if check(d, g, "G/land", mid_seen, sess):
                return d, g, True
            for i, x0 in enumerate((39, 45, 51, 57, 39, 45, 51, 57)):
                d2 = pad(sess, g, x0)
                if d2 is None:
                    continue
                g = plane(d2["frame"]); d = d2
                log.append({"pad": x0, **snap(d, g)})
                if check(d, g, f"G/env{x0}", mid_seen, sess):
                    return d, g, True
                for fn, tag in ((click_gap, "gap"), (click_accent, "acc")):
                    d2 = fn(sess, g)
                    if d2 is None:
                        continue
                    g = plane(d2["frame"]); d = d2
                    if check(d, g, f"G/{tag}", mid_seen, sess):
                        return d, g, True
            for x0 in (9, 15, 39, 45, 51, 57):
                d2 = pad(sess, g, x0)
                if d2 is None:
                    continue
                g = plane(d2["frame"]); d = d2
                if check(d, g, f"G/pad{x0}", mid_seen, sess):
                    return d, g, True
                d2 = click_gap(sess, g)
                if d2:
                    g = plane(d2["frame"]); d = d2
                    if check(d, g, f"G/pad{x0}_gap", mid_seen, sess):
                        return d, g, True
            return d, g, False

        def L_bay0(sess, mid_seen, log):
            d, g = setup_convert(sess)
            if check(d, g, "L/conv", mid_seen, sess):
                return d, g, True
            for x0 in (39, 45, 51, 57):
                d2 = pad(sess, g, x0)
                if d2:
                    g = plane(d2["frame"]); d = d2
                d2 = click_gap(sess, g)
                if d2:
                    g = plane(d2["frame"]); d = d2
                    log.append({"unarmed": x0, **snap(d, g)})
                    if check(d, g, "L/unarmed_gap", mid_seen, sess):
                        return d, g, True
            c = left12(g)
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            g = plane(d2["frame"]); d = d2
            for x0 in (39, 45, 51, 57):
                d2 = pad(sess, g, x0)
                if d2 is None:
                    continue
                g = plane(d2["frame"]); d = d2
                d2 = click_gap(sess, g)
                if d2:
                    g = plane(d2["frame"]); d = d2
                log.append({"armed": x0, **snap(d, g)})
                if check(d, g, "L/armed", mid_seen, sess):
                    return d, g, True
            return d, g, False

        def S_shuttle(sess, mid_seen, log):
            d, g = setup_convert(sess)
            d, g = arm_hop(sess, d, g, 39)
            for i in range(4):
                d2 = click_gap(sess, g)
                if d2:
                    g = plane(d2["frame"]); d = d2
                    if check(d, g, f"S/gap{i}", mid_seen, sess):
                        return d, g, True
                c = left12(g)
                if not c:
                    break
                d2 = click(sess, round(c["cx"]), round(c["cy"]))
                g = plane(d2["frame"]); d = d2
                d2 = pad(sess, g, 39)
                if d2 is None:
                    break
                g = plane(d2["frame"]); d = d2
                log.append({"shuttle": i, **snap(d, g)})
                if check(d, g, f"S/hop{i}", mid_seen, sess):
                    return d, g, True
            return d, g, False

        def F_deep(sess, mid_seen, log):
            d, g = setup_convert(sess)
            d, g = arm_hop(sess, d, g, 39)
            for _ in range(4):
                d2 = pad(sess, g, 9)
                if d2 is None:
                    break
                g = plane(d2["frame"]); d = d2
                if check(d, g, "F/sink", mid_seen, sess):
                    return d, g, True
            for x0 in (39, 45, 51, 57, 39, 45):
                d2 = pad(sess, g, x0)
                if d2:
                    g = plane(d2["frame"]); d = d2
                d2 = click_gap(sess, g)
                if d2:
                    g = plane(d2["frame"]); d = d2
                    log.append({"deep": x0, **snap(d, g)})
                    if check(d, g, "F/gap", mid_seen, sess):
                        return d, g, True
            return d, g, False

        def N_noleft(sess, mid_seen, log):
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            d2 = pad(sess, g, 9)
            if d2:
                g = plane(d2["frame"]); d = d2
            for _ in range(3):
                for x0 in (39, 45, 51, 57):
                    d2 = pad(sess, g, x0)
                    if d2:
                        g = plane(d2["frame"]); d = d2
                    d2 = click_gap(sess, g)
                    if d2:
                        g = plane(d2["frame"]); d = d2
                    m = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
                    if m:
                        d2 = click(sess, round(m[0]["cx"]), round(m[0]["cy"]))
                        if d2:
                            g = plane(d2["frame"]); d = d2
                    log.append(snap(d, g))
                    if check(d, g, "N", mid_seen, sess):
                        return d, g, True
            return d, g, False

        def C_conv(sess, mid_seen, log):
            d, g = setup_convert(sess)
            d2 = click_gap(sess, g)
            if d2:
                g = plane(d2["frame"]); d = d2
                log.append({"unarmed_gap": True, **snap(d, g)})
                if check(d, g, "C/unarmed", mid_seen, sess):
                    return d, g, True
            c = left12(g)
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            g = plane(d2["frame"]); d = d2
            d2 = click_gap(sess, g)
            if d2:
                g = plane(d2["frame"]); d = d2
                if check(d, g, "C/armed", mid_seen, sess):
                    return d, g, True
            d2 = pad(sess, g, 15)
            if d2:
                g = plane(d2["frame"]); d = d2
                log.append({"hop15": True, **snap(d, g)})
                if check(d, g, "C/hop15", mid_seen, sess):
                    return d, g, True
                d2 = click_gap(sess, g)
                if d2:
                    g = plane(d2["frame"]); d = d2
                    if check(d, g, "C/hop15_gap", mid_seen, sess):
                        return d, g, True
            return d, g, False

        for label, fn in [
            ("G/ceil_gap_ritual", G_ceil),
            ("L/bay0_c12_gap", L_bay0),
            ("S/shuttle_gap", S_shuttle),
            ("F/deep_gap", F_deep),
            ("N/noleft_gap", N_noleft),
            ("C/conv_gap", C_conv),
        ]:
            row, cleared = run_family(sess, label, fn)
            rows.append(row)
            if cleared:
                break

        bypass = any(r["cleared"] and 12 not in r["mid_seen"] for r in rows)
        reading = (
            "BYPASS_CLEAR" if bypass
            else ("CLEAR_BUT_MID12" if any(r["cleared"] for r in rows) else "NO_BYPASS_CLEAR")
        )
        out = {
            "rows": rows,
            "bypass": bypass,
            "mid_ever_12": any(12 in r["mid_seen"] for r in rows),
            "reading": reading,
            "hypothesis": "H57 levels 3→4 while mid stays kind=1",
        }
        print("\n## Summary")
        print("cleared:", [r["label"] for r in rows if r["cleared"]])
        print("READING:", reading)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
