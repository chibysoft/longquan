"""L4 knives: dig-offset / ceiling break (H38) + falsify mid-as-second-gate (H39).

Goal A: ANY state with dig_top(x15-26)<accent_y1+1 OR body y0<40.
Goal B: alternate clear signal without mid12 (gap morph / hist / novel click / levels 3→4).

Hard locks: no re-prove flank/env/east; hop ±15 bay0↔1; max_cx=20.5; acts=[6].
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

OUT = ROOT / "tests/fixtures/vc33_l4_dig_offset.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def dig_metrics(g):
    sp = sprite(g)
    if not sp or not sp.get("accent"):
        return None
    acc = sp["accent"]
    body = sp["body"]
    ys = []
    for x in range(15, 27):
        for y in range(34, 60):
            if int(g[y, x]) == 0:
                ys.append(y)
                break
    dig_top = min(ys) if ys else None
    offset = None if dig_top is None else dig_top - (acc["y1"] + 1)
    return {
        "y0": body["y0"],
        "cy": body["cy"],
        "cx": body["cx"],
        "acc_y0": acc["y0"],
        "acc_y1": acc["y1"],
        "dig_top": dig_top,
        "expected": acc["y1"] + 1,
        "offset": offset,  # 0 = locked H28; <0 = SUCCESS dig break
        "break_dig": offset is not None and offset < 0,
        "break_ceil": body["y0"] < 40,
        "h12": int((g == 12).sum()),
        "mid12": bool([c for c in components(g, 12, 1, 80) if c["cx"] > 20]),
        "c1n": len(components(g, 1, 1, 80)),
        "c12n": len(components(g, 12, 1, 80)),
        "gap": gap11(g),
        "hist": {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))},
    }


def snap(d, g, tag, log):
    m = dig_metrics(g)
    row = {
        "tag": tag,
        "lv": d.get("levels_completed"),
        "acts": d.get("available_actions"),
        **(m or {}),
    }
    flag = ""
    if m and (m["break_dig"] or m["break_ceil"]):
        flag = " *** BREAK ***"
    print(
        f"{tag} dig={m and m['dig_top']} exp={m and m['expected']} off={m and m['offset']} "
        f"y0={m and m['y0']} cy={m and m['cy']} mid12={m and m['mid12']} "
        f"lv={row['lv']}{flag}"
    )
    log.append(row)
    return row


def pad(sess, d, g, x0, tag, log):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    g0 = g
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, None
    g2 = plane(d2["frame"])
    s0, s1 = sprite(g0), sprite(g2)
    info = snap(d2, g2, f"{tag}pad{x0}", log)
    info["dx"] = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    info["dy"] = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    info["nd"] = body_ndiff(g0, g2)
    info["ch"] = body_changes(g0, g2)
    return d2, g2, info


def sink_c12(sess, d, g, log, tag="sink"):
    for i in range(14):
        if int((g == 12).sum()) > 0:
            break
        d, g, _ = pad(sess, d, g, 15, f"{tag}{i} ", log)
    return d, g


def arm_left(sess, d, g, log, tag="arm"):
    c12 = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
    if not c12:
        return d, g, False
    c = c12[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    if d2 is None:
        return d, g, False
    g2 = plane(d2["frame"])
    snap(d2, g2, tag, log)
    return d2, g2, True


def climb(sess, d, g, log, tag="up", n=6):
    for i in range(n):
        sp = sprite(g)
        if sp and sp["body"]["y0"] <= 40:
            d, g, info = pad(sess, d, g, 15, f"{tag}{i} ", log)
            if abs(info.get("dy") or 0) < 0.1:
                break
            continue
        d, g, info = pad(sess, d, g, 15, f"{tag}{i} ", log)
        if abs(info.get("dy") or 0) < 0.1:
            break
    return d, g


def maybe_clear(d, sess, out):
    lv = int(d.get("levels_completed") or 0)
    if lv < 4:
        return False
    print("*** LEVELS CLEAR ***", lv)
    FIXTURE_L4_CLEAR.write_text(
        json.dumps({"frame": d["frame"], "levels": lv, "meta": d}, indent=2, default=float),
        encoding="utf-8",
    )
    d1 = sess.action("ACTION1")
    FIXTURE_L5.write_text(
        json.dumps(
            {
                "frame": d1["frame"],
                "levels": d1.get("levels_completed"),
                "meta": {
                    "levels_completed": d1.get("levels_completed"),
                    "state": d1.get("state"),
                    "available_actions": d1.get("available_actions"),
                },
            },
            indent=2,
            default=float,
        ),
        encoding="utf-8",
    )
    out["CLEAR"] = True
    out["clear_lv"] = lv
    return True


def any_break(log):
    return [r for r in log if r.get("break_dig") or r.get("break_ceil")]


# ---------- sections ----------

def sec_A_arm_clear_climb(sess, out):
    """Arm then clear (hop back / unarm) dig phase then climb — dig offset hunt."""
    print("\n==== A arm-clear dig then climb")
    log = []
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    snap(d, g, "enter", log)
    d, g = sink_c12(sess, d, g, log)
    d, g, _ = arm_left(sess, d, g, log)
    # hop to bay1 then hop back (spent?) then climb from bay0 high dig?
    d, g, _ = pad(sess, d, g, 39, "hz ", log)
    # re-arm left if still c12, or sink again
    if int((g == 12).sum()) > 0:
        d, g, _ = arm_left(sess, d, g, log, "arm2")
        d, g, _ = pad(sess, d, g, 9, "hz9 ", log)  # back bay0
    # deep sink without re-arm, then climb in bay0
    for i in range(4):
        d, g, info = pad(sess, d, g, 15, f"dn{i} ", log)
        if abs(info.get("dy") or 0) < 0.1:
            break
    d, g = climb(sess, d, g, log, "climb", n=8)
    # env interleaved climb from deep
    for i in range(3):
        d, g, _ = pad(sess, d, g, 39, f"env{i} ", log)
        d, g, info = pad(sess, d, g, 15, f"eup{i} ", log)
        if abs(info.get("dy") or 0) < 0.1 and i > 0:
            break
    out["A"] = {"log": log, "breaks": any_break(log)}
    return d, g


def sec_B_hop_phase(sess, out):
    """hop9 vs hop15; climb with env at each height; dn/up at cy45-42 boundary."""
    print("\n==== B hop9/15 phase + boundary wiggle")
    log = []
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    d, g = sink_c12(sess, d, g, log)
    d, g, _ = arm_left(sess, d, g, log)
    d, g, _ = pad(sess, d, g, 15, "hop15 ", log)  # hop with mover pad
    snap(d, g, "post_hop15", log)
    d, g = climb(sess, d, g, log, "up15", n=5)
    # boundary wiggle: at ceiling do dn/up
    for i in range(4):
        d, g, _ = pad(sess, d, g, 9, f"bdn{i} ", log)
        d, g, info = pad(sess, d, g, 15, f"bup{i} ", log)
        if info and (info.get("break_dig") or info.get("break_ceil")):
            break
    # env at each height from mid climb — re-enter hop path
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    d, g = sink_c12(sess, d, g, log, "s2")
    d, g, _ = arm_left(sess, d, g, log, "arm9")
    d, g, _ = pad(sess, d, g, 9, "hop9 ", log)
    for i in range(5):
        d, g, _ = pad(sess, d, g, 45, f"envH{i} ", log)
        d, g, info = pad(sess, d, g, 15, f"upH{i} ", log)
        if abs(info.get("dy") or 0) < 0.1 and sprite(g) and sprite(g)["body"]["y0"] <= 40:
            break
    out["B"] = {"log": log, "breaks": any_break(log)}
    return d, g


def sec_C_click_dig(sess, out):
    """Click dig cells (color0 under/near accent) then up; left-bay ceiling then hop."""
    print("\n==== C click dig cells + left-ceil hop")
    log = []
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    d, g = sink_c12(sess, d, g, log)
    d, g, _ = arm_left(sess, d, g, log)
    d, g, _ = pad(sess, d, g, 39, "hz ", log)
    d, g = climb(sess, d, g, log, "up", n=5)
    m = dig_metrics(g)
    dig_cells = []
    if m and m["dig_top"] is not None:
        yt = m["dig_top"]
        for x in range(15, 27):
            if int(g[yt, x]) == 0:
                dig_cells.append((x, yt))
            if yt + 1 < 64 and int(g[yt + 1, x]) == 0:
                dig_cells.append((x, yt + 1))
    hits = []
    for x, y in dig_cells[:18]:
        g0 = g
        d2 = click(sess, x, y)
        if d2 is None:
            continue
        g2 = plane(d2["frame"])
        nd = body_ndiff(g0, g2)
        row = snap(d2, g2, f"dig({x},{y})", log)
        row["nd"] = nd
        if nd > 0 or row.get("break_dig") or row.get("lv", 3) > 3:
            hits.append(row)
            print("  HIT dig-click", x, y, "nd", nd)
        g, d = g2, d2
        if maybe_clear(d, sess, out):
            break
    # after dig clicks try up
    d, g, _ = pad(sess, d, g, 15, "post_dig_up ", log)

    # left-bay ceiling first then hop
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    # climb in bay0 without convert? pad9 = -y, pad15 = +y at start
    # sink to convert, arm, climb in bay0 (no hop) to ceiling, THEN hop
    d, g = sink_c12(sess, d, g, log, "L")
    d, g, _ = arm_left(sess, d, g, log, "Larm")
    # climb bay0 while armed (may unarm on climb — document)
    for i in range(6):
        d, g, info = pad(sess, d, g, 15, f"Lb0up{i} ", log)
        if abs(info.get("dy") or 0) < 0.1:
            break
    # if lost c12, re-sink+arm at height?
    if int((g == 12).sum()) == 0:
        for i in range(8):
            d, g, info = pad(sess, d, g, 9, f"Ldn{i} ", log)  # down pad in bay?
            if int((g == 12).sum()) > 0:
                break
            if abs(info.get("dy") or 0) < 0.1 and i > 2:
                break
        if int((g == 12).sum()) > 0:
            d, g, _ = arm_left(sess, d, g, log, "Lrearm")
    d, g, _ = pad(sess, d, g, 39, "Lhop ", log)
    d, g = climb(sess, d, g, log, "Lup", n=5)
    out["C"] = {"log": log, "hits": hits, "breaks": any_break(log)}
    return d, g


def sec_D_falsify_midgate(sess, out):
    """H39: alternate clear without mid12 — gap morph, hist, novel clicks."""
    print("\n==== D falsify mid-as-second-gate")
    log = []
    signals = []
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    base = dig_metrics(g)
    snap(d, g, "enter", log)
    gap0 = base["gap"] if base else None

    def track(tag, d, g, g_prev=None):
        m = dig_metrics(g)
        gp = m["gap"] if m else None
        morph = None
        if gap0 and gp:
            morph = {
                "dx0": gp["x0"] - gap0["x0"],
                "dy0": gp["y0"] - gap0["y0"],
                "dx1": gp["x1"] - gap0["x1"],
                "dy1": gp["y1"] - gap0["y1"],
                "dn": gp["n"] - gap0["n"],
            }
        hist_d = {}
        if base and m:
            for k in set(base["hist"]) | set(m["hist"]):
                dv = m["hist"].get(k, 0) - base["hist"].get(k, 0)
                if dv:
                    hist_d[k] = dv
        c1 = components(g, 1, 1, 80)
        c12 = components(g, 12, 1, 80)
        row = {
            "tag": tag,
            "lv": d.get("levels_completed"),
            "gap_morph": morph,
            "hist_delta": hist_d,
            "c1": c1,
            "c12": c12,
            "c1n": len(c1),
            "c12n": len(c12),
            "nd": body_ndiff(g_prev, g) if g_prev is not None else 0,
        }
        interesting = bool(
            (morph and any(v != 0 for v in morph.values()))
            or any(k not in (0, 3, 4, 9, 11, 12) and abs(v) > 0 for k, v in hist_d.items())
            or len(c12) > 1
            or (len(c1) != (base["c1n"] if base else 2) and int((g == 12).sum()) == 0)
            or int(d.get("levels_completed") or 0) > 3
        )
        if interesting:
            print(f"  SIGNAL {tag} morph={morph} histΔ={hist_d} c12n={len(c12)} lv={row['lv']}")
            signals.append(row)
        log.append({**row, **(m or {})})
        return row

    track("enter", d, g)

    # novel: click gap11, beam5 near gap, color7 top, mid window, dig seam
    targets = []
    if gap0:
        targets.append(("gap", round(gap0["cx"]), round(gap0["cy"])))
        targets.append(("gap_corner", gap0["x0"], gap0["y0"]))
        # beam near gap
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-2, 0)):
            x, y = gap0["x0"] + dx, gap0["y0"] + dy
            if 0 <= x < 64 and 0 <= y < 64 and int(g[y, x]) == 5:
                targets.append(("beam", x, y))
                break
    # color7
    ys, xs = np.where(g == 7)
    if len(xs):
        targets.append(("c7", int(xs[0]), int(ys[0])))
    mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if mid:
        targets.append(("mid", round(mid[0]["cx"]), round(mid[0]["cy"])))

    g_prev = g
    for name, x, y in targets:
        d2 = click(sess, x, y)
        if d2 is None:
            continue
        g2 = plane(d2["frame"])
        track(f"click_{name}", d2, g2, g_prev)
        if maybe_clear(d2, sess, out):
            out["D"] = {"log": log, "signals": signals, "breaks": any_break(log)}
            return d2, g2
        g, d, g_prev = g2, d2, g2

    # convert + hop + ceiling novel clicks
    d, g = sink_c12(sess, d, g, log, "Ds")
    track("converted", d, g, g_prev)
    d, g, _ = arm_left(sess, d, g, log, "Darm")
    d, g, _ = pad(sess, d, g, 39, "Dhz ", log)
    d, g = climb(sess, d, g, log, "Dup", n=5)
    track("ceiling", d, g)

    # at ceiling: click gap, mid, dig_top cells, accent, body side
    m = dig_metrics(g)
    ceil_targets = []
    gp = gap11(g)
    if gp:
        ceil_targets.append(("ceil_gap", round(gp["cx"]), round(gp["cy"])))
    mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if mid:
        ceil_targets.append(("ceil_mid", round(mid[0]["cx"]), round(mid[0]["cy"])))
    if m and m["dig_top"] is not None:
        ceil_targets.append(("ceil_dig", 26, m["dig_top"]))
        ceil_targets.append(("ceil_y45", 26, 45))
    sp = sprite(g)
    if sp and sp.get("accent"):
        a = sp["accent"]
        ceil_targets.append(("ceil_acc", round(a["cx"]), round(a["cy"])))
    # color5 under mid
    ceil_targets.append(("ceil_beam", 28, 46))

    g_prev = g
    for name, x, y in ceil_targets:
        if not (0 <= x < 64 and 0 <= y < 64):
            continue
        d2 = click(sess, x, y)
        if d2 is None:
            continue
        g2 = plane(d2["frame"])
        track(f"click_{name}", d2, g2, g_prev)
        if maybe_clear(d2, sess, out):
            break
        # also try pad after novel click
        if body_ndiff(g_prev, g2) > 0:
            d, g = d2, g2
            d, g, _ = pad(sess, d, g, 15, f"after_{name} ", log)
            track(f"after_{name}", d, g)
            g_prev = g
        else:
            g, d, g_prev = g2, d2, g2

    # hist scan across bay0 deep sink + env storm without expecting mid flank
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    base2 = dig_metrics(g)
    hist_events = []
    for i in range(6):
        g0 = g
        d, g, _ = pad(sess, d, g, 15, f"Hsink{i} ", log)
        h0 = {int(k): int(v) for k, v in zip(*np.unique(g0, return_counts=True))}
        h1 = {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}
        dd = {k: h1.get(k, 0) - h0.get(k, 0) for k in set(h0) | set(h1) if h1.get(k, 0) != h0.get(k, 0)}
        # flag rare color births
        rare = {k: v for k, v in dd.items() if k not in (0, 1, 3, 4, 9, 11, 12) and v != 0}
        if rare or int((g == 12).sum()) != int((g0 == 12).sum()):
            hist_events.append({"i": i, "dd": dd, "rare": rare, "lv": d.get("levels_completed")})
            print("  hist_event", i, dd)
        if maybe_clear(d, sess, out):
            break
    for i in range(8):
        g0 = g
        d, g, _ = pad(sess, d, g, 45 + (i % 3) * 6, f"Henv{i} ", log)  # 45,51,57
        h0 = {int(k): int(v) for k, v in zip(*np.unique(g0, return_counts=True))}
        h1 = {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}
        dd = {k: h1.get(k, 0) - h0.get(k, 0) for k in set(h0) | set(h1) if h1.get(k, 0) != h0.get(k, 0)}
        if any(k not in (0, 3) for k in dd):
            hist_events.append({"env_i": i, "dd": dd, "lv": d.get("levels_completed")})
            print("  env_hist", i, dd)
        gp = gap11(g)
        if base2 and base2.get("gap") and gp:
            if (gp["x0"], gp["y0"], gp["n"]) != (
                base2["gap"]["x0"],
                base2["gap"]["y0"],
                base2["gap"]["n"],
            ):
                print("  GAP MORPH", base2["gap"], "->", gp)
                signals.append({"tag": "gap_morph_env", "from": base2["gap"], "to": gp})

    out["D"] = {
        "log": log,
        "signals": signals,
        "hist_events": hist_events,
        "breaks": any_break(log),
    }
    return d, g


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"CLEAR": False, "breaks_all": []}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        sec_A_arm_clear_climb(sess, out)
        if out.get("CLEAR"):
            return 0
        sec_B_hop_phase(sess, out)
        if out.get("CLEAR"):
            return 0
        sec_C_click_dig(sess, out)
        if out.get("CLEAR"):
            return 0
        sec_D_falsify_midgate(sess, out)

        for sec in ("A", "B", "C", "D"):
            br = (out.get(sec) or {}).get("breaks") or []
            out["breaks_all"].extend(br)
        print("\n==== SUMMARY")
        print("CLEAR", out.get("CLEAR"))
        print("breaks_n", len(out["breaks_all"]))
        for b in out["breaks_all"][:20]:
            print(" BREAK", b.get("tag"), "off", b.get("offset"), "y0", b.get("y0"))
        sigs = (out.get("D") or {}).get("signals") or []
        print("signals_n", len(sigs))
        for s in sigs[:15]:
            print(" SIG", s.get("tag"), s.get("gap_morph"), s.get("hist_delta"), "lv", s.get("lv"))
    finally:
        sess.close()

    # slim log for fixture (drop huge ch lists)
    def slim(obj):
        if isinstance(obj, dict):
            return {
                k: slim(v)
                for k, v in obj.items()
                if k not in ("ch",)
            }
        if isinstance(obj, list):
            return [slim(x) for x in obj]
        return obj

    OUT.write_text(
        json.dumps(slim(out), indent=2, ensure_ascii=False, default=float),
        encoding="utf-8",
    )
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
