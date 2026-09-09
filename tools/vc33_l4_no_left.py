"""L4: NO-LEFT-CONVERT tree — falsify 'mid is required second gate'.

Enter L4; NEVER sink to left 1→12. Only: pad9(up from start), env pads,
click mid, click gap. Log every frame diff / novel colors / mid morph / levels.
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
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_no_left.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 7: "U", 9: "P", 11: "A", 12: "C"}


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def hist(g):
    u, c = np.unique(g, return_counts=True)
    return {int(k): int(v) for k, v in zip(u, c)}


def mid_win(g):
    mids = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if mids:
        return {"kind": 1, **mids[0]}
    m12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    if m12:
        return {"kind": 12, **m12[0]}
    return None


def left_win(g):
    left1 = [c for c in components(g, 1, 4, 80) if c["cx"] < 20]
    if left1:
        return {"kind": 1, **left1[0]}
    left12 = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
    if left12:
        return {"kind": 12, **left12[0]}
    return None


def snap(g, d, tag):
    sp = sprite(g)
    gp = gap11(g)
    h = hist(g)
    return {
        "tag": tag,
        "lv": d.get("levels_completed") if d else None,
        "acts": d.get("available_actions") if d else None,
        "hist": h,
        "colors": sorted(h),
        "h1": int((g == 1).sum()),
        "h12": int((g == 12).sum()),
        "mid": mid_win(g),
        "left": left_win(g),
        "gap": gp,
        "sprite": sp,
        "cx": sp["body"]["cx"] if sp else None,
        "cy": sp["body"]["cy"] if sp else None,
        "y0": sp["body"]["y0"] if sp else None,
    }


def novel_colors(h0, h1):
    return sorted(set(h1) - set(h0) - {0, 3})


def apply(sess, d, g, op, base_hist):
    """op: ('pad', x0) | ('xy', x, y, label)"""
    g0 = g
    s0 = snap(g, d, "pre")
    if op[0] == "pad":
        x0 = op[1]
        p = next(p for p in pads_sorted(g) if p["x0"] == x0)
        d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
        label = f"pad{x0}"
    else:
        _, x, y, label = op
        d2 = click(sess, int(x), int(y))
    if d2 is None:
        return d, g, {"label": label, "http": True}
    g2 = plane(d2["frame"])
    s1 = snap(g2, d2, label)
    nd = body_ndiff(g0, g2)
    ch = body_changes(g0, g2) if nd else {}
    nov = novel_colors(base_hist, s1["hist"])
    mid_ch = s0["mid"] != s1["mid"]
    left_ch = s0["left"] != s1["left"]
    gap_ch = s0["gap"] != s1["gap"]
    # SAFETY: abort if left converted to 12 (should not happen without sink)
    left_became_12 = (s0["left"] or {}).get("kind") == 1 and (s1["left"] or {}).get("kind") == 12
    info = {
        "label": label,
        "nd": nd,
        "ch": ch,
        "dx": (s1["cx"] or 0) - (s0["cx"] or 0),
        "dy": (s1["cy"] or 0) - (s0["cy"] or 0),
        "lv0": s0["lv"],
        "lv1": s1["lv"],
        "acts": s1["acts"],
        "novel": nov,
        "mid_ch": mid_ch,
        "left_ch": left_ch,
        "gap_ch": gap_ch,
        "left_became_12": left_became_12,
        "h12": s1["h12"],
        "mid": s1["mid"],
        "left": s1["left"],
        "cy": s1["cy"],
        "cx": s1["cx"],
        "y0": s1["y0"],
    }
    flag = (
        nov
        or mid_ch
        or gap_ch
        or left_became_12
        or int(s1["lv"] or 0) != int(s0["lv"] or 0)
        or (s1["acts"] or []) != (s0["acts"] or [])
        or abs(info["dx"]) + abs(info["dy"]) > 0.1
        or (nd and not ch)  # weird
    )
    # always print non-noop-ish
    if flag or nd:
        print(
            f"  {label}: Δ=({info['dx']:.0f},{info['dy']:.0f}) nd={nd} ch={ch} "
            f"lv={s0['lv']}→{s1['lv']} acts={s1['acts']} novel={nov} "
            f"mid_ch={mid_ch} gap_ch={gap_ch} left12={left_became_12} "
            f"h12={s1['h12']} cy={s1['cy']} mid={s1['mid']}"
        )
    return d2, g2, info


def maybe_clear(d, sess):
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
    return True


def dump(g, y0=34, y1=55, x0=0, x1=50):
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(x0, x1 + 1))
        print(f"{y:02d}|{row}")


def main():
    key = _api_key()
    sess = Sess(key)
    log = []
    signals = []
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        base = snap(g, d, "enter")
        print("ENTER", {k: base[k] for k in ("lv", "acts", "colors", "h1", "h12", "cy", "y0", "left", "mid", "gap")})
        dump(g)
        log.append(base)
        base_hist = base["hist"]

        # Guard: never use pad15 while it would sink (cy increases).
        # At enter: pad9 = -3y (up), pad15 = +3y (sink) — FORBIDDEN.
        # After one up to ceil: pad15 may be noop or down depending bay — still avoid pad15
        # until we know we're not converting. Policy: NEVER pad15 in this probe.

        mid = mid_win(g)
        gp = gap11(g)
        mid_xy = (round(mid["cx"]), round(mid["cy"])) if mid else (28, 40)
        gap_xy = (round(gp["cx"]), round(gp["cy"])) if gp else (43, 29)

        # ---- Phase 1: at spawn — env + mid + gap, no vertical sink ----
        print("\n==== P1 spawn: env / mid / gap (no pad15)")
        for op in [
            ("pad", 39), ("pad", 45), ("pad", 51), ("pad", 57),
            ("pad", 39), ("pad", 45),
            ("xy", *mid_xy, "mid"),
            ("xy", mid["x0"], mid["y1"], "midbot") if mid else ("xy", 28, 45, "midbot"),
            ("xy", *gap_xy, "gap"),
        ]:
            d, g, info = apply(sess, d, g, op, base_hist)
            log.append(info)
            if info.get("novel") or info.get("mid_ch") or info.get("gap_ch") or info.get("left_became_12") or (
                info.get("lv1") != info.get("lv0")
            ):
                signals.append(info)
            if maybe_clear(d, sess):
                return
            assert not info.get("left_became_12"), "LEFT CONVERTED — probe violated"

        print("after P1", snap(g, d, "p1")["left"], snap(g, d, "p1")["mid"], "h12", int((g == 12).sum()))

        # ---- Phase 2: climb LEFT bay with pad9 only (up), never pad15 ----
        # At enter pad9=-3y. Keep tapping pad9 until noop (left ceiling).
        print("\n==== P2 climb left with pad9 only")
        for i in range(6):
            d, g, info = apply(sess, d, g, ("pad", 9), base_hist)
            log.append(info)
            if info.get("novel") or info.get("mid_ch") or info.get("gap_ch") or abs(info.get("dy") or 0) > 0.1:
                if info.get("novel") or info.get("mid_ch") or info.get("gap_ch") or info.get("lv1") != info.get("lv0"):
                    signals.append(info)
            if maybe_clear(d, sess):
                return
            if abs(info.get("dy") or 0) < 0.1 and i > 0:
                print("  left ceiling reached")
                break
            # if pad9 somehow sank (shouldn't), abort
            if (info.get("dy") or 0) > 0.1:
                print("  UNEXPECTED sink on pad9 — stop")
                break

        s = snap(g, d, "left_ceil")
        print("left_ceil", {k: s[k] for k in ("cy", "y0", "h12", "left", "mid", "lv")})
        dump(g, 34, 55, 0, 45)
        log.append(s)

        # ---- Phase 3: at left ceiling — env + mid + gap spam ----
        print("\n==== P3 left-ceil: env / mid / gap")
        for op in [
            ("pad", 39), ("pad", 45), ("pad", 51), ("pad", 57),
            ("pad", 39), ("pad", 45), ("pad", 51), ("pad", 57),
            ("xy", *mid_xy, "mid"),
            ("xy", 28, 45, "midbot"),
            ("xy", 27, 45, "midL"),
            ("xy", 29, 34, "midtop"),
            ("xy", *gap_xy, "gap"),
            ("xy", 43, 29, "gap2"),
        ]:
            d, g, info = apply(sess, d, g, op, base_hist)
            log.append(info)
            if info.get("novel") or info.get("mid_ch") or info.get("gap_ch") or info.get("lv1") != info.get("lv0"):
                signals.append(info)
            if maybe_clear(d, sess):
                return
            assert int((g == 12).sum()) == 0 or (left_win(g) or {}).get("kind") != 12

        # ---- Phase 4: forced choice — ONE pad15 from left ceil?
        # At left ceil, pad15 is +3y = SINK toward convert. FORBIDDEN.
        # Instead try pad15 only if we're somehow still above convert height with
        # explicit check: refuse if it would create h12.
        # Skip pad15 entirely.

        # ---- Phase 5: re-enter style second branch — from spawn go pad9 once, then env heavy ----
        print("\n==== P5 fresh: one-up then env×20 + mid/gap (still no pad15)")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        base_hist = hist(g)
        d, g, info = apply(sess, d, g, ("pad", 9), base_hist)  # one up
        log.append(info)
        for i, e in enumerate([39, 45, 51, 57] * 5):
            d, g, info = apply(sess, d, g, ("pad", e), base_hist)
            log.append(info)
            if info.get("novel") or info.get("mid_ch") or info.get("gap_ch") or info.get("lv1") != info.get("lv0"):
                signals.append(info)
            if maybe_clear(d, sess):
                return
        for op in [("xy", 28, 40, "mid"), ("xy", 28, 45, "midbot"), ("xy", 43, 29, "gap")]:
            d, g, info = apply(sess, d, g, op, base_hist)
            log.append(info)
            if info.get("novel") or info.get("mid_ch") or info.get("gap_ch") or info.get("lv1") != info.get("lv0"):
                signals.append(info)
            if maybe_clear(d, sess):
                return

        final = snap(g, d, "final")
        print("\n==== RESULT")
        print("signals", len(signals))
        for s in signals:
            print(" SIGNAL", s.get("label"), "novel=", s.get("novel"), "mid_ch=", s.get("mid_ch"),
                  "gap_ch=", s.get("gap_ch"), "lv", s.get("lv0"), "→", s.get("lv1"))
        print("final lv", final["lv"], "h12", final["h12"], "left", final["left"], "mid", final["mid"])

        verdict = {
            "left_never_12": final["h12"] == 0 and (final["left"] or {}).get("kind") != 12,
            "any_novel": any(s.get("novel") for s in signals),
            "any_mid_ch": any(s.get("mid_ch") for s in signals),
            "any_gap_ch": any(s.get("gap_ch") for s in signals),
            "any_levels": any(s.get("lv1") != s.get("lv0") for s in signals),
            "n_signals": len(signals),
            "final_lv": final["lv"],
        }
        # Interpretation per user brief
        if verdict["any_novel"] or verdict["any_mid_ch"] or verdict["any_gap_ch"] or verdict["any_levels"]:
            verdict["reading"] = "NEW_SIGNAL — mid-not-only-path / reassess clear meta"
        else:
            verdict["reading"] = "NO_SIGNAL — mid-as-second-gate still plausible; need keep-left-12 climb"

        print("VERDICT", verdict)
        OUT.write_text(
            json.dumps({"verdict": verdict, "signals": signals, "log_tail": log[-40:], "final": final},
                       indent=2, default=str),
            encoding="utf-8",
        )
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
