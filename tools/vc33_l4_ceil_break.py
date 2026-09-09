"""L4: break body y0=40 OR get color0@x24-26/x30 y<=45; falsify mid-gate.

Knife: one more climb would put color0 tops 46→43 (inside mid y). Map/clear
cells above body; pre-ceil phase; env reach at x30; left-only levels hunt.

tags=["vc33_recon"]
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
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite, summarize  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_ceil_break.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 7: "U", 9: "P", 11: "A", 12: "C"}


def dump(g, y0=32, y1=50, x0=15, x1=40):
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
        return d, g, {}
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "y0": s1["body"]["y0"] if s1 else None,
        "cy": s1["body"]["cy"] if s1 else None,
        "cx": s1["body"]["cx"] if s1 else None,
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
        "h12": int((g2 == 12).sum()),
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "lv": d2.get("levels_completed"),
        "acts": d2.get("available_actions"),
    }
    print(
        f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) y0={info['y0']} cy={info['cy']} "
        f"nd={info['nd']} mid12={info['mid12']} lv={info['lv']} acts={info['acts']}"
    )
    return d2, g2, info


def crit(g):
    tops = {}
    for x in (24, 25, 26, 30, 31):
        ys = [int(y) for y in range(34, 60) if int(g[y, x]) == 0]
        tops[x] = min(ys) if ys else None
    gap0 = [(x, y) for x in (24, 25, 26) for y in range(34, 46) if int(g[y, x]) == 0]
    midr0 = [(30, y) for y in range(34, 46) if int(g[y, 30]) == 0]
    zeros_le45 = [(int(x), int(y)) for y, x in np.argwhere(g == 0) if y <= 45 and 9 <= x <= 44]
    return {
        "tops": tops,
        "gap0": gap0,
        "midr0": midr0,
        "zeros_le45_n": len(zeros_le45),
        "zeros_le45_sample": zeros_le45[:40],
        "body": sprite(g)["body"] if sprite(g) else None,
    }


def above_cells(g):
    sp = sprite(g)
    if not sp:
        return []
    b = sp["body"]
    cells = []
    for y in range(max(1, b["y0"] - 6), b["y0"]):
        for x in range(b["x0"] - 1, b["x1"] + 2):
            cells.append((x, y, int(g[y, x])))
    return cells


def arm_hop(sess, hop=39):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"])
    d = d2
    d, g, _ = pad(sess, d, g, hop, "hz ")
    return d, g


def climb_to(sess, d, g, target_y0=40):
    for i in range(8):
        sp = sprite(g)
        if not sp:
            break
        if sp["body"]["y0"] <= target_y0:
            break
        d, g, info = pad(sess, d, g, 15, f"up{i} ")
        if abs(info.get("dy") or 0) < 0.1:
            break
    return d, g


def maybe_clear(d, g, sess, out):
    if int(d.get("levels_completed") or 0) < 4:
        return False
    print("CLEAR", d.get("levels_completed"))
    (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
        json.dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
        encoding="utf-8",
    )
    d1 = sess.action("ACTION1")
    (ROOT / "tests/fixtures/vc33_l5_frame_live.json").write_text(
        json.dumps({"frame": d1["frame"], "levels": d1.get("levels_completed")}, indent=2),
        encoding="utf-8",
    )
    out["cleared"] = True
    out["l5_lv"] = d1.get("levels_completed")
    return True


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"hits": [], "phases": {}}
    try:
        sess.open()

        # === A: ceiling above-map + clear blockers then retry up ===
        print("\n=== A ceiling blockers")
        d, g = arm_hop(sess, 39)
        d, g = climb_to(sess, d, g, 40)
        sp = sprite(g)
        print("ceil", sp["body"] if sp else None, "crit", crit(g))
        dump(g)
        above = above_cells(g)
        print("above", above)
        out["phases"]["A_ceil"] = {"crit": crit(g), "above": above, "acts": d.get("available_actions")}
        # click every non-empty / every cell in would-be -3y landing
        b = sp["body"]
        targets = []
        for y in range(b["y0"] - 3, b["y0"]):
            for x in range(b["x0"], b["x1"] + 1):
                targets.append((x, y, f"land{int(g[y, x])}"))
        for x, y, col in above:
            if col != 3:
                targets.append((x, y, f"ab{col}"))
        # also mid left edge / seam
        for x, y in [(26, 45), (26, 44), (26, 43), (27, 45), (27, 40), (24, 45), (30, 45), (30, 46)]:
            targets.append((x, y, "seam"))
        seen = set()
        for x, y, tag in targets:
            if (x, y) in seen or not (0 <= x < 64 and 0 <= y < 64):
                continue
            seen.add((x, y))
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            s1 = sprite(g2)
            if nd or (s1 and s1["body"]["y0"] < 40):
                print(f"  click({x},{y}:{tag}) nd={nd} ch={body_changes(g0,g2)} "
                      f"y0={s1['body']['y0'] if s1 else None} lv={d2.get('levels_completed')}")
                out["hits"].append({"phase": "A_click", "xy": [x, y], "tag": tag, "nd": nd,
                                    "y0": s1["body"]["y0"] if s1 else None, "lv": d2.get("levels_completed")})
                g, d = g2, d2
            if maybe_clear(d2, g2, sess, out):
                OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                return
        # retry up after clicks
        d, g, info = pad(sess, d, g, 15, "Aretry ")
        print("after retry crit", crit(g))
        out["phases"]["A_retry"] = {"info": info, "crit": crit(g)}
        if (info.get("y0") or 99) < 40 or info.get("mid12") or crit(g)["gap0"] or crit(g)["midr0"]:
            out["hits"].append({"phase": "A_retry", **info, "crit": crit(g)})
        if maybe_clear(d, g, sess, out):
            OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
            return

        # === B: stop at pre-ceil y0=43, clear above, then final up ===
        print("\n=== B pre-ceil clear then up")
        d, g = arm_hop(sess, 39)
        d, g = climb_to(sess, d, g, 43)
        print("pre", sprite(g)["body"], "crit", crit(g), "above", above_cells(g))
        dump(g, 34, 50, 15, 35)
        b = sprite(g)["body"]
        for y in range(b["y0"] - 4, b["y0"]):
            for x in range(b["x0"] - 1, b["x1"] + 2):
                col = int(g[y, x])
                if col in (0, 1, 5, 7, 11, 12):
                    g0 = g
                    d2 = click(sess, x, y)
                    if d2 is None:
                        break
                    g2 = plane(d2["frame"])
                    if body_ndiff(g0, g2):
                        print(f"  Bclick({x},{y})={col} ch={body_changes(g0,g2)}")
                        g, d = g2, d2
        d, g, info = pad(sess, d, g, 15, "Bup ")
        print("B after up", sprite(g)["body"] if sprite(g) else None, "crit", crit(g))
        out["phases"]["B"] = {"info": info, "crit": crit(g)}
        if (info.get("y0") or 99) < 40 or crit(g)["gap0"] or crit(g)["midr0"] or info.get("mid12"):
            out["hits"].append({"phase": "B", **info, "crit": crit(g)})
        if maybe_clear(d, g, sess, out):
            OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
            return

        # === C: floor env reach — any color0 at y<=45 near mid? then climb ===
        print("\n=== C floor env x30/global y<=45")
        d, g = arm_hop(sess, 39)
        for i, e in enumerate((39, 45, 51, 57, 39, 45, 51, 57, 39, 45)):
            d, g, info = pad(sess, d, g, e, f"C{i} ")
            c = crit(g)
            if c["gap0"] or c["midr0"] or c["zeros_le45_n"]:
                print("  crit hit", c)
            if c["gap0"] or c["midr0"]:
                out["hits"].append({"phase": "C_env", "e": e, "crit": c})
        print("C after env crit", crit(g))
        dump(g, 34, 56, 20, 45)
        out["phases"]["C_env"] = crit(g)
        # climb with env interleaved at each step — watch tops[30] and gap0
        for i in range(6):
            d, g, info = pad(sess, d, g, 15, f"Cup{i} ")
            c = crit(g)
            print("  climb crit", c["tops"], "gap0", c["gap0"], "midr0", c["midr0"], "y0", c["body"]["y0"] if c["body"] else None)
            out["phases"][f"C_up{i}"] = {"info": info, "crit": c}
            if c["gap0"] or c["midr0"] or (c["body"] and c["body"]["y0"] < 40) or info.get("mid12"):
                out["hits"].append({"phase": f"C_up{i}", **info, "crit": c})
                print("HIT C")
            if abs(info.get("dy") or 0) < 0.1:
                break
            for e in (39, 45):
                d, g, info = pad(sess, d, g, e, f"Ce{i} ")
                c = crit(g)
                if c["gap0"] or c["midr0"]:
                    print("  env during climb HIT", c)
                    out["hits"].append({"phase": f"C_env@{i}", "e": e, "crit": c})
            if maybe_clear(d, g, sess, out):
                OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                return
        print("C final", crit(g), "lv", d.get("levels_completed"))
        out["phases"]["C_final"] = crit(g)

        # === D: falsify must-mid — left bay only, max height + gap click + levels ===
        print("\n=== D left-only (no mid12 path)")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        # climb left first
        for i in range(5):
            d, g, info = pad(sess, d, g, 9, f"Dup{i} ")
            if abs(info.get("dy") or 0) < 0.1:
                break
        print("D left ceil", sprite(g)["body"] if sprite(g) else None, "crit", crit(g))
        out["phases"]["D_left_ceil"] = crit(g)
        gp = gap11(g)
        if gp:
            d2 = click(sess, round(gp["cx"]), round(gp["cy"]))
            if d2:
                print("D gap click lv", d2.get("levels_completed"), "nd", body_ndiff(g, plane(d2["frame"])))
                g, d = plane(d2["frame"]), d2
                if maybe_clear(d, g, sess, out):
                    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                    return
        # sink convert arm hop stay in bay0/1 only — never open mid — spam gap
        while int((g == 12).sum()) == 0 and sprite(g)["body"]["cy"] < 55:
            d, g, _ = pad(sess, d, g, 15, "Ddn ")
        if int((g == 12).sum()):
            c = components(g, 12, 1, 80)[0]
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            g, d = plane(d2["frame"]), d2
            for _ in range(3):
                d, g, info = pad(sess, d, g, 39, "Dhz ")
                if maybe_clear(d, g, sess, out):
                    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                    return
                if abs(info.get("dx") or 0) < 0.1 and int((g == 12).sum()):
                    c = components(g, 12, 1, 80)[0]
                    d2 = click(sess, round(c["cx"]), round(c["cy"]))
                    g, d = plane(d2["frame"]), d2
            # climb bay1 ceil, click gap again
            d, g = climb_to(sess, d, g, 40)
            gp = gap11(g)
            if gp:
                d2 = click(sess, round(gp["cx"]), round(gp["cy"]))
                if d2:
                    print("D ceil gap lv", d2.get("levels_completed"))
                    g, d = plane(d2["frame"]), d2
                    if maybe_clear(d, g, sess, out):
                        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                        return
        out["phases"]["D_final"] = {"lv": d.get("levels_completed"), "crit": crit(g), "sum": summarize(g)}
        print("D final lv", d.get("levels_completed"), "mid12", bool([c for c in components(g, 12, 1, 80) if c["cx"] > 20]))

        out["final_lv"] = d.get("levels_completed")
        out["final_crit"] = crit(g)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("done hits", len(out["hits"]), "lv", out["final_lv"])
    finally:
        sess.close()


if __name__ == "__main__":
    main()
