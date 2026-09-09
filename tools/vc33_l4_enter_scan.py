"""L4 enter-frame full scan (NO sink) + H46 color7 mode-switch.

Before any pad15/9 sink:
  - map hist / all color components
  - click every color7 cell (top UI bar; hist=64)
  - sample color5 beam comps + odd colors
  - watch levels / available_actions / frame morph / pad semantics

H46: after c7 clicks, re-probe pad9/15/39 deltas vs enter baseline.

tags=["vc33_recon"]. Enter via enter_l4.
"""
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

OUT = ROOT / "tests/fixtures/vc33_l4_enter_scan.json"


def hist(g):
    return {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def all_comps(g):
    out = {}
    for c in sorted(hist(g)):
        out[str(c)] = components(g, c, 1, 10**6)
    return out


def pad_deltas(sess, g0):
    """One-shot pad probe without mutating caller's intent — uses live g."""
    rows = []
    g = g0
    for p in pads_sorted(g0):
        g_before = g
        sp0 = sprite(g_before)
        d = click(sess, int(round(p["cx"])), int(round(p["cy"])))
        if d is None:
            rows.append({"x0": p["x0"], "err": "HTTP"})
            continue
        g = plane(d["frame"])
        sp1 = sprite(g)
        ddx = ddy = None
        if sp0 and sp1:
            ddx = round(sp1["body"]["cx"] - sp0["body"]["cx"], 3)
            ddy = round(sp1["body"]["cy"] - sp0["body"]["cy"], 3)
        rows.append({
            "x0": p["x0"],
            "nd": int(body_ndiff(g_before, g)),
            "ddx": ddx,
            "ddy": ddy,
            "ch": body_changes(g_before, g),
            "lv": int(d.get("levels_completed") or 0),
            "acts": d.get("available_actions"),
            "h12": int((g == 12).sum()),
        })
        print(
            f"  pad{p['x0']} nd={rows[-1]['nd']} d=({ddx},{ddy}) "
            f"h12={rows[-1]['h12']} lv={rows[-1]['lv']}"
        )
        # undo sink drift: if we moved sprite, stop further pads on dirty board
        # caller re-enters; here we just record sequential effects
    return rows, d if rows else None, g


def run(sess, out):
    """Run enter-scan + H46 on already-open sess. Mutates out. Returns (d,g,cleared)."""
    log = []
    out["section"] = "enter_scan_H46"
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    base = {
        "lv": int(d.get("levels_completed") or 0),
        "acts": d.get("available_actions"),
        "hist": hist(g),
        "comps": all_comps(g),
        "summary": summarize(g),
    }
    out["enter"] = base
    print(
        "ENTER hist", base["hist"],
        "acts", base["acts"],
        "c7_comps", len(base["comps"].get("7", [])),
        "c5_comps", len(base["comps"].get("5", [])),
    )

    # --- click every color7 cell (y=0 bar) ---
    c7_hits = []
    ys, xs = np.where(g == 7)
    cells = sorted(zip(xs.tolist(), ys.tolist()))
    print(f"c7 cells={len(cells)}")
    g_prev = g
    for i, (x, y) in enumerate(cells):
        # re-locate remaining c7 if UI flipped
        if int(g[y, x]) != 7:
            # find nearest remaining 7 on row
            row = np.where(g[y] == 7)[0]
            if len(row) == 0:
                c7_hits.append({"i": i, "xy": [x, y], "skip": "no_c7"})
                continue
            x = int(row[min(range(len(row)), key=lambda j: abs(row[j] - x))])
        d2 = click(sess, x, y)
        if d2 is None:
            c7_hits.append({"i": i, "xy": [x, y], "err": "HTTP"})
            continue
        g2 = plane(d2["frame"])
        nd = int(body_ndiff(g_prev, g2))
        # ignore pure UI (63,0) tick: measure body y>=1
        row = {
            "i": i,
            "xy": [x, y],
            "nd": nd,
            "ch": body_changes(g_prev, g2) if nd else {},
            "lv": int(d2.get("levels_completed") or 0),
            "acts": d2.get("available_actions"),
            "hist_d": {
                k: hist(g2).get(k, 0) - hist(g_prev).get(k, 0)
                for k in set(hist(g2)) | set(hist(g_prev))
                if hist(g2).get(k, 0) != hist(g_prev).get(k, 0)
            },
            "h7": int((g2 == 7).sum()),
            "h4": int((g2 == 4).sum()),
        }
        if nd or row["hist_d"] or row["lv"] != base["lv"]:
            print(f"c7@{x},{y} nd={nd} hist_d={row['hist_d']} lv={row['lv']} acts={row['acts']}")
        c7_hits.append(row)
        g_prev = g2
        d = d2
        g = g2
        if int(d.get("levels_completed") or 0) >= 4:
            out["CLEARED"] = True
            break
    out["c7_clicks"] = c7_hits
    out["after_c7"] = {
        "lv": int(d.get("levels_completed") or 0),
        "acts": d.get("available_actions"),
        "hist": hist(g),
        "comps": {k: v for k, v in all_comps(g).items() if k not in ("0", "3")},
        "summary": summarize(g),
    }

    # --- color5 beam samples (each component centroid + corners) ---
    c5_hits = []
    for ci, c in enumerate(components(g, 5, 1, 500)):
        samples = [
            (int(c["cx"]), int(c["cy"]), "cen"),
            (c["x0"], c["y0"], "tl"),
            (c["x1"], c["y1"], "br"),
            (c["x0"], c["y1"], "bl"),
            (c["x1"], c["y0"], "tr"),
        ]
        for x, y, lab in samples:
            if int(g[y, x]) != 5:
                continue
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                c5_hits.append({"comp": ci, "lab": lab, "err": "HTTP"})
                continue
            g2 = plane(d2["frame"])
            nd = int(body_ndiff(g0, g2))
            row = {
                "comp": ci,
                "lab": lab,
                "xy": [x, y],
                "bbox": c,
                "nd": nd,
                "ch": body_changes(g0, g2) if nd else {},
                "lv": int(d2.get("levels_completed") or 0),
                "acts": d2.get("available_actions"),
            }
            if nd:
                print(f"c5[{ci}]{lab}@{x},{y} nd={nd} ch={row['ch']}")
            c5_hits.append(row)
            d, g = d2, g2
            if int(d.get("levels_completed") or 0) >= 4:
                out["CLEARED"] = True
                break
        if out.get("CLEARED"):
            break
    out["c5_clicks"] = c5_hits

    # --- odd / rare colors (not 0,1,3,4,5,7,9,11) ---
    odd_hits = []
    known = {0, 1, 3, 4, 5, 7, 9, 11, 12}
    for col in sorted(set(hist(g)) - known):
        for ci, c in enumerate(components(g, col, 1, 500)):
            x, y = int(c["cx"]), int(c["cy"])
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                odd_hits.append({"col": col, "err": "HTTP"})
                continue
            g2 = plane(d2["frame"])
            nd = int(body_ndiff(g0, g2))
            row = {
                "col": col,
                "xy": [x, y],
                "nd": nd,
                "ch": body_changes(g0, g2) if nd else {},
                "lv": int(d2.get("levels_completed") or 0),
                "acts": d2.get("available_actions"),
            }
            print(f"odd{col}@{x},{y} nd={nd} lv={row['lv']}")
            odd_hits.append(row)
            d, g = d2, g2
    out["odd_clicks"] = odd_hits

    # also click color1 windows + gap11 + accent (enter-state, no sink yet)
    misc = []
    for lab, comps in (
        ("c1", components(g, 1, 1, 80)),
        ("c11", components(g, 11, 1, 40)),
        ("c9", components(g, 9, 1, 20)),
    ):
        for ci, c in enumerate(comps):
            x, y = int(c["cx"]), int(c["cy"])
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                continue
            g2 = plane(d2["frame"])
            nd = int(body_ndiff(g0, g2))
            row = {
                "lab": f"{lab}_{ci}",
                "xy": [x, y],
                "nd": nd,
                "ch": body_changes(g0, g2) if nd else {},
                "lv": int(d2.get("levels_completed") or 0),
                "acts": d2.get("available_actions"),
                "ddx_ddy": None,
            }
            sp0, sp1 = sprite(g0), sprite(g2)
            if sp0 and sp1:
                row["ddx_ddy"] = (
                    round(sp1["body"]["cx"] - sp0["body"]["cx"], 3),
                    round(sp1["body"]["cy"] - sp0["body"]["cy"], 3),
                )
            if nd or row["ddx_ddy"] not in (None, (0.0, 0.0)):
                print(f"misc {row['lab']} nd={nd} d={row['ddx_ddy']}")
            misc.append(row)
            d, g = d2, g2
            if int(d.get("levels_completed") or 0) >= 4:
                out["CLEARED"] = True
                break
        if out.get("CLEARED"):
            break
    out["misc_clicks"] = misc

    # --- H46: first-click pad signature before vs after c7 bar spam ---
    def first_clicks(label):
        rows = []
        pad_x0s = None
        for i in range(6):
            ent_i = enter_l4(sess)
            d_i, g_i = ent_i["data"], ent_i["frame"]
            pads = pads_sorted(g_i)
            if pad_x0s is None:
                pad_x0s = [p["x0"] for p in pads]
            if i >= len(pad_x0s):
                break
            # optional mode prep
            if label == "mode":
                for x in (0, 16, 32, 48, 63):
                    if int(g_i[0, x]) in (7, 4):
                        d_tmp = click(sess, x, 0)
                        if d_tmp is not None:
                            g_i = plane(d_tmp["frame"])
                            d_i = d_tmp
            p = next(p for p in pads_sorted(g_i) if p["x0"] == pad_x0s[i])
            g0 = g_i
            sp0 = sprite(g0)
            d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
            if d2 is None:
                rows.append({"x0": pad_x0s[i], "err": "HTTP"})
                continue
            g2 = plane(d2["frame"])
            sp1 = sprite(g2)
            ddx = ddy = None
            if sp0 and sp1:
                ddx = round(sp1["body"]["cx"] - sp0["body"]["cx"], 3)
                ddy = round(sp1["body"]["cy"] - sp0["body"]["cy"], 3)
            row = {
                "x0": pad_x0s[i],
                "nd": int(body_ndiff(g0, g2)),
                "ddx": ddx,
                "ddy": ddy,
                "lv": int(d2.get("levels_completed") or 0),
                "acts": d2.get("available_actions"),
                "h12": int((g2 == 12).sum()),
                "ch": body_changes(g0, g2),
            }
            print(f"  {label} pad{row['x0']} d=({ddx},{ddy}) nd={row['nd']}")
            rows.append(row)
            d_i, g_i = d2, g2
        return rows, d_i, g_i

    print("=== H46 baseline first-clicks ===")
    base_rows, d, g = first_clicks("BASE")
    out["H46_baseline_seq"] = base_rows
    print("=== H46 mode (c7 prep) first-clicks ===")
    mode_rows, d, g = first_clicks("mode")
    out["H46_mode_pad_seq"] = mode_rows
    out["H46_mode_clicks"] = "per_pad_enter_c7_x=0,16,32,48,63"

    def sig(rows):
        return [(r.get("x0"), r.get("ddx"), r.get("ddy"), r.get("nd")) for r in rows]

    out["H46_verdict"] = {
        "baseline_sig": sig(base_rows),
        "mode_sig": sig(mode_rows),
        "sigs_equal": sig(base_rows) == sig(mode_rows),
        "acts_changed": any(
            r.get("acts") not in (None, [6]) for r in base_rows + mode_rows
        ),
        "levels_up": int(d.get("levels_completed") or 0) >= 4,
    }
    print("H46 verdict", out["H46_verdict"])

    cleared = int(d.get("levels_completed") or 0) >= 4
    if cleared:
        FIXTURE_L4_CLEAR.write_text(
            json.dumps({"game_id": sess.game_id, "frame": g.tolist(), "meta": {
                "levels_completed": d.get("levels_completed"),
                "available_actions": d.get("available_actions"),
            }}, indent=2),
            encoding="utf-8",
        )
        d5 = sess.action("ACTION1")
        g5 = plane(d5["frame"])
        FIXTURE_L5.write_text(
            json.dumps({"game_id": sess.game_id, "frame": g5.tolist(), "meta": {
                "levels_completed": d5.get("levels_completed"),
                "available_actions": d5.get("available_actions"),
            }}, indent=2),
            encoding="utf-8",
        )
        out["CLEARED"] = True
        print("*** L4 CLEARED *** saved clear+L5")
    return d, g, cleared


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"hypotheses": ["enter_scan", "H46"]}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        run(sess, out)
    finally:
        sess.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
