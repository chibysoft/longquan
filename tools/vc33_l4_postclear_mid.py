"""L4 H54: after left-12 cleared, hunt mid convert via NON-dig triggers.

Per height rung: ONE enter → setup → try actions in-session (re-climb if
a pad moved us). Look for mid 1→12 / n4 / novel / levels↑.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_postclear_mid.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad_click(sess, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    return click(sess, int(round(p["cx"])), int(round(p["cy"])))


def mid_comp(g):
    m1 = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if m1:
        return {"kind": 1, **{k: m1[0][k] for k in ("n", "x0", "y0", "x1", "y1", "cx", "cy")}}
    m12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    if m12:
        return {"kind": 12, **{k: m12[0][k] for k in ("n", "x0", "y0", "x1", "y1", "cx", "cy")}}
    return None


def left_comp(g):
    for color in (12, 1):
        cs = [c for c in components(g, color, 1, 80) if c["cx"] < 20]
        if cs:
            return {"kind": color, **{k: cs[0][k] for k in ("n", "x0", "y0", "x1", "y1", "cx", "cy")}}
    return None


def n4_zero_to_mid(g, mid):
    if mid is None:
        return 0
    H, W = g.shape
    kind = mid["kind"]
    n = 0
    for y in range(mid["y0"], mid["y1"] + 1):
        for x in range(mid["x0"], mid["x1"] + 1):
            if int(g[y, x]) != kind:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and int(g[ny, nx]) == 0:
                    n += 1
    return n


def snap(g, d):
    sp = sprite(g)
    mid = mid_comp(g)
    return {
        "lv": d.get("levels_completed"),
        "acts": d.get("available_actions"),
        "h12": int((g == 12).sum()),
        "left": left_comp(g),
        "mid": mid,
        "n4": n4_zero_to_mid(g, mid),
        "cy": sp["body"]["cy"] if sp else None,
        "cx": sp["body"]["cx"] if sp else None,
        "acc_y0": sp["accent"]["y0"] if sp and sp["accent"] else None,
        "acc_y1": sp["accent"]["y1"] if sp and sp["accent"] else None,
        "gap": gap11(g),
        "hist": dict(Counter(int(v) for v in g.ravel())),
    }


def signals(before, after, g0, g1):
    sigs = []
    if after["mid"] and before["mid"]:
        if after["mid"]["kind"] != before["mid"]["kind"]:
            sigs.append(f"mid_kind {before['mid']['kind']}->{after['mid']['kind']}")
        bb0 = (before["mid"]["x0"], before["mid"]["y0"], before["mid"]["x1"], before["mid"]["y1"])
        bb1 = (after["mid"]["x0"], after["mid"]["y0"], after["mid"]["x1"], after["mid"]["y1"])
        if bb0 != bb1:
            sigs.append(f"mid_bbox {bb0}->{bb1}")
    if after["n4"] != before["n4"]:
        sigs.append(f"n4 {before['n4']}->{after['n4']}")
    if (after["lv"] or 0) > (before["lv"] or 0):
        sigs.append(f"levels {before['lv']}->{after['lv']}")
    if after["acts"] != before["acts"]:
        sigs.append(f"acts {before['acts']}->{after['acts']}")
    nov = {c: n for c, n in after["hist"].items() if c not in before["hist"] and c not in (4, 11)}
    if nov:
        sigs.append(f"novel {nov}")
    mid = before["mid"] or after["mid"]
    if mid:
        local = []
        for y in range(max(0, mid["y0"] - 2), min(64, mid["y1"] + 4)):
            for x in range(max(0, mid["x0"] - 4), min(64, mid["x1"] + 5)):
                a, b = int(g0[y, x]), int(g1[y, x])
                if a != b and (a, b) not in (
                    (3, 0), (0, 3), (3, 4), (4, 3), (3, 11), (11, 3), (4, 11), (11, 4),
                    (4, 0), (0, 4), (11, 0), (0, 11),
                ):
                    local.append((x, y, a, b))
        if local:
            sigs.append(f"local_mid {local[:16]}")
    if before["gap"] != after["gap"]:
        sigs.append("gap_ch")
    return sigs


def setup_bay1_clear(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    for _ in range(8):
        if int((g == 12).sum()) > 0:
            break
        d2 = pad_click(sess, g, 15)
        g = plane(d2["frame"]); d = d2
    c = [x for x in components(g, 12, 1, 80) if x["cx"] < 20][0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d2 = pad_click(sess, g, 39)
    g = plane(d2["frame"]); d = d2
    d2 = pad_click(sess, g, 15)  # clear 12
    g = plane(d2["frame"]); d = d2
    assert int((g == 12).sum()) == 0
    return d, g


def climb_to(sess, d, g, target_cy=None, max_ups=6, until_touch=False):
    """Climb pad15. If until_touch: stop when accent y overlaps mid y near mid x."""
    n = 0
    for i in range(max_ups):
        sp = sprite(g)
        mid = mid_comp(g)
        acc = sp["accent"] if sp else None
        if until_touch and acc and mid:
            if acc["y0"] <= mid["y1"] and acc["y1"] >= mid["y0"] and acc["x1"] >= mid["x0"] - 3:
                return d, g, n, True
        if target_cy is not None and sp and sp["body"]["cy"] <= target_cy + 0.1:
            return d, g, n, False
        cy0 = sp["body"]["cy"] if sp else 99
        d2 = pad_click(sess, g, 15)
        if d2 is None:
            break
        g2 = plane(d2["frame"])
        if abs(sprite(g2)["body"]["cy"] - cy0) < 0.1:
            return d2, g2, n, False
        g = g2; d = d2
        n += 1
    sp = sprite(g)
    mid = mid_comp(g)
    acc = sp["accent"] if sp else None
    touch = bool(
        acc and mid
        and acc["y0"] <= mid["y1"]
        and acc["y1"] >= mid["y0"]
        and acc["x1"] >= mid["x0"] - 3
    )
    return d, g, n, touch


def restore_height(sess, d, g, want_cy, want_cx):
    """Cheap restore after a pad moved us: pad9 sink / pad15 up / hop if needed."""
    sp = sprite(g)
    if not sp:
        return d, g
    # if hopped away from bay1, try hop back via re-arm — too heavy; just climb/sink in place
    for _ in range(8):
        sp = sprite(g)
        if not sp:
            break
        cy, cx = sp["body"]["cy"], sp["body"]["cx"]
        if abs(cy - want_cy) < 0.2 and abs(cx - want_cx) < 1.0:
            return d, g
        if cy > want_cy + 0.2:
            d2 = pad_click(sess, g, 15)
        elif cy < want_cy - 0.2:
            d2 = pad_click(sess, g, 9)
        elif cx < want_cx - 5:
            # try hop east if left12 somehow — usually can't
            d2 = pad_click(sess, g, 39)
        else:
            break
        if d2 is None:
            break
        g = plane(d2["frame"]); d = d2
    return d, g


def try_one(sess, d, g, label, do_fn, rows, rung):
    before = snap(g, d)
    g0 = g.copy()
    d2 = do_fn(sess, g)
    if d2 is None:
        rows.append({"label": f"{rung}/{label}", "ok": False, "sigs": ["http"]})
        print(f"| {rung}/{label:22s} | FAIL |")
        return d, g, False
    g2 = plane(d2["frame"])
    after = snap(g2, d2)
    sigs = signals(before, after, g0, g2)
    dx = (after["cx"] or 0) - (before["cx"] or 0)
    dy = (after["cy"] or 0) - (before["cy"] or 0)
    row = {
        "label": f"{rung}/{label}",
        "ok": True,
        "sigs": sigs,
        "dx": dx,
        "dy": dy,
        "cy0": before["cy"],
        "cy1": after["cy"],
        "n4": after["n4"],
        "h12": after["h12"],
        "lv": after["lv"],
        "mid_kind": after["mid"]["kind"] if after["mid"] else None,
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2) if body_ndiff(g0, g2) else {},
    }
    rows.append(row)
    flag = "SIGNAL" if sigs else "none"
    print(
        f"| {row['label']:28s} | {flag:6s} | d=({dx:+.0f},{dy:+.0f}) "
        f"cy {before['cy']}->{after['cy']} n4={after['n4']} | {sigs}"
    )
    hard = any(str(s).startswith("mid_kind") or str(s).startswith("levels") for s in sigs)
    # restore if moved
    if abs(dx) > 0.5 or abs(dy) > 0.5:
        d2, g2 = restore_height(sess, d2, g2, before["cy"], before["cx"])
    return d2, g2, hard


def run_rung(sess, rung, until_touch=False, target_cy=None):
    rows = []
    d, g = setup_bay1_clear(sess)
    d, g, n_up, touch = climb_to(sess, d, g, target_cy=target_cy, until_touch=until_touch)
    base = snap(g, d)
    print(
        f"\n## {rung} ups={n_up} touch={touch} cy={base['cy']} "
        f"acc={base['acc_y0']}-{base['acc_y1']} h12={base['h12']} "
        f"left={base['left']['kind'] if base['left'] else None} "
        f"mid={base['mid']['kind'] if base['mid'] else None} n4={base['n4']}"
    )
    want_cy, want_cx = base["cy"], base["cx"]

    # Non-moving clicks first
    mid = mid_comp(g)
    left = left_comp(g)
    gp = gap11(g)
    sp = sprite(g)
    statics = []
    if mid:
        statics += [
            ("click_mid", lambda s, gg, m=mid: click(s, round(m["cx"]), round(m["cy"]))),
            ("click_midbot", lambda s, gg, m=mid: click(s, m["x0"], m["y1"])),
            ("click_midtop", lambda s, gg, m=mid: click(s, m["x0"], m["y0"])),
            ("click_mid_L", lambda s, gg, m=mid: click(s, m["x0"], round(m["cy"]))),
            ("click_mid_R", lambda s, gg, m=mid: click(s, m["x1"], round(m["cy"]))),
        ]
    if left:
        statics.append(("click_left", lambda s, gg, L=left: click(s, round(L["cx"]), round(L["cy"]))))
    if gp:
        statics.append(("click_gap", lambda s, gg, gp=gp: click(s, round(gp["cx"]), round(gp["cy"]))))
    for xy, lab in (
        ((25, 45), "flank25_45"),
        ((31, 45), "flank31_45"),
        ((26, 45), "dig26_45"),
        ((26, 46), "dig26_46"),
        ((27, 46), "beam27_46"),
        ((28, 46), "beam28_46"),
        ((29, 46), "beam29_46"),
        ((24, 45), "seam24_45"),
        ((30, 45), "seam30_45"),
        ((28, 45), "midcell28_45"),
        ((28, 34), "midcell28_34"),
    ):
        statics.append((lab, lambda s, gg, xy=xy: click(s, xy[0], xy[1])))
    if sp and sp["accent"]:
        a, b = sp["accent"], sp["body"]
        statics.append(("click_accent", lambda s, gg, a=a: click(s, round(a["cx"]), round(a["cy"]))))
        statics.append(("click_body", lambda s, gg, b=b: click(s, round(b["cx"]), round(b["cy"]))))

    for lab, fn in statics:
        d, g, hard = try_one(sess, d, g, lab, fn, rows, rung)
        if hard:
            return rows, True

    # env pads then click mid
    for env_x in (39, 45, 51, 57):
        d, g, hard = try_one(
            sess, d, g, f"pad{env_x}",
            lambda s, gg, x0=env_x: pad_click(s, gg, x0),
            rows, rung,
        )
        if hard:
            return rows, True
        mid = mid_comp(g)
        if mid:
            d, g, hard = try_one(
                sess, d, g, f"after{env_x}_mid",
                lambda s, gg, m=mid: click(s, round(m["cx"]), round(m["cy"])),
                rows, rung,
            )
            if hard:
                return rows, True

    # pad9 / pad15 last (will need restore)
    for x0 in (9, 15):
        d, g, hard = try_one(
            sess, d, g, f"pad{x0}",
            lambda s, gg, x0=x0: pad_click(s, gg, x0),
            rows, rung,
        )
        if hard:
            return rows, True
        d, g = restore_height(sess, d, g, want_cy, want_cx)
        # if restore failed to clear height, re-setup this rung once
        sp = sprite(g)
        if not sp or abs(sp["body"]["cy"] - want_cy) > 0.5:
            print("  restore failed — re-setup rung")
            d, g = setup_bay1_clear(sess)
            d, g, _, _ = climb_to(sess, d, g, target_cy=target_cy, until_touch=until_touch)

    return rows, False


def main():
    key = _api_key()
    sess = Sess(key)
    all_rows = []
    try:
        sess.open()
        # Rung A: just after clear (~cy48)
        rows, hard = run_rung(sess, "clear0", until_touch=False, target_cy=48.0)
        all_rows.extend(rows)
        if not hard:
            # Rung B: climb until accent touches mid band
            rows, hard = run_rung(sess, "contact", until_touch=True)
            all_rows.extend(rows)
        if not hard:
            # Rung C: force ceiling (extra ups / stuck)
            rows, hard = run_rung(sess, "ceil", until_touch=False, target_cy=41.5)
            all_rows.extend(rows)

        sig_rows = [r for r in all_rows if r.get("sigs")]
        hard_hit = any(
            any(str(s).startswith("mid_kind") or str(s).startswith("levels") for s in r.get("sigs", []))
            for r in all_rows
        )
        reading = "MID_TRIGGER_FOUND" if hard_hit else ("WEAK_SIGNAL" if sig_rows else "NO_SIGNAL")
        out = {
            "rows": all_rows,
            "n_signal_rows": len(sig_rows),
            "signal_labels": [r["label"] for r in sig_rows],
            "reading": reading,
            "hypothesis": "H54 post-clear mid non-dig trigger",
        }
        print("\n## Summary")
        print("signal_labels:", out["signal_labels"])
        print("READING:", reading)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
