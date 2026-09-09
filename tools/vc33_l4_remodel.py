"""L4 remodel knives H45 (left-gate rhythm) + H47 (env y44–45 tunnel).

H45: left c12 already reachable — try pad rhythm / hop-cycle revisit /
     multi-arm count / convert→hop→return→reconvert without assuming mid12.

H47: measure whether env ever paints y44–45 at x≥30 (horizontal tunnel
     toward gap11); track accent↔gap x-overlap if tunnel appears.

H48: ignore GAME_OVER/HTTP400 — skip and continue.

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
)

OUT = ROOT / "tests/fixtures/vc33_l4_remodel.json"


def hist(g):
    return {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP skip", e)
        return None


def metrics(g, d=None):
    sp = sprite(g)
    gp = gap11(g)
    m = {
        "lv": None if d is None else int(d.get("levels_completed") or 0),
        "acts": None if d is None else d.get("available_actions"),
        "h12": int((g == 12).sum()),
        "c12n": len(components(g, 12, 1, 80)),
        "c1n": len(components(g, 1, 1, 80)),
    }
    if sp:
        b, a = sp["body"], sp.get("accent")
        m.update({
            "bx": round(b["cx"], 2), "by": round(b["cy"], 2),
            "by0": b["y0"], "bx1": b["x1"],
        })
        if a:
            m.update({
                "ax0": a["x0"], "ax1": a["x1"],
                "ay0": a["y0"], "ay1": a["y1"],
            })
    if gp and sp and sp.get("accent"):
        a = sp["accent"]
        ox0 = max(a["x0"], gp["x0"])
        ox1 = min(a["x1"], gp["x1"])
        m.update({
            "gx0": gp["x0"], "gx1": gp["x1"],
            "gy0": gp["y0"], "gy1": gp["y1"],
            "dx": gp["x0"] - a["x1"],
            "x_overlap": ox1 >= ox0,
        })
    return m


def tunnel_scan(g):
    """Zeros / env paint on y44–45 for x23→42 (H47)."""
    rows = {}
    for y in (44, 45):
        zs = []
        for x in range(23, 43):
            c = int(g[y, x])
            if c == 0:
                zs.append(x)
        rows[y] = {
            "zeros": zs,
            "xmax0": max(zs) if zs else None,
            "xmin0": min(zs) if zs else None,
            "n0": len(zs),
            "x30plus": [x for x in zs if x >= 30],
            "colors": {x: int(g[y, x]) for x in range(23, 43)},
        }
    return rows


def pad_by(g, x0):
    for p in pads_sorted(g):
        if p["x0"] == x0:
            return p
    return None


def do_pad(sess, d, g, x0, tag, log):
    p = pad_by(g, x0)
    if not p:
        log.append({"tag": tag, "err": f"no_pad_{x0}"})
        return d, g
    g0 = g
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        log.append({"tag": tag, "err": "HTTP"})
        return d, g
    g2 = plane(d2["frame"])
    row = {
        "tag": tag,
        "pad": x0,
        "nd": int(body_ndiff(g0, g2)),
        "ch": body_changes(g0, g2),
        **metrics(g2, d2),
        "tunnel": tunnel_scan(g2),
    }
    print(
        f"{tag} pad{x0} cy={row.get('by')} h12={row['h12']} "
        f"dx={row.get('dx')} xov={row.get('x_overlap')} "
        f"t45_30+={row['tunnel'][45]['x30plus']} lv={row['lv']}"
    )
    log.append(row)
    return d2, g2


def do_cell(sess, d, g, x, y, tag, log):
    g0 = g
    d2 = click(sess, x, y)
    if d2 is None:
        log.append({"tag": tag, "err": "HTTP"})
        return d, g
    g2 = plane(d2["frame"])
    row = {
        "tag": tag,
        "xy": [x, y],
        "nd": int(body_ndiff(g0, g2)),
        "ch": body_changes(g0, g2),
        **metrics(g2, d2),
        "tunnel": tunnel_scan(g2),
    }
    print(
        f"{tag} @{x},{y} nd={row['nd']} cy={row.get('by')} h12={row['h12']} "
        f"lv={row['lv']}"
    )
    log.append(row)
    return d2, g2


def left_c12(g):
    comps = components(g, 12, 1, 80)
    left = [c for c in comps if c["cx"] < 20]
    return left[0] if left else (comps[0] if comps else None)


def maybe_save_clear(sess, d, g, out):
    if int(d.get("levels_completed") or 0) < 4:
        return False
    FIXTURE_L4_CLEAR.write_text(
        json.dumps({
            "game_id": sess.game_id,
            "frame": g.tolist(),
            "meta": {
                "levels_completed": d.get("levels_completed"),
                "available_actions": d.get("available_actions"),
            },
        }, indent=2),
        encoding="utf-8",
    )
    d5 = sess.action("ACTION1")
    g5 = plane(d5["frame"])
    FIXTURE_L5.write_text(
        json.dumps({
            "game_id": sess.game_id,
            "frame": g5.tolist(),
            "meta": {
                "levels_completed": d5.get("levels_completed"),
                "available_actions": d5.get("available_actions"),
            },
        }, indent=2),
        encoding="utf-8",
    )
    out["CLEARED"] = True
    print("*** L4 CLEARED ***")
    return True


def run_h45(sess, out):
    log = []
    out["H45"] = {"log": log}
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    log.append({"tag": "enter", **metrics(g, d), "tunnel": tunnel_scan(g)})

    # sink to left convert (pad15 ×2 typical)
    for i in range(3):
        d, g = do_pad(sess, d, g, 15, f"sink{i}", log)
        if metrics(g)["h12"] > 0:
            break
    assert metrics(g)["h12"] > 0, "no left c12"

    # --- A: pad rhythm without arm — alternate env + sink/up micro ---
    rhythm = [39, 15, 45, 15, 51, 9, 57, 15, 39, 9, 45, 15]
    for i, x0 in enumerate(rhythm):
        d, g = do_pad(sess, d, g, x0, f"A_r{i}_{x0}", log)
        if maybe_save_clear(sess, d, g, out):
            return d, g, True

    # --- B: arm left c12 N times then env (no hop yet) ---
    w = left_c12(g)
    if w:
        for n in range(1, 4):
            d, g = do_cell(
                sess, d, g, int(w["cx"]), int(w["cy"]), f"B_arm{n}", log
            )
            for j, x0 in enumerate([39, 45, 51]):
                d, g = do_pad(sess, d, g, x0, f"B_arm{n}_env{x0}", log)
                if maybe_save_clear(sess, d, g, out):
                    return d, g, True

    # --- C: hop cycle bay0↔bay1 then revisit left convert ---
    # ensure c12; arm once; hop with pad39; hop back; sink/reconvert; count
    ent2 = enter_l4(sess)
    d, g = ent2["data"], ent2["frame"]
    log.append({"tag": "C_reenter", **metrics(g, d)})
    for i in range(3):
        d, g = do_pad(sess, d, g, 15, f"C_sink{i}", log)
        if metrics(g)["h12"] > 0:
            break
    w = left_c12(g)
    if w:
        d, g = do_cell(sess, d, g, int(w["cx"]), int(w["cy"]), "C_arm", log)
    # hop east (bay1)
    d, g = do_pad(sess, d, g, 39, "C_hop_e", log)
    # in bay1: climb a bit then env then hop back
    for i in range(2):
        d, g = do_pad(sess, d, g, 15, f"C_bay1_up{i}", log)
    for x0 in (39, 45, 51, 57):
        d, g = do_pad(sess, d, g, x0, f"C_bay1_env{x0}", log)
        if maybe_save_clear(sess, d, g, out):
            return d, g, True
    # re-arm mid or left if present
    w = left_c12(g)
    if not w:
        # may have lost c12 — try hop with any pad after clicking mid?
        mids = [c for c in components(g, 1, 1, 80) if c["cx"] > 20]
        c12s = components(g, 12, 1, 80)
        if c12s:
            w = c12s[0]
        elif mids:
            d, g = do_cell(
                sess, d, g, int(mids[0]["cx"]), int(mids[0]["cy"]), "C_mid", log
            )
    if w:
        d, g = do_cell(sess, d, g, int(w["cx"]), int(w["cy"]), "C_rearm", log)
    d, g = do_pad(sess, d, g, 9, "C_hop_w", log)  # often -15 back
    # revisit deep convert
    for i in range(4):
        d, g = do_pad(sess, d, g, 15, f"C_resink{i}", log)
        if maybe_save_clear(sess, d, g, out):
            return d, g, True
    w = left_c12(g)
    if w:
        for n in range(3):
            d, g = do_cell(
                sess, d, g, int(w["cx"]), int(w["cy"]), f"C_revisit_arm{n}", log
            )
            d, g = do_pad(sess, d, g, 39, f"C_revisit_hop{n}", log)
            if maybe_save_clear(sess, d, g, out):
                return d, g, True

    # --- D: convert count — pad15×N without arm; click gap while c12 lit ---
    ent3 = enter_l4(sess)
    d, g = ent3["data"], ent3["frame"]
    for i in range(5):
        d, g = do_pad(sess, d, g, 15, f"D_sink{i}", log)
        m = metrics(g, d)
        if m["h12"] > 0:
            gp = gap11(g)
            if gp:
                d, g = do_cell(
                    sess, d, g, int(gp["cx"]), int(gp["cy"]), f"D_gap_at_c12_{i}", log
                )
            # click both windows while lit
            for ci, c in enumerate(components(g, 12, 1, 80) + components(g, 1, 1, 80)):
                d, g = do_cell(
                    sess, d, g, int(c["cx"]), int(c["cy"]), f"D_win{ci}_{i}", log
                )
                if maybe_save_clear(sess, d, g, out):
                    return d, g, True
        if maybe_save_clear(sess, d, g, out):
            return d, g, True

    out["H45_verdict"] = {
        "levels_up": False,
        "max_h12": max((r.get("h12") or 0) for r in log),
        "any_x_overlap": any(r.get("x_overlap") for r in log),
        "min_dx": min((r["dx"] for r in log if r.get("dx") is not None), default=None),
    }
    print("H45 verdict", out["H45_verdict"])
    return d, g, False


def run_h47(sess, out):
    log = []
    out["H47"] = {"log": log}
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    log.append({"tag": "enter", **metrics(g, d), "tunnel": tunnel_scan(g)})

    # bay0 deep + heavy env; then convert + env; then bay1 floor env
    phases = []

    # phase1: no convert, env spam from enter
    for i, x0 in enumerate([39, 45, 51, 57] * 8):
        d, g = do_pad(sess, d, g, x0, f"P1_env{i}_{x0}", log)
        t = tunnel_scan(g)
        if t[44]["x30plus"] or t[45]["x30plus"]:
            print("*** TUNNEL HIT P1 ***", t[44], t[45])
            phases.append(("P1", t))
        if maybe_save_clear(sess, d, g, out):
            return d, g, True

    # phase2: convert then env
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    for i in range(3):
        d, g = do_pad(sess, d, g, 15, f"P2_sink{i}", log)
        if metrics(g)["h12"] > 0:
            break
    for i, x0 in enumerate([39, 45, 51, 57] * 10):
        d, g = do_pad(sess, d, g, x0, f"P2_env{i}_{x0}", log)
        t = tunnel_scan(g)
        if t[44]["x30plus"] or t[45]["x30plus"]:
            print("*** TUNNEL HIT P2 ***", t[44]["x30plus"], t[45]["x30plus"])
            phases.append(("P2", t))
        if maybe_save_clear(sess, d, g, out):
            return d, g, True

    # phase3: hop to bay1, stay low (pad9 sink), env spam
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    for i in range(3):
        d, g = do_pad(sess, d, g, 15, f"P3_sink{i}", log)
        if metrics(g)["h12"] > 0:
            break
    w = left_c12(g)
    if w:
        d, g = do_cell(sess, d, g, int(w["cx"]), int(w["cy"]), "P3_arm", log)
    d, g = do_pad(sess, d, g, 39, "P3_hop", log)
    # sink in bay1
    for i in range(4):
        d, g = do_pad(sess, d, g, 9, f"P3_dn{i}", log)
    for i, x0 in enumerate([39, 45, 51, 57] * 10):
        d, g = do_pad(sess, d, g, x0, f"P3_env{i}_{x0}", log)
        t = tunnel_scan(g)
        if t[44]["x30plus"] or t[45]["x30plus"]:
            print("*** TUNNEL HIT P3 ***", t[44]["x30plus"], t[45]["x30plus"])
            phases.append(("P3", t))
        m = metrics(g, d)
        if m.get("x_overlap"):
            print("*** X OVERLAP ***", m)
            phases.append(("P3_xov", m))
        if maybe_save_clear(sess, d, g, out):
            return d, g, True

    # summarize max east reach of zeros on y44/45 across log
    max_x45 = None
    max_x44 = None
    any_30 = False
    for r in log:
        t = r.get("tunnel") or {}
        for y, slot in ((44, "max_x44"), (45, "max_x45")):
            row = t.get(y) or {}
            xm = row.get("xmax0")
            if xm is not None:
                if y == 44:
                    max_x44 = xm if max_x44 is None else max(max_x44, xm)
                else:
                    max_x45 = xm if max_x45 is None else max(max_x45, xm)
            if row.get("x30plus"):
                any_30 = True

    out["H47_verdict"] = {
        "any_y44_45_x30plus_zero": any_30,
        "max_zero_x_y44": max_x44,
        "max_zero_x_y45": max_x45,
        "tunnel_hits": len(phases),
        "levels_up": False,
        "min_dx": min((r["dx"] for r in log if r.get("dx") is not None), default=None),
    }
    print("H47 verdict", out["H47_verdict"])
    return d, g, False


def run(sess, out):
    d, g, cleared = run_h45(sess, out)
    if cleared:
        return d, g, True
    d, g, cleared = run_h47(sess, out)
    return d, g, cleared


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"hypotheses": ["H45", "H47"]}
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
