"""tr87 L1: slot cursor map + ACTION1/2 follow selection + short clear hunt.

tags=["tr87_recon"]. Independent scorecard. No r11l/vc33.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane, ascii_preview  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_slot_map.json"
TAGS = ["tr87_recon"]


def ndiff(a, b):
    return int(np.sum(a != b))


def changes(a, b):
    m = a != b
    ys, xs = np.where(m)
    hist = Counter()
    cells = []
    for y, x in zip(ys.tolist(), xs.tolist()):
        aa, bb = int(a[y, x]), int(b[y, x])
        hist[(aa, bb)] += 1
        cells.append((int(x), int(y), aa, bb))
    return {f"{a_}->{b_}": n for (a_, b_), n in hist.most_common(20)}, cells


def color0_cells(g):
    return sorted((int(x), int(y)) for y, x in np.argwhere(g == 0))


def color0_bbox(g):
    cells = color0_cells(g)
    if not cells:
        return None
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    return {
        "n": len(cells),
        "x0": min(xs), "x1": max(xs),
        "y0": min(ys), "y1": max(ys),
        "cx": sum(xs) / len(xs),
        "cy": sum(ys) / len(ys),
        "cells": cells,
    }


def five_seven_bbox(cells):
    """bbox of cells involved in 5↔7 flips."""
    fs = [(x, y) for x, y, a, b in cells if {a, b} <= {5, 7}]
    if not fs:
        return None
    xs = [c[0] for c in fs]
    ys = [c[1] for c in fs]
    return {
        "n": len(fs),
        "x0": min(xs), "x1": max(xs),
        "y0": min(ys), "y1": max(ys),
        "cx": sum(xs) / len(xs),
        "cy": sum(ys) / len(ys),
    }


def slot_id(bbox):
    """Bucket selection by cx into left/mid/right-ish."""
    if bbox is None:
        return None
    cx = bbox["cx"]
    if cx < 20:
        return "L"
    if cx < 35:
        return "M"
    if cx < 50:
        return "R"
    return "X"


def act(sess, n):
    return sess.action(f"ACTION{n}")


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"tags": TAGS, "sections": {}}
    try:
        sess.open()

        # ---- A: cursor walk with only 3/4 ----
        print("\n## A cursor walk ACTION3/4")
        d = sess.reset()
        g = plane(d["frame"])
        path = []
        b0 = color0_bbox(g)
        path.append({"step": "reset", "slot": slot_id(b0), "bbox": b0})
        print(f"  reset slot={slot_id(b0)} bbox={b0 and (b0['x0'], b0['x1'], b0['y0'], b0['y1'])}")

        # spam ACTION3 ×8
        seq3 = []
        for i in range(8):
            g0 = g
            d = act(sess, 3)
            g = plane(d["frame"])
            b = color0_bbox(g)
            ch, cells = changes(g0, g)
            row = {
                "i": i, "action": 3,
                "slot": slot_id(b),
                "bbox": {k: b[k] for k in ("n", "x0", "x1", "y0", "y1", "cx", "cy")} if b else None,
                "nd": ndiff(g0, g),
                "ch": ch,
            }
            seq3.append(row)
            print(f"  3#{i} slot={row['slot']} x={b['x0'] if b else None}-{b['x1'] if b else None} nd={row['nd']}")
        out["sections"]["A_action3_walk"] = seq3

        d = sess.reset()
        g = plane(d["frame"])
        seq4 = []
        for i in range(8):
            g0 = g
            d = act(sess, 4)
            g = plane(d["frame"])
            b = color0_bbox(g)
            ch, _ = changes(g0, g)
            row = {
                "i": i, "action": 4,
                "slot": slot_id(b),
                "bbox": {k: b[k] for k in ("n", "x0", "x1", "y0", "y1", "cx", "cy")} if b else None,
                "nd": ndiff(g0, g),
                "ch": ch,
            }
            seq4.append(row)
            print(f"  4#{i} slot={row['slot']} x={b['x0'] if b else None}-{b['x1'] if b else None} nd={row['nd']}")
        out["sections"]["A_action4_walk"] = seq4

        # alternating 3/4 from reset
        d = sess.reset()
        g = plane(d["frame"])
        alt = [{"step": "reset", "slot": slot_id(color0_bbox(g))}]
        for i, a in enumerate([3, 4, 3, 4, 3, 4, 3, 4]):
            d = act(sess, a)
            g = plane(d["frame"])
            b = color0_bbox(g)
            alt.append({"i": i, "action": a, "slot": slot_id(b),
                        "x0": b["x0"] if b else None, "x1": b["x1"] if b else None})
            print(f"  alt {a} -> slot={slot_id(b)} x={b['x0'] if b else None}")
        out["sections"]["A_alt34"] = alt

        # ---- B: does 1/2 follow selection? ----
        print("\n## B ACTION1/2 follow slot")
        follow = []
        for prep in (
            ("at_L", []),
            ("at_M", [4]),          # left -> mid
            ("at_R", [3]),          # left -> right
            ("at_L_via_33", [3, 3]),  # if cyclic
            ("at_M_via_44", [4, 4]),
        ):
            name, seq = prep
            d = sess.reset()
            g = plane(d["frame"])
            for a in seq:
                d = act(sess, a)
                g = plane(d["frame"])
            slot = slot_id(color0_bbox(g))
            bsel = color0_bbox(g)
            for flip in (1, 2):
                g0 = g.copy()
                d = act(sess, flip)
                g1 = plane(d["frame"])
                ch, cells = changes(g0, g1)
                fb = five_seven_bbox(cells)
                row = {
                    "prep": name,
                    "prep_seq": seq,
                    "slot": slot,
                    "sel_x0": bsel["x0"] if bsel else None,
                    "sel_x1": bsel["x1"] if bsel else None,
                    "flip": flip,
                    "nd": ndiff(g0, g1),
                    "ch": ch,
                    "flip_bbox": fb,
                    "flip_overlaps_sel": (
                        fb is not None and bsel is not None
                        and not (fb["x1"] < bsel["x0"] or fb["x0"] > bsel["x1"])
                        and not (fb["y1"] < bsel["y0"] or fb["y0"] > bsel["y1"])
                    ),
                    "lv": d.get("levels_completed"),
                }
                follow.append(row)
                print(
                    f"  {name} slot={slot} selx={row['sel_x0']}-{row['sel_x1']} "
                    f"ACT{flip} flipx={fb and (fb['x0'], fb['x1'])} "
                    f"overlap={row['flip_overlaps_sel']} nd={row['nd']}"
                )
                g = g1
                # after flip, selection may stay; continue second flip on same prep board
            # re-prep for cleanliness each prep name already resets
        out["sections"]["B_follow"] = follow

        # ---- C: short sequences hunting levels↑ ----
        print("\n## C short clear hunt (budget)")
        # After understanding slots: try bring each slot through both flips
        hunts = []
        # sequences: visit L,M,R with flips
        candidates = [
            # flip both modes on L then move
            [1, 2, 4, 1, 2, 3, 1, 2],
            [2, 1, 4, 2, 1, 3, 2, 1],
            [4, 1, 2, 3, 1, 2],
            [3, 1, 2, 4, 1, 2],
            [1, 4, 1, 3, 1],
            [2, 4, 2, 3, 2],
            # many 1s / 2s on L
            [1] * 6,
            [2] * 6,
            [1, 2] * 4,
            # circle slots
            [3, 3, 3, 3, 4, 4, 4, 4],
            [4, 4, 4, 4, 3, 3, 3, 3],
            # flip while circling
            [1, 3, 1, 3, 1, 3, 1],
            [1, 4, 1, 4, 1, 4, 1],
            [2, 3, 2, 3, 2, 3],
            [2, 4, 2, 4, 2, 4],
        ]
        best_lv = 0
        for seq in candidates:
            d = sess.reset()
            g = plane(d["frame"])
            lv0 = d.get("levels_completed")
            log = []
            cleared = False
            for a in seq:
                d = act(sess, a)
                g2 = plane(d["frame"])
                lv = int(d.get("levels_completed") or 0)
                log.append({
                    "a": a,
                    "slot": slot_id(color0_bbox(g2)),
                    "lv": lv,
                    "nd": ndiff(g, g2),
                })
                g = g2
                if lv > best_lv:
                    best_lv = lv
                if lv > int(lv0 or 0):
                    print(f"*** LEVELS {lv0}->{lv} seq={seq} log={log}")
                    cleared = True
                    # save frame
                    (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                        json.dumps({"frame": d["frame"], "levels": lv, "seq": seq}, indent=2),
                        encoding="utf-8",
                    )
                    break
            hunts.append({"seq": seq, "final_lv": log[-1]["lv"] if log else lv0, "cleared": cleared, "log": log})
            print(f"  seq={seq} final_lv={hunts[-1]['final_lv']} slots={[x['slot'] for x in log]}")
            if cleared:
                break
        out["sections"]["C_hunt"] = hunts
        out["best_lv"] = best_lv

        # ---- D: dump bottom band icons under each slot ----
        print("\n## D bottom band snapshot per slot")
        snaps = []
        for name, seq in (("L", []), ("M", [4]), ("R", [3])):
            d = sess.reset()
            g = plane(d["frame"])
            for a in seq:
                d = act(sess, a)
                g = plane(d["frame"])
            b = color0_bbox(g)
            # crop y48-60
            crop = g[48:61, 12:50].tolist()
            snaps.append({
                "name": name,
                "slot": slot_id(b),
                "bbox": b,
                "preview": ascii_preview(g, y0=48, y1=60, x0=12, x1=49),
            })
            print(f"  slot {name}:", snaps[-1]["preview"][:8])
        out["sections"]["D_band"] = [
            {k: v for k, v in s.items() if k != "bbox"} | {
                "bbox": ({kk: s["bbox"][kk] for kk in ("n", "x0", "x1", "y0", "y1", "cx", "cy")}
                         if s["bbox"] else None)
            }
            for s in snaps
        ]

        reading = (
            "L1_CLEAR" if best_lv >= 1
            else "SLOT_MAPPED"
        )
        out["reading"] = reading
        # derive slot cycle summary
        out["summary"] = {
            "action3_slots": [r["slot"] for r in seq3],
            "action4_slots": [r["slot"] for r in seq4],
            "follow_overlap": [
                (r["prep"], r["flip"], r["slot"], r["flip_overlaps_sel"])
                for r in follow
            ],
            "best_lv": best_lv,
        }
        print("\n## Summary")
        print("3 walk:", out["summary"]["action3_slots"])
        print("4 walk:", out["summary"]["action4_slots"])
        print("follow:", out["summary"]["follow_overlap"])
        print("best_lv", best_lv)
        print("READING:", reading)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
